"""Stream complete fixed JARVIS releases into standard JSONL and frozen splits."""

from collections import Counter
import hashlib
import io
import json
import math
from numbers import Real
from pathlib import Path
import re
import time
import zipfile

from universal_gnn.data.splits import create_manifest


SYMBOLS = ("X H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
           "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
           "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf "
           "Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()
ATOMIC_NUMBERS = {symbol: number for number, symbol in enumerate(SYMBOLS) if number}
SOURCES = {"bandgap": ("optb88vdw_bandgap", 1, "https://ndownloader.figshare.com/files/38521619"),
           "phonon_dos": ("pdos_elast", 200, "https://ndownloader.figshare.com/files/29216859"),
           "electron_dos": ("edos_up", 300, "https://ndownloader.figshare.com/files/29216859")}


def file_sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def iter_json_array(stream):
    decoder = json.JSONDecoder()
    buffer, ended = "", False

    def refill():
        nonlocal buffer, ended
        more = stream.read(65536)
        ended = not more
        buffer += more

    def whitespace():
        nonlocal buffer
        buffer = buffer.lstrip()
        while not buffer and not ended:
            refill()
            buffer = buffer.lstrip()

    refill()
    whitespace()
    if not buffer.startswith("["):
        raise ValueError("Expected a JSON array")
    buffer = buffer[1:]
    whitespace()
    if buffer.startswith("]"):
        buffer = buffer[1:]
    else:
        while True:
            whitespace()
            while True:
                try:
                    record, offset = decoder.raw_decode(buffer)
                    break
                except json.JSONDecodeError:
                    if ended:
                        raise ValueError("Truncated or invalid JSON array") from None
                    refill()
            yield record
            buffer = buffer[offset:]
            whitespace()
            if buffer.startswith("]"):
                buffer = buffer[1:]
                break
            if not buffer.startswith(","):
                raise ValueError("Expected comma or end of JSON array")
            buffer = buffer[1:]
            whitespace()
            if buffer.startswith("]"):
                raise ValueError("Trailing JSON array comma")
    whitespace()
    if buffer or not ended:
        raise ValueError("Unexpected trailing content")


def records_from(path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".json")]
            if len(names) != 1:
                raise ValueError("Expected exactly one JSON member")
            with archive.open(names[0]) as stream:
                yield from iter_json_array(io.TextIOWrapper(stream, encoding="utf-8"))
    else:
        with path.open(encoding="utf-8") as stream:
            yield from iter_json_array(stream)


def finite_scalar(value):
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def geometry(atoms):
    if not isinstance(atoms, dict):
        raise ValueError("missing_atoms")
    elements, coords, cell = atoms.get("elements"), atoms.get("coords"), atoms.get("lattice_mat")
    if (not isinstance(elements, list) or not elements or not isinstance(coords, list) or
            len(coords) != len(elements) or not isinstance(cell, list) or len(cell) != 3):
        raise ValueError("invalid_geometry_shape")
    for row in cell + coords:
        if not isinstance(row, (list, tuple)) or len(row) != 3 or not all(finite_scalar(x) for x in row):
            raise ValueError("invalid_geometry_values")
    try:
        numbers = [ATOMIC_NUMBERS[element] for element in elements]
    except (KeyError, TypeError):
        raise ValueError("unknown_element") from None
    a, b, c = cell
    determinant = (a[0] * (b[1] * c[2] - b[2] * c[1]) -
                   a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0]))
    if not math.isfinite(determinant) or abs(determinant) < 1e-9:
        raise ValueError("singular_cell")
    cartesian = atoms.get("cartesian", False)
    if not isinstance(cartesian, bool):
        raise ValueError("invalid_cartesian_flag")
    positions = ([[float(v) for v in row] for row in coords] if cartesian else
                 [[sum(row[j] * cell[j][k] for j in range(3)) for k in range(3)] for row in coords])
    if not all(finite_scalar(v) for row in positions for v in row):
        raise ValueError("nonfinite_cartesian_positions")
    result = {"numbers": numbers, "positions": positions, "cell": [[float(v) for v in row] for row in cell],
              "pbc": [True, True, True]}
    return result, hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prepare_release(source, output, *, kind, split_seed=0, metal_threshold=.01, execution=None):
    if kind not in SOURCES:
        raise ValueError("Unknown JARVIS preparation kind")
    if not finite_scalar(metal_threshold) or metal_threshold < 0:
        raise ValueError("metal_threshold must be finite and nonnegative")
    field, channels, url = SOURCES[kind]

    def targets(record):
        value = record.get(field)
        if kind == "bandgap":
            if not finite_scalar(value):
                raise ValueError("missing_or_nonfinite_label")
            return {"bandgap": float(value), "classification": int(value > metal_threshold)}
        if (not isinstance(value, list) or len(value) != channels or
                not all(finite_scalar(v) for v in value)):
            raise ValueError("missing_nonfinite_or_wrong_channels")
        return {"spectrum": [float(v) for v in value]}

    return prepare_records(source, output, records_from(source), kind=kind, field=field,
                           channels=channels, url=url, targets=targets, split_seed=split_seed,
                           metal_threshold=metal_threshold, execution=execution)


