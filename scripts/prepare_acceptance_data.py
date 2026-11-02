"""Curate ten real structures per output route; never synthesize missing labels.

Reads the official downloaded JARVIS archives and author-published GMTNet data.
Selection stops after the required small cohort; large preprocessing belongs in Slurm.
"""

import argparse
from collections import OrderedDict
import hashlib
import io
import json
import math
from numbers import Real
from pathlib import Path
import pickle
import zipfile


class TensorDataUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) == ("collections", "OrderedDict"):
            return OrderedDict
        if (module, name) in {("numpy", "dtype"), ("numpy", "ndarray"),
                              ("numpy.core.multiarray", "scalar"),
                              ("numpy.core.multiarray", "_reconstruct")}:
            import numpy as np

            return {"dtype": np.dtype, "ndarray": np.ndarray, "scalar": np.core.multiarray.scalar,
                    "_reconstruct": np.core.multiarray._reconstruct}[name]
        raise pickle.UnpicklingError(f"Unexpected object in plain tensor dataset: {module}.{name}")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def json_list(stream):
    decoder = json.JSONDecoder()
    buffer = stream.read(65536).lstrip()
    if not buffer.startswith("["):
        raise ValueError("Expected JSON list")
    buffer = buffer[1:]
    while True:
        buffer = buffer.lstrip()
        if buffer.startswith(","):
            buffer = buffer[1:].lstrip()
        if buffer.startswith("]"):
            return
        try:
            record, end = decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            more = stream.read(65536)
            if not more:
                raise ValueError("Truncated JSON list") from None
            buffer += more
            continue
        yield record
        buffer = buffer[end:]


def zip_records(path):
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".json")]
        if len(names) != 1:
            raise ValueError("Expected exactly one JSON member")
        with archive.open(names[0]) as binary:
            yield from json_list(io.TextIOWrapper(binary, encoding="utf-8"))


def finite(value):
    if isinstance(value, (list, tuple)):
        return bool(value) and all(finite(item) for item in value)
    return isinstance(value, Real) and math.isfinite(value)


def small(record):
    return 1 <= len(record["atoms"]["elements"]) <= 12


def geometry_hash(record):
    atoms = record["atoms"]
    value = {key: atoms[key] for key in ["lattice_mat", "coords", "elements", "cartesian"] if key in atoms}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Cohorts:
    def __init__(self, output):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.tasks = {}

    def save(self, name, records, source, task, bindings=None):
        if len(records) != 10:
            raise ValueError(f"{name}: requires ten structures, found {len(records)}")
        normalized = []
        seen = set()
        for index, record in records:
            key = geometry_hash(record)
            if key in seen:
                raise ValueError(f"{name}: duplicate geometry")
            seen.add(key)
            identifier = str(record.get("JARVIS_ID", record.get("jid", index)))
            normalized.append({"id": f"{identifier}:source-{index}", "atoms": record["atoms"],
                               "targets": {key: value for key, value in record.items()
                                           if key not in {"atoms", "metadata"}},
                               "metadata": {**record.get("metadata", {}),
                                            "upstream_id": identifier, "upstream_index": index,
                                            "upstream": source}})
        path = self.output / f"{name}-10.json"
        path.write_text(json.dumps(normalized, indent=2,
                                   default=lambda value: value.tolist()), encoding="utf-8")
        dataset = {"path": path.as_posix(), "sha256": digest(path)}
        if bindings:
            dataset["bindings"] = bindings
        self.tasks[name] = {"dataset": dataset, "task": task, "selection": "ten distinct small real structures"}


def source(path, url, definition):
    return {"url": url, "sha256": digest(path), "definition": definition}


