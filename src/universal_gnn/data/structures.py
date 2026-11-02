from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

from universal_gnn.contracts import Structure


def load_structures(path: str | Path, *, dtype=torch.float64) -> list[Structure]:
    """Read normalized JSON, JARVIS-style atom dictionaries, or labelled ASE files."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.suffix.lower() not in {".json", ".jsonl"}:
        from ase.io import read

        result = []
        for i, atoms in enumerate(read(path, index=":")):
            targets = dict(atoms.info)
            targets.update({key: value.tolist() for key, value in atoms.arrays.items()
                            if key not in {"numbers", "positions"}})
            if atoms.calc is not None:
                targets.update({key: value.tolist() if hasattr(value, "tolist") else value
                                for key, value in atoms.calc.results.items()})
            cell = atoms.cell.array
            if abs(float(torch.linalg.det(torch.as_tensor(cell)))) < 1e-9:
                atoms = atoms.copy()
                atoms.center(vacuum=6.)
                cell = atoms.cell.array
            result.append(Structure(torch.tensor(atoms.numbers, dtype=torch.long),
                                    torch.tensor(atoms.positions, dtype=dtype),
                                    torch.tensor(cell, dtype=dtype), torch.tensor(atoms.pbc),
                                    str(targets.get("id", f"{path.stem}-{i}")), targets,
                                    {"source": str(path), "sha256": digest, "source_index": i}))
        return result
    records = ([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
               if path.suffix == ".jsonl" else json.loads(path.read_text(encoding="utf-8")))
    if isinstance(records, dict):
        records = records.get("structures", records.get("data"))
    if not isinstance(records, list):
        raise ValueError("Dataset must contain an explicit list of structures")
    result = []
    from ase.data import atomic_numbers

    for i, record in enumerate(records):
        atom = record.get("atoms", record)
        numbers = atom.get("numbers")
        if numbers is None:
            numbers = [atomic_numbers[element] for element in atom["elements"]]
        cell = torch.tensor(atom.get("cell", atom.get("lattice_mat")), dtype=dtype)
        positions = torch.tensor(atom.get("positions", atom.get("coords")), dtype=dtype)
        cartesian = atom.get("cartesian", "positions" in atom)
        if not cartesian:
            positions = positions @ cell
        targets = record.get("targets", {k: v for k, v in record.items() if k != "atoms"})
        identifier = str(record.get("id", record.get("jid", i)))
        result.append(Structure(torch.tensor(numbers, dtype=torch.long), positions, cell,
                                torch.tensor(atom.get("pbc", [True, True, True]), dtype=torch.bool),
                                identifier, targets, {**record.get("metadata", {}),
                                "source": str(path), "sha256": digest, "source_index": i}))
    return result


VOIGT = [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
VASP_VOIGT = [(0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (0, 2)]


def expand_voigt(values: torch.Tensor, kind: str, order: str = "standard") -> torch.Tensor:
    """Expand labelled symmetric index pairs; does not constrain model predictions."""
    if order not in {"standard", "vasp"}:
        raise ValueError("voigt_order must be standard (xx,yy,zz,yz,xz,xy) or vasp (xx,yy,zz,xy,yz,zx)")
    pairs = VASP_VOIGT if order == "vasp" else VOIGT
    if kind == "stress" and values.shape == (6,):
        result = values.new_zeros(3, 3)
        for k, (i, j) in enumerate(pairs):
            result[i, j] = result[j, i] = values[k]
        return result
    if kind == "piezoelectric" and values.numel() == 18:
        result = values.new_zeros(3, 3, 3)
        for k, (i, j) in enumerate(pairs):
            result[:, i, j] = result[:, j, i] = values.reshape(3, 6)[:, k]
        return result
    if kind == "elastic" and values.numel() == 36:
        result = values.new_zeros(3, 3, 3, 3)
        for a, (i, j) in enumerate(pairs):
            for b, (k, l) in enumerate(pairs):
                for p, q in {(i, j), (j, i)}:
                    for r, s in {(k, l), (l, k)}:
                        result[p, q, r, s] = values.reshape(6, 6)[a, b]
        return result
    return values


def bind_targets(structures: list[Structure], bindings: dict) -> list[Structure]:
    """Bindings explicitly specify source keys, transforms, units and conventions."""
    from dataclasses import replace

    result = []
    for structure in structures:
        targets = {}
        for output, binding in bindings.items():
            if isinstance(binding, str):
                binding = {"key": binding}
            key = binding["key"]
            if key not in structure.targets:
                raise ValueError(f"{structure.identifier}: missing target {key}")
            value = torch.as_tensor(structure.targets[key], dtype=structure.positions.dtype)
            value = value * binding.get("factor", 1.0)
            if binding.get("per_atom_to_total"):
                value = value * len(structure.numbers)
            if "threshold" in binding:
                value = (value > binding["threshold"]).long()
            if binding.get("voigt"):
                value = expand_voigt(value, output, binding.get("voigt_order", "standard"))
            targets[output] = value
        result.append(replace(structure, targets=targets,
                              metadata={**structure.metadata, "target_bindings": bindings}))
    return result