def prepare_records(source, output, records, *, kind, field, channels, url, targets,
                    split_seed=0, metal_threshold=None, execution=None, audit_details=None):
    """Write validated source records using one immutable group and audit protocol."""
    started = time.perf_counter()
    source, output = Path(source), Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Preparation output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    source_hash = file_sha256(source)
    counts, group_records, known_ids = Counter(), [], {}
    dataset_hash, max_atoms, group_counts, class_counts = hashlib.sha256(), 0, Counter(), Counter()
    species_counts = Counter()
    parents, geometry_first, reference_first = [], {}, {}

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def join(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[max(a, b)] = min(a, b)
    with (output / "structures.jsonl").open("wb") as data, (output / "exclusions.jsonl").open("w", encoding="utf-8") as excluded:
        for index, record in enumerate(records):
            counts["source_records"] += 1
            identifier = record.get("jid") if isinstance(record, dict) else None
            reason = None
            if not isinstance(identifier, str) or not identifier:
                reason = "missing_jid"
            if reason is None:
                try:
                    record_targets = targets(record)
                    atoms, fingerprint = geometry(record.get("atoms"))
                except ValueError as error:
                    reason = str(error)
            if reason is not None:
                counts[reason] += 1
                excluded.write(json.dumps({"source_index": index, "id": identifier, "reason": reason}) + "\n")
                continue
            content = hashlib.sha256(json.dumps({"geometry": fingerprint, "targets": record_targets}, sort_keys=True).encode()).hexdigest()
            if identifier in known_ids:
                if known_ids[identifier] != content:
                    raise ValueError(f"Conflicting source records for {identifier}")
                counts["identical_duplicate_id"] += 1
                excluded.write(json.dumps({"source_index": index, "id": identifier, "reason": "identical_duplicate_id"}) + "\n")
                continue
            known_ids[identifier] = content
            metadata = {"source_url": url, "archive_sha256": source_hash, "source_index": index,
                        "source_file": source.name, "geometry_sha256": fingerprint,
                        "label_field": field, "external_reference": record.get("reference")}
            normalized = {"schema_version": 1, "id": identifier, **atoms, "targets": record_targets, "metadata": metadata}
            encoded = (json.dumps(normalized, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            data.write(encoded)
            dataset_hash.update(encoded)
            counts["written_records"] += 1
            max_atoms = max(max_atoms, len(atoms["numbers"]))
            species_counts.update(atoms["numbers"])
            group_counts[fingerprint] += 1
            group_records.append({"id": identifier, "group": fingerprint})
            current = len(parents)
            parents.append(current)
            if fingerprint in geometry_first:
                join(current, geometry_first[fingerprint])
            geometry_first[fingerprint] = current
            reference = record.get("reference")
            for token in re.findall(r"\bmp-\d+\b", reference if isinstance(reference, str) else ""):
                if token in reference_first:
                    join(current, reference_first[token])
                reference_first[token] = current
            if kind == "bandgap":
                class_counts[str(record_targets["classification"])] += 1
    component_names = {}
    for index, record in enumerate(group_records):
        component = find(index)
        component_names[component] = min(component_names.get(component, record["id"]), record["id"])
    for index, record in enumerate(group_records):
        record["group"] = "material:" + component_names[find(index)]
    split = create_manifest(group_records, source_sha256=dataset_hash.hexdigest(), seed=split_seed)
    (output / "split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")
    audit = {"version": 1, "kind": kind, "source": {"file": source.name, "url": url, "sha256": source_hash,
              "bytes": source.stat().st_size}, "dataset_sha256": dataset_hash.hexdigest(), "counts": dict(counts),
             "split_counts": split["counts"], "split_seed": split_seed, "maximum_atoms": max_atoms,
             "atomic_numbers_present": sorted(species_counts),
             "atom_occurrences_by_number": {str(z): species_counts[z] for z in sorted(species_counts)},
             "duplicate_geometry_records_retained": sum(n - 1 for n in group_counts.values()),
             "grouping": "union of exact Cartesian geometry and explicit shared mp-ID references; no crystallographic equivalence claim",
             "coverage": "all source records visited; no atom-count cap or first-N selection",
             "pretraining_overlap": "not yet audited; do not claim disjoint pretrained evaluation",
             "tasks": ["bandgap", "classification"] if kind == "bandgap" else
                      ["dielectric"] if kind == "dielectric" else ["spectrum"],
             "channels": channels, "vector_transform": "none; upstream vector order/scale retained" if channels > 1 else None,
             "metal_threshold_eV": metal_threshold if kind == "bandgap" else None,
             "class_convention": {"0": "bandgap<=threshold", "1": "bandgap>threshold"} if kind == "bandgap" else None,
             "class_counts": dict(class_counts) if kind == "bandgap" else None,
             "elapsed_seconds": time.perf_counter() - started,
             "execution": {"preparation_source_sha256": file_sha256(__file__), **(execution or {})}}
    audit.update(audit_details or {})
    (output / "audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False), encoding="utf-8")
    return audit
