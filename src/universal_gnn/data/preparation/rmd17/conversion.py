"""Standard JSONL with unmodified coordinates and explicit SI energy/force units."""

from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import time

from .partitions import build_manifest, frame_id, parse_indices
from .source import SOURCE_FILES, SOURCE_URL, read_arrays, verify_sources


with localcontext() as context:
    context.prec = 50
    KCAL_MOL_TO_EV = float(Decimal("4184") / (Decimal("6.02214076e23") * Decimal("1.602176634e-19")))


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(json.dumps(value, indent=2, allow_nan=False).encode())
    temporary.replace(path)


def _scalar(value):
    return type(value) in (int, float) and math.isfinite(value)


def normalize_record(index, *, numbers, positions, energy, forces, old_index):
    if (not isinstance(numbers, list) or not numbers or any(type(z) is not int or not 1 <= z <= 118 for z in numbers)
            or type(old_index) is not int or old_index < 0 or not _scalar(energy)):
        raise ValueError("Invalid rMD17 species, original frame, or energy")
    n = len(numbers)
    for name, value in (("positions", positions), ("forces", forces)):
        if (not isinstance(value, list) or len(value) != n or any(
                not isinstance(row, list) or len(row) != 3 or not all(_scalar(x) for x in row) for row in value)):
            raise ValueError("Invalid rMD17 finite [N,3] " + name)
    atoms = dict(numbers=list(numbers), positions=[[float(x) for x in row] for row in positions],
                 cell=[[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]], pbc=[False, False, False])
    fingerprint = hashlib.sha256(json.dumps(atoms, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return dict(schema_version=1, id=frame_id(index), **atoms,
        targets=dict(energy=float(energy) * KCAL_MOL_TO_EV,
                     forces=[[float(x) * KCAL_MOL_TO_EV for x in row] for row in forces]),
        metadata=dict(source_url=SOURCE_URL, archive_sha256=SOURCE_FILES["rmd17_ethanol.npz"]["sha256"],
            source_index=index, geometry_sha256=fingerprint, molecule="ethanol", old_index=old_index,
            cell_convention="Identity nonperiodic placeholder only; original coordinates unchanged, never wrapped",
            label_field="revised energies/forces; old labels not used"))


def _write_records(output, rows, *, expected_count, official_train, official_test):
    output = Path(output)
    names = ["structures.jsonl", "structures.jsonl.partial", "split.json", "audit.json"]
    if any((output / name).exists() for name in names):
        raise FileExistsError("rMD17 writer requires fresh output files")
    digest, records, old_indices = hashlib.sha256(), [], set()
    energies, forces, zero_forces = 0, 0, 0
    with (output / "structures.jsonl.partial").open("wb") as stream:
        for index, row in enumerate(rows):
            if (row["id"] != frame_id(index) or row["metadata"]["source_index"] != index
                    or row["metadata"]["old_index"] in old_indices):
                raise ValueError("rMD17 source order/ID or unique old frame changed")
            old_indices.add(row["metadata"]["old_index"])
            encoded = (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            stream.write(encoded)
            digest.update(encoded)
            records.append(dict(id=row["id"], group=row["metadata"]["geometry_sha256"]))
            energies += 1
            forces += 3 * len(row["numbers"])
            zero_forces += all(x == 0 for values in row["targets"]["forces"] for x in values)
    if len(records) != expected_count:
        raise ValueError("rMD17 complete source count differs; no partial success")
    manifest = build_manifest(records, source_sha256=digest.hexdigest(), official_train=official_train, official_test=official_test)
    _json(output / "split.json", manifest)
    (output / "structures.jsonl.partial").replace(output / "structures.jsonl")
    return dict(dataset_sha256=digest.hexdigest(), source_records=len(records), written_records=len(records), excluded_records=0,
        energy_components=energies, force_components=forces, whole_zero_force_records=zero_forces,
        split_counts=manifest["counts"], official_test_cohort_count=1000, split_sha256=_hash(output / "split.json"))


def prepare_rmd17(raw_directory, output, *, execution=None):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Complete rMD17 preparation requires Slurm")
    started = time.perf_counter()
    raw_directory, output = Path(raw_directory), Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("rMD17 preparation requires a fresh empty output")
    output.mkdir(parents=True, exist_ok=True)
    report = dict(version=1, kind="rmd17_ethanol_preparation", status="running", stage="source_integrity",
                  formal_training_runs=0, execution=execution or {})
    _json(output / "report.json", report)
    try:
        sources = verify_sources(raw_directory)
        arrays, summary = read_arrays(raw_directory)
        official = {role: parse_indices((raw_directory / ("index_" + role + "_01.csv")).read_text(), source_count=100000)
                    for role in ("train", "test")}
        report.update(stage="complete_conversion", sources=sources, original_arrays=summary)
        _json(output / "report.json", report)
        z = [int(x) for x in arrays["nuclear_charges"].tolist()]
        rows = (normalize_record(i, numbers=z, positions=arrays["coords"][i].tolist(),
                energy=float(arrays["energies"][i]), forces=arrays["forces"][i].tolist(), old_index=int(arrays["old_indices"][i]))
                for i in range(100000))
        audit = _write_records(output, rows, expected_count=100000, official_train=official["train"], official_test=official["test"])
        if verify_sources(raw_directory) != sources:
            raise ValueError("rMD17 source changed during conversion")
        package = Path(__file__).parent
        hashes = {"data/preparation/rmd17/" + name: _hash(package / name)
                  for name in ("__init__.py", "source.py", "partitions.py", "conversion.py")}
        hashes["data/splits/manifest.py"] = _hash(package.parents[1] / "splits/manifest.py")
        report.update(status="passed", stage="complete", **audit, source_sha256=hashes,
            maximum_atoms=9, atomic_numbers_present=sorted(set(z)),
            units=dict(positions="angstrom", energy="eV total per structure", forces="eV/angstrom"),
            source_units=dict(positions="angstrom", energy="kcal/mol", forces="kcal/mol/angstrom"),
            source_to_target_factor=KCAL_MOL_TO_EV, unit_convention="thermochemical calorie and exact SI2019 e/Avogadro constants",
            stress="No stress labels or supervised stress claim", elapsed_seconds=time.perf_counter() - started,
            interpretation="All100000 nonperiodic source frames retained; author1000 development ->900train100validation,99000 test plus original1000 test cohort. Correlated MD frames, no independent-trajectory/new-molecule or GNN acceptance.")
        _json(output / "audit.json", report)
        _json(output / "report.json", report)
        return report
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        _json(output / "report.json", report)
        raise