def select(records, predicate):
    result, seen = [], set()
    for index, record in enumerate(records):
        if not small(record) or not predicate(record):
            continue
        key = geometry_hash(record)
        if key in seen:
            continue
        seen.add(key)
        result.append((index, record))
        if len(result) == 10:
            break
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, default=Path("data/downloads"))
    parser.add_argument("--examples", type=Path,
                        default=Path("tmp/alignn2-audit/alignn/alignn/examples"))
    parser.add_argument("--output", type=Path, default=Path("data/acceptance"))
    args = parser.parse_args()
    cohorts = Cohorts(args.output)
    path = args.downloads / "jarvis-dft3d-38521619.zip"
    origin = source(path, "https://ndownloader.figshare.com/files/38521619", "JARVIS DFT 2022 release")
    for name, field, unit in [("formation_energy", "formation_energy_peratom", "eV/atom"),
                               ("bandgap", "optb88vdw_bandgap", "eV")]:
        cohort = select(zip_records(path), lambda record: finite(record.get(field)))
        cohorts.save(name, cohort, origin, {"kind": "supervised", "property": name},
                     {name: {"key": field, "unit": unit}})
    cohorts.save("generation", cohort, origin, {"kind": "generation",
                 "sampling": {"steps": 12, "inner_steps": 2}})
    balanced = [[], []]
    for index, record in enumerate(zip_records(path)):
        value = record.get("optb88vdw_bandgap")
        if small(record) and finite(value):
            group = int(value > .1)
            if len(balanced[group]) < 5:
                balanced[group].append((index, record))
        if all(len(group) == 5 for group in balanced):
            break
    cohorts.save("classification", balanced[0] + balanced[1], origin,
                 {"kind": "supervised", "property": "classification"},
                 {"classification": {"key": "optb88vdw_bandgap", "threshold": .1, "unit": "class"}})

    for name, filename, field, binding in [
        ("dielectric", "gmtnet-jarvis-diele-piezo.pkl", "dielectric", {"unit": "dimensionless"}),
        ("piezoelectric", "gmtnet-jarvis-diele-piezo.pkl", "piezoelectric_C_m2",
         {"unit": "C/m^2", "voigt": True, "voigt_order": "vasp"}),
        ("elastic", "gmtnet-jarvis-elastic.pkl", "elastic_total_kbar",
         {"unit": "GPa", "factor": .1, "voigt": True, "voigt_order": "vasp"}),
    ]:
        path = args.downloads / filename
        upstream = "jarvis_elastic.pkl" if name == "elastic" else "jarvis_diele_piezo.pkl"
        origin = source(path, f"https://raw.githubusercontent.com/YKQ98/GMTNet/main/data/{upstream}",
                        f"GMTNet curated JARVIS field {field}; original VASP index order")
        with path.open("rb") as stream:
            records = TensorDataUnpickler(stream).load()
        def valid(record):
            values = record.get(field)
            if not finite(values):
                return False
            if name == "piezoelectric":
                return max(abs(item) for row in values for item in row) > .01
            return True
        cohorts.save(name, select(records, valid), origin, {"kind": "supervised", "property": name},
                     {name: {"key": field, **binding}})

    path = args.downloads / "jarvis-edos-pdos-29216859.zip"
    origin = source(path, "https://ndownloader.figshare.com/files/29216859",
                    "Upstream interpolated vectors retained without resampling or renormalization")
    for name, field, channels in [("electron_dos", "edos_up", 300), ("phonon_dos", "pdos_elast", 200)]:
        cohort = select(zip_records(path), lambda record: finite(record.get(field)) and len(record[field]) == channels)
        cohorts.save(name, cohort, origin, {"kind": "supervised", "property": "spectrum", "channels": channels},
                     {"spectrum": {"key": field, "unit": "dataset_defined"}})

    path = args.examples / "sample_data_atomwise/id_prop.json"
    origin = source(path, "https://github.com/atomgptlab/alignn/blob/main/alignn/examples/sample_data_atomwise/id_prop.json",
                    "Author example atomwise DFT labels, retained verbatim")
    records = json.loads(path.read_text(encoding="utf-8"))
    for name, field, unit in [("atom_charge", "charges", "e"), ("atom_moment", "magmoms", "mu_B")]:
        cohort = select(records, lambda record: finite(record.get(field)))
        cohorts.save(name, cohort, origin, {"kind": "supervised", "property": "atom_scalar", "unit": unit},
                     {"atom_scalar": {"key": field, "unit": unit}})
    manifest = {"tasks": cohorts.tasks,
                "pending": {"forcefield": "Confirm upstream stress convention before binding",
                            "born_charge": "Acquire true per-atom DFPT Born tensors",
                            "raman": "Acquire true Raman intensity curves"},
                "interpretation": "ten-structure execution cohorts; no benchmark split or generalization claim"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"tasks": list(cohorts.tasks), "structures_each": 10}))


if __name__ == "__main__":
    main()
