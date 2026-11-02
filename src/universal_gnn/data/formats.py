"""Canonical JSON dataset/graph serialization; legacy readers remain supported."""

import json
from pathlib import Path

import torch

from universal_gnn.contracts import GraphRecord
from universal_gnn.contracts.schema import validate_version


def graph_record(values, *, dtype=torch.float64):
    if not isinstance(values, dict) or "edge_index" not in values:
        raise ValueError("graph must contain edge_index")
    tensors = {}
    for name in ["edge_index", "cell_shifts"]:
        value = values.get(name)
        if value is None:
            tensors[name] = None
        else:
            tensor = torch.as_tensor(value)
            if tensor.numel() and tensor.dtype not in {torch.int32, torch.int64}:
                raise ValueError(f"{name} must contain integers")
            if name == "cell_shifts" and tensor.numel() == 0:
                tensor = tensor.reshape(0, 3)
            tensors[name] = tensor.long()
    for name in ["node_features", "edge_features"]:
        value = values.get(name)
        tensors[name] = torch.as_tensor(value, dtype=dtype) if value is not None else None
        if name == "edge_features" and tensors[name] is not None and tensors[name].shape == (0,):
            width = values.get("edge_features_width", 0)
            if not isinstance(width, int) or isinstance(width, bool) or width < 0:
                raise ValueError("edge_features_width must be a nonnegative integer")
            tensors[name] = tensors[name].reshape(0, width)
    if "schema_version" in values:
        validate_version(values["schema_version"], "graph")
    return GraphRecord(**tensors)


def graph_dict(graph):
    if graph is None:
        return None
    result = {name: getattr(graph, name).detach().cpu().tolist() for name in
            ["edge_index", "cell_shifts", "node_features", "edge_features"]
            if getattr(graph, name) is not None}
    result["schema_version"] = 1
    if graph.edge_features is not None and graph.edge_features.shape[0] == 0:
        result["edge_features_width"] = graph.edge_features.shape[1]
    return result


def validate_record(record):
    if not isinstance(record.get("id"), str) or not record["id"]:
        raise ValueError("Standard dataset records require a nonempty string id")
    if "numbers" not in record or "positions" not in record:
        raise ValueError("Standard records require numbers and Cartesian positions")
    if torch.as_tensor(record["numbers"]).dtype not in {torch.int32, torch.int64}:
        raise ValueError("Atomic numbers must be integers")
    position = torch.as_tensor(record["positions"])
    if len(record["numbers"]) == 0 or position.shape != (len(record["numbers"]), 3) or not bool(torch.isfinite(position).all()):
        raise ValueError("Standard positions must be finite [N,3] for nonempty atoms")
    pbc = record.get("pbc")
    if not isinstance(pbc, list) or len(pbc) != 3 or not all(isinstance(v, bool) for v in pbc):
        raise ValueError("Standard pbc must be three explicit booleans")
    if not isinstance(record.get("targets", {}), dict) or not isinstance(record.get("metadata", {}), dict):
        raise ValueError("targets and metadata must be mappings")
    for name, value in record.get("targets", {}).items():
        try:
            tensor = torch.as_tensor(value)
            valid = tensor.numel() > 0 and bool(torch.isfinite(tensor).all())
        except (TypeError, ValueError, RuntimeError):
            valid = False
        if not valid:
            raise ValueError(f"Standard target {name!r} must contain finite numeric values")


def save_structures(path, structures, *, metadata=None):
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("Dataset metadata must be a mapping")
    records = []
    for structure in structures:
        structure.validate()
        record = {"id": structure.identifier, "numbers": structure.numbers.detach().cpu().tolist(),
                  "positions": structure.positions.detach().cpu().tolist(),
                  "cell": structure.cell.detach().cpu().tolist(), "pbc": structure.pbc.cpu().tolist(),
                  "targets": structure.targets, "metadata": structure.metadata}
        if structure.graph is not None:
            record["graph"] = graph_dict(structure.graph)
        validate_record(record)
        records.append(record)
    identifiers = [record["id"] for record in records]
    if not records or len(set(identifiers)) != len(identifiers):
        raise ValueError("Standard datasets require nonempty structures with unique ids")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "metadata": metadata or {}, "structures": records}
    validate_version(payload["schema_version"], "dataset")
    path.write_text(json.dumps(payload, indent=2, allow_nan=False,
                               default=lambda value: value.tolist()), encoding="utf-8")
