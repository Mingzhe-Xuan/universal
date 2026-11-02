from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import torch
from torch import Tensor


@dataclass
class Structure:
    numbers: Tensor
    positions: Tensor
    cell: Tensor
    pbc: Tensor
    identifier: str
    targets: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        n = len(self.numbers)
        if n == 0 or self.numbers.shape != (n,) or self.positions.shape != (n, 3):
            raise ValueError(f"{self.identifier}: expected nonempty numbers[N], positions[N,3]")
        if self.numbers.dtype != torch.long or not bool((self.numbers > 0).all()):
            raise ValueError("Atomic numbers must be positive int64")
        if self.cell.shape != (3, 3) or self.pbc.shape != (3,):
            raise ValueError("Expected row cell[3,3] and pbc[3]")
        if not bool(torch.isfinite(self.positions).all() and torch.isfinite(self.cell).all()):
            raise ValueError("Nonfinite geometry")
        if abs(float(torch.linalg.det(self.cell.detach()))) < 1e-9:
            raise ValueError("Singular cell; use a nonsingular bounding cell for molecules")
        if self.positions.device != self.cell.device:
            raise ValueError("Positions and cells must be on the same device")


@dataclass
class StructureBatch:
    numbers: Tensor
    positions: Tensor
    cell: Tensor
    pbc: Tensor
    batch: Tensor
    ptr: Tensor
    identifiers: tuple[str, ...]
    targets: tuple[dict[str, Any], ...]
    metadata: tuple[dict[str, Any], ...]

    @classmethod
    def from_structures(cls, structures: list[Structure]) -> StructureBatch:
        if not structures:
            raise ValueError("Cannot batch an empty structure list")
        for structure in structures:
            structure.validate()
        device, dtype = structures[0].positions.device, structures[0].positions.dtype
        if any(s.positions.device != device or s.positions.dtype != dtype for s in structures):
            raise ValueError("All structures must share device and floating dtype")
        sizes = torch.tensor([len(s.numbers) for s in structures], device=device)
        ptr = torch.cat([sizes.new_zeros(1), sizes.cumsum(0)])
        return cls(
            torch.cat([s.numbers.to(device) for s in structures]),
            torch.cat([s.positions for s in structures]),
            torch.stack([s.cell.to(dtype=dtype) for s in structures]),
            torch.stack([s.pbc.to(device=device, dtype=torch.bool) for s in structures]),
            torch.repeat_interleave(torch.arange(len(structures), device=device), sizes),
            ptr,
            tuple(s.identifier for s in structures),
            tuple(s.targets for s in structures),
            tuple(s.metadata for s in structures),
        )

    @property
    def num_graphs(self) -> int:
        return len(self.identifiers)

    @property
    def natoms(self) -> Tensor:
        return self.ptr[1:] - self.ptr[:-1]

    def with_geometry(self, positions: Tensor, cell: Tensor) -> StructureBatch:
        if positions.shape != self.positions.shape or cell.shape != self.cell.shape:
            raise ValueError("Geometry replacement must preserve batch/atom dimensions")
        return replace(self, positions=positions, cell=cell)

    def to(self, device: str | torch.device, dtype: torch.dtype | None = None) -> StructureBatch:
        return replace(
            self,
            numbers=self.numbers.to(device),
            positions=self.positions.to(device=device, dtype=dtype),
            cell=self.cell.to(device=device, dtype=dtype),
            pbc=self.pbc.to(device),
            batch=self.batch.to(device),
            ptr=self.ptr.to(device),
        )


@dataclass
class NativeFeatures:
    nodes: Tensor
    irreps: str
    kind: str
    batch: Tensor
    ptr: Tensor
    geometry: StructureBatch
    graph_features: Tensor | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        from .e3nn_compat import load_o3

        o3 = load_o3()

        if self.nodes.shape != (len(self.geometry.numbers), o3.Irreps(self.irreps).dim):
            raise ValueError("Node dimensions do not match irreps and atom mapping")
        if self.kind not in {"invariant", "equivariant"}:
            raise ValueError("Unknown native feature kind")
        if self.kind == "invariant" and any(ir.l or ir.p != 1 for _, ir in o3.Irreps(self.irreps)):
            raise ValueError("Invariant node features must be even scalars")
