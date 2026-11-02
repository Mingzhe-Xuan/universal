"""Ten real ASE G2-1 molecules/experimental ionization energies; run preprocessing on Slurm."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import ase
from ase import Atoms
from ase.data import g2_1
import torch

from universal_gnn.contracts import GraphRecord, Structure, StructureBatch
from universal_gnn.data.formats import save_structures
from universal_gnn.data.graphs import make_graph_builder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/acceptance"))
    args = parser.parse_args()
    module_path = Path(g2_1.__file__)
    source = {"dataset": "ASE G2-1", "ase_version": ase.__version__,
              "source_module": "ase.data.g2_1", "source_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
              "source_url": "https://gitlab.com/ase/ase/-/blob/master/ase/data/g2_1.py",
              "experimental_reference": "https://cccbdb.nist.gov/",
              "geometry": "published G2-1 MP2(full)/6-31G(d) geometry, no new calculation",
              "label": "published ionization energy, not vertical ionization energy", "unit": "eV"}
    records = []
    for name in ["N2", "O2", "F2", "HF", "H2O", "NH3", "CH4", "CO", "CO2", "C2H2"]:
        row = g2_1.data[name]
        atoms = Atoms(row["symbols"], positions=row["positions"], pbc=False)
        positions = torch.tensor(atoms.positions, dtype=torch.float64)
        cell = torch.diag(positions.amax(0) - positions.amin(0) + 12.)
        records.append(Structure(torch.tensor(atoms.numbers, dtype=torch.long), positions, cell,
                                 torch.zeros(3, dtype=torch.bool), name,
                                 {"ionization_energy": float(row["ionization energy"])},
                                 {"upstream": source, "upstream_id": name,
                                  "cell_convention": "nonperiodic bounding cell; positions unchanged"}))
    save_structures(args.output / "molecules-g2-10.json", records, metadata=source)
    builder = make_graph_builder({"name": "plugin:examples/custom_knn_gcn", "k": 2})
    imported = []
    for record in records:
        graph = builder(StructureBatch.from_structures([record]))
        imported.append(replace(record, graph=GraphRecord(graph.edge_index, graph.cell_shifts)))
    save_structures(args.output / "molecules-g2-10-graphs.json", imported, metadata=source)
    print(json.dumps({"structures": len(records), "ids": [r.identifier for r in records], "source": source}))


if __name__ == "__main__":
    main()
