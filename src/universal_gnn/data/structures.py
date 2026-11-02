from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

from universal_gnn.contracts import Structure


def load_structures(path: str | Path, *, dtype=torch.float64, options=None) -> list[Structure]:
    """Read normalized JSON, JARVIS-style atom dictionaries, or labelled ASE files."""
    if str(path).startswith("plugin:"):
        from dataclasses import replace
        from universal_gnn.contracts.plugins import load_plugin

        module = load_plugin(str(path).removeprefix("plugin:"))
        structures = list(module.build_dataset(**(options or {})))
        if not structures or not all(isinstance(s, Structure) for s in structures):
            raise ValueError("Dataset plugin must return a nonempty iterable of Structure")
        result = []
        for structure in structures:
            structure = replace(structure, positions=structure.positions.to(dtype=dtype),
                                cell=structure.cell.to(dtype=dtype),
                                graph=structure.graph.to(device=structure.positions.device, dtype=dtype)
                                if structure.graph is not None else None,
                                metadata={**structure.metadata, "dataset_plugin": str(path)})
            structure.validate()
            result.append(structure)
        return result
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
    from universal_gnn.contracts.schema import validate_version
    from universal_gnn.data.formats import graph_record, validate_record

    version, dataset_metadata = None, {}
    if isinstance(records, dict):
        version = records.get("schema_version")
        if "schema_version" in records:
            validate_version(version, "dataset")
            if "structures" not in records:
                raise ValueError("Standard dataset envelope requires structures")
        dataset_metadata = records.get("metadata", {})
        if version is not None and not isinstance(dataset_metadata, dict):
            raise ValueError("Dataset metadata must be a mapping")
        records = records.get("structures", records.get("data"))
    if not isinstance(records, list):
        raise ValueError("Dataset must contain an explicit list of structures")
    result = []
    from ase.data import atomic_numbers

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("Each dataset structure must be a mapping")
        record_version = record.get("schema_version", version)
        if record_version is not None or "schema_version" in record:
            validate_version(record_version, "dataset")
            validate_record(record)
        atom = record.get("atoms", record)
        numbers = atom.get("numbers")
        if numbers is None:
            numbers = [atomic_numbers[element] for element in atom["elements"]]
        positions = torch.tensor(atom.get("positions", atom.get("coords")), dtype=dtype)
        cell_values = atom.get("cell", atom.get("lattice_mat"))
        pbc = torch.tensor(atom.get("pbc", [True, True, True]), dtype=torch.bool)
        metadata = {**record.get("metadata", {}), "source": str(path), "sha256": digest, "source_index": i}
        if dataset_metadata:
            metadata["dataset_metadata"] = dataset_metadata
        if cell_values is None:
            if bool(pbc.any()):
                raise ValueError("Periodic structures require an explicit cell")
            cell = torch.diag(positions.amax(0) - positions.amin(0) + 12.)
            metadata["cell_convention"] = "nonperiodic bounding cell; positions unchanged"
        else:
            cell = torch.tensor(cell_values, dtype=dtype)
        cartesian = atom.get("cartesian", "positions" in atom)
        if not cartesian:
            positions = positions @ cell
        targets = record.get("targets", {k: v for k, v in record.items() if k != "atoms"})
        identifier = str(record.get("id", record.get("jid", i)))
        structure = Structure(torch.tensor(numbers, dtype=torch.long), positions, cell, pbc,
                              identifier, targets, metadata,
                              graph_record(record["graph"], dtype=dtype) if record.get("graph") is not None else None)
        structure.validate()
        result.append(structure)
    if version is not None or any("schema_version" in record for record in records):
        identifiers = [structure.identifier for structure in result]
        if not result or len(set(identifiers)) != len(identifiers):
            raise ValueError("Standard datasets require nonempty structures and unique ids")
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
