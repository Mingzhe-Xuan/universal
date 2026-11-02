from __future__ import annotations

import math

import torch
from torch import nn

from universal_gnn.adapters.features import invariant_width, scalar_features
from universal_gnn.backbones.invariant import mlp
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.data.geometry import scatter_mean, scatter_sum
from universal_gnn.properties import PropertySpec

o3 = load_o3()
from e3nn.io import CartesianTensor  # noqa: E402


def pool(values, features, spec):
    if spec.scope == "node":
        return values
    operation = scatter_sum if spec.reduction == "sum" else scatter_mean
    return operation(values, features.batch, features.geometry.num_graphs)


class PropertyReadout(nn.Module):
    def __init__(self, irreps: str, spec: PropertySpec):
        super().__init__()
        if spec.construction != "direct":
            raise ValueError("Derivative properties require ResponseReadout")
        self.irreps, self.spec = irreps, spec
        self.network = mlp(invariant_width(irreps), math.prod(spec.shape))

    def forward(self, features):
        values = self.network(scalar_features(features.nodes, self.irreps))
        values = pool(values, features, self.spec)
        return values.reshape(len(values), *self.spec.shape)


class ResponseReadout(nn.Module):
    def __init__(self, irreps: str, kind: str, spec: PropertySpec):
        super().__init__()
        if spec.construction != "derivative" or not spec.response_indices or not spec.auxiliary_indices:
            raise ValueError("A response requires explicit response/auxiliary indices")
        self.irreps, self.kind, self.spec = irreps, kind, spec
        self.response = CartesianTensor(spec.response_indices)
        self.auxiliary = CartesianTensor(spec.auxiliary_indices)
        self.response_size = 3 ** len(spec.response_indices)
        self.auxiliary_size = 3 ** len(spec.auxiliary_indices)
        if kind == "equivariant":
            self.coupling = o3.FullyConnectedTensorProduct(irreps, self.auxiliary, self.response)
        elif kind == "invariant":
            self.coefficients = mlp(invariant_width(irreps), self.response_size * self.auxiliary_size)
        else:
            raise ValueError(f"Unknown feature kind {kind}")

    def forward(self, features, *, create_graph: bool | None = None):
        create_graph = self.training if create_graph is None else create_graph
        with torch.enable_grad():
            if self.spec.scope == "node":
                nodes = features.nodes
            else:
                nodes = scatter_mean(features.nodes, features.batch, features.geometry.num_graphs)
            q = nodes.new_zeros((len(nodes), *([3] * len(self.spec.auxiliary_indices))), requires_grad=True)
            if self.kind == "equivariant":
                response_irreps = self.coupling(nodes, self.auxiliary.from_cartesian(q))
                response = self.response.to_cartesian(response_irreps).reshape(len(nodes), self.response_size)
            else:
                coefficients = self.coefficients(scalar_features(nodes, self.irreps))
                coefficients = coefficients.reshape(len(nodes), self.response_size, self.auxiliary_size)
                response = torch.einsum("brq,bq->br", coefficients, q.flatten(1))
            derivatives = [torch.autograd.grad(response[:, i].sum(), q, create_graph=create_graph,
                                               retain_graph=True)[0] for i in range(self.response_size)]
            result = torch.stack(derivatives, dim=1)
            return result.reshape(len(nodes), *self.spec.shape)
