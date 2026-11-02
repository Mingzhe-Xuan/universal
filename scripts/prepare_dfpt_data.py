"""Run raw-DFPT batch parsing on Slurm; append matched real execution cohorts."""

import argparse
import json
from pathlib import Path

from prepare_acceptance_data import Cohorts, digest, geometry_hash
from universal_gnn.data.dfpt import read_dfpt_zip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, default=Path("data/downloads/jarvis-dfpt"))
    parser.add_argument("--sources", type=Path, default=Path("data/downloads/dfpt-selected-source.json"))
    parser.add_argument("--output", type=Path, default=Path("data/acceptance"))
    args = parser.parse_args()
    sources = json.loads(args.sources.read_text())
    records, failures, seen = [], [], set()
    for index, source in enumerate(sources):
        try:
            record = read_dfpt_zip(args.downloads / (source["jid"] + ".zip"), source)
            if not 1 <= len(record["atoms"]["elements"]) <= 12:
                raise ValueError("Execution cohort atom count outside 1..12")
            key = geometry_hash(record)
            if key not in seen:
                seen.add(key)
                records.append((index, record))
        except Exception as error:
            failures.append({"id": source["jid"], "error": repr(error)})
        if len(records) == 10:
            break
    (args.output / "dfpt-parsing.json").write_text(json.dumps({"count": len(records), "failures": failures}, indent=2))
    cohorts = Cohorts(args.output)
    origin = {"dataset": "JARVIS published raw DFPT archives", "source_manifest_sha256": digest(args.sources),
              "definition": "Labels and geometry from the same vasprun.xml, no synthetic labels"}
    cohorts.save("forcefield", records, origin, {"kind": "forcefield"},
                 {"total_energy": {"key": "free_energy", "unit": "eV"},
                  "forces": {"key": "forces", "unit": "eV/angstrom"},
                  "stress": {"key": "stress_ase", "factor": 160.21766208, "unit": "GPa"}})
    cohorts.save("born_charge", records, origin,
                 {"kind": "supervised", "property": "born_charge", "route": "common_equivariant"},
                 {"born_charge": {"key": "born_effective_charges", "unit": "e"}})
    cohorts.save("dielectric_dfpt", records, origin,
                 {"kind": "supervised", "property": "dielectric", "route": "common_equivariant"},
                 {"dielectric": {"key": "dielectric_tensor", "unit": "dimensionless"}})
    path = args.output / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["tasks"].update(cohorts.tasks)
    for name in ["forcefield", "born_charge"]:
        manifest["pending"].pop(name, None)
    path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"structures": len(records), "tasks": list(cohorts.tasks), "failures": failures}))


if __name__ == "__main__":
    main()
