"""Indexed JSONL access and lazy selection/target binding for training and inference."""

from collections.abc import Sequence
import hashlib
import json
from pathlib import Path

import torch

from universal_gnn.data.structures import bind_targets, load_structures, structure_from_record


class JSONLStructures(Sequence):
    def __init__(self, path, *, dtype=torch.float32):
        self.path, self.dtype = Path(path), dtype
        self.offsets = []
        digest, identifiers = hashlib.sha256(), set()
        standard, duplicate = False, False
        with self.path.open("rb") as stream:
            while True:
                offset = stream.tell()
                line = stream.readline()
                if not line:
                    break
                digest.update(line)
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("Each JSONL record must be a structure mapping")
                standard = standard or "schema_version" in record
                identifier = str(record.get("id", record.get("jid", len(self.offsets))))
                duplicate = duplicate or identifier in identifiers
                identifiers.add(identifier)
                self.offsets.append(offset)
        if standard and duplicate:
            raise ValueError("Standard datasets require unique ids")
        self.sha256 = digest.hexdigest()
        if not self.offsets:
            raise ValueError("Dataset must not be empty")

    def __len__(self):
        return len(self.offsets)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return SelectedStructures(self, range(len(self))[index])
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        with self.path.open("rb") as stream:
            stream.seek(self.offsets[index])
            record = json.loads(stream.readline())
        return structure_from_record(record, index, self.path, self.sha256, self.dtype)


class SelectedStructures(Sequence):
    def __init__(self, source, indices=None, bindings=None):
        self.source = source
        self.indices = range(len(source)) if indices is None else indices
        self.bindings = bindings

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return SelectedStructures(self.source, self.indices[index], self.bindings)
        structure = self.source[self.indices[index]]
        return bind_targets([structure], self.bindings)[0] if self.bindings is not None else structure


def open_structures(path, *, dtype=torch.float32, options=None):
    if not str(path).startswith("plugin:") and Path(path).suffix.lower() == ".jsonl":
        return JSONLStructures(path, dtype=dtype)
    return load_structures(path, dtype=dtype, options=options)
