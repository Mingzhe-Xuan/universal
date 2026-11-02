"""Public graph and GNN protocol, independent of any third-party graph library."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Any, TYPE_CHECKING

import torch
from torch import Tensor, nn

if TYPE_CHECKING:
    from .types import StructureBatch


@dataclass
class GraphRecord:
    """One structure's local indices and optional invariant input features."""

    edge_index: Tensor
    cell_shifts: Tensor | None = None
    node_features: Tensor | None = None
    edge_features: Tensor | None = None

    def validate(self, natoms: int, pbc: Tensor):
        index = self.edge_index
        if not isinstance(index, Tensor) or index.dtype != torch.long or index.ndim != 2 or index.shape[0] != 2:
            raise ValueError("edge_index must be int64 [2,E]")
        if index.numel() and (int(index.min()) < 0 or int(index.max()) >= natoms):
            raise ValueError("edge_index contains an out-of-range atom index")
        if self.cell_shifts is not None:
            shifts = self.cell_shifts
            if not isinstance(shifts, Tensor) or shifts.dtype != torch.long or shifts.shape != (index.shape[1], 3):
                raise ValueError("cell_shifts must be int64 [E,3]")
            if bool((shifts[:, ~pbc.to(device=shifts.device, dtype=torch.bool)] != 0).any()):
                raise ValueError("Nonperiodic axes cannot have cell shifts")
        for name, value, length in [("node_features", self.node_features, natoms),
                                    ("edge_features", self.edge_features, index.shape[1])]:
            if value is not None and (not isinstance(value, Tensor) or not value.is_floating_point()
                                      or value.ndim != 2 or value.shape[0] != length
                                      or not bool(torch.isfinite(value).all())):
                raise ValueError(f"{name} must be finite floating [{length},F]")

    def to(self, device=None, dtype=None):
        return replace(self, edge_index=self.edge_index.to(device=device),
                       cell_shifts=self.cell_shifts.to(device=device) if self.cell_shifts is not None else None,
                       node_features=self.node_features.to(device=device, dtype=dtype) if self.node_features is not None else None,
                       edge_features=self.edge_features.to(device=device, dtype=dtype) if self.edge_features is not None else None)


@dataclass
class GraphBatch:
    geometry: StructureBatch
    edge_index: Tensor
    cell_shifts: Tensor
    node_features: Tensor | None = None
    edge_features: Tensor | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def src(self):
        return self.edge_index[0]

    @property
    def dst(self):
        return self.edge_index[1]

    @property
    def edge_batch(self):
        return self.geometry.batch[self.dst]

    @property
    def vectors(self):
        shifts = torch.einsum("ei,eij->ej", self.cell_shifts.to(self.geometry.cell.dtype),
                              self.geometry.cell[self.edge_batch])
        return self.geometry.positions[self.src] + shifts - self.geometry.positions[self.dst]

    @property
    def distances(self):
        return torch.linalg.vector_norm(self.vectors, dim=-1)

    def validate(self):
        GraphRecord(self.edge_index, self.cell_shifts, self.node_features, self.edge_features).validate(
            len(self.geometry.numbers), torch.ones(3, dtype=torch.bool, device=self.edge_index.device))
        if self.edge_index.device != self.geometry.positions.device or self.cell_shifts.device != self.edge_index.device:
            raise ValueError("Graph indices, shifts and geometry must share a device")
        if not torch.equal(self.geometry.batch[self.src], self.geometry.batch[self.dst]):
            raise ValueError("Edges cannot connect different structures")
        if bool(((self.cell_shifts != 0) & ~self.geometry.pbc[self.edge_batch]).any()):
            raise ValueError("Cell shifts violate the structure PBC flags")
        for value in [self.node_features, self.edge_features]:
            if value is not None and (value.device != self.geometry.positions.device
                                      or value.dtype != self.geometry.positions.dtype):
                raise ValueError("Graph features must share geometry dtype/device")


class BaseGraphBuilder(nn.Module, ABC):
    @abstractmethod
    def forward(self, batch: StructureBatch) -> GraphBatch:
        """Construct topology, preserving live geometry and original atom order."""


@dataclass
class GNNOutput:
    nodes: Tensor
    graph_features: Tensor | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseGNN(nn.Module, ABC):
    def __init__(self, irreps: str, kind: str, context_dim: int = 0):
        super().__init__()
        self.irreps, self.kind, self.context_dim = irreps, kind, context_dim
        if kind not in {"invariant", "equivariant"} or context_dim < 0:
            raise ValueError("GNN requires invariant/equivariant kind and nonnegative context_dim")

    @abstractmethod
    def forward(self, graph: GraphBatch, context: Tensor | None = None) -> GNNOutput:
        """Return unpooled node features, not downstream predictions."""
