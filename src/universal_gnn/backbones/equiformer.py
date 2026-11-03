from __future__ import annotations

import math

import torch
from torch import nn

from universal_gnn.adapters.features import scalar_features
from universal_gnn.backbones.invariant import mlp
from universal_gnn.contracts import NativeFeatures
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.data.geometry import gaussian_basis, radius_graph, scatter_sum

o3 = load_o3()


class EquivariantFeedForward(nn.Module):
    def __init__(self, irreps):
        super().__init__()
        self.irreps = o3.Irreps(irreps)
        self.input = o3.Linear(irreps, irreps)
        self.gates = mlp(self.irreps.num_irreps, self.irreps.num_irreps)
        self.output = o3.Linear(irreps, irreps)

    def forward(self, nodes):
        values = self.input(nodes)
        gates = self.gates(scalar_features(values, str(self.irreps))).sigmoid()
        blocks, offset = [], 0
        for (multiplicity, irrep), block in zip(self.irreps, self.irreps.slices()):
            piece = values[:, block].reshape(len(values), multiplicity, irrep.dim)
            if irrep.l == 0:
                piece = nn.functional.silu(piece)
            piece = piece * gates[:, offset:offset + multiplicity, None]
            blocks.append(piece.flatten(1))
            offset += multiplicity
        return self.output(torch.cat(blocks, dim=-1))


class EquiformerBlock(nn.Module):
    """Single-head dot-product Equiformer variant with radial tensor-product key/values."""

    def __init__(self, irreps, radial):
        super().__init__()
        sh = o3.Irreps.spherical_harmonics(2)
        self.query = o3.Linear(irreps, irreps)
        self.key = o3.FullyConnectedTensorProduct(irreps, sh, irreps, shared_weights=False)
        self.value = o3.FullyConnectedTensorProduct(irreps, sh, irreps, shared_weights=False)
        self.radial = mlp(radial, self.key.weight_numel + self.value.weight_numel)
        self.output = o3.Linear(irreps, irreps)
        self.feedforward = EquivariantFeedForward(irreps)

    def forward(self, nodes, graph, harmonics, radial):
        n, dim = nodes.shape
        weights = self.radial(radial)
        key_weights, value_weights = weights.split([self.key.weight_numel, self.value.weight_numel], -1)
        pair = nodes[graph.src] + nodes[graph.dst]
        keys = self.key(pair, harmonics, key_weights)
        values = self.value(pair, harmonics, value_weights)
        logits = (self.query(nodes)[graph.dst] * keys).sum(-1) / math.sqrt(dim)
        maxima = nodes.new_full((n,), -torch.inf)
        maxima.scatter_reduce_(0, graph.dst, logits.detach(), reduce="amax", include_self=True)
        attention = torch.exp(logits - maxima[graph.dst]) * graph.weights
        denominator = scatter_sum(attention, graph.dst, n)[graph.dst] + 1e-12
        attention = attention / denominator
        messages = values * attention[:, None] * graph.weights[:, None]
        nodes = nodes + self.output(scatter_sum(messages, graph.dst, n))
        scale = torch.rsqrt(nodes.square().mean(-1, keepdim=True) + 1e-8)
        return nodes + self.feedforward(nodes * scale)


class EquiformerEncoder(nn.Module):
    kind = "equivariant"
    basis = "e3nn/component"
    transformation = "O3"
    gradient_capabilities = {"positions": True, "strain": True, "mixed": True}

    def __init__(self, width=32, layers=2, cutoff=4., radial=16, context_dim=0):
        super().__init__()
        channels = max(4, width // 4)
        self.irreps = f"{channels}x0e + {channels}x1o + {channels}x2e"
        self.cutoff, self.radial_count = cutoff, radial
        self.embedding = nn.Embedding(119, channels)
        self.initial = o3.Linear(f"{channels}x0e", self.irreps)
        self.condition = nn.Linear(context_dim, channels, bias=False) if context_dim else None
        self.blocks = nn.ModuleList([EquiformerBlock(self.irreps, radial) for _ in range(layers)])

    def encode(self, batch, context=None):
        graph = radius_graph(batch, self.cutoff)
        embedding = self.embedding(batch.numbers)
        if self.condition is not None:
            if context is None:
                raise ValueError("Equiformer conditioned encoder requires context")
            embedding = embedding + self.condition(context)[batch.batch]
        nodes = self.initial(embedding)
        harmonics = o3.spherical_harmonics(list(range(3)), graph.vectors,
                                          normalize=True, normalization="component")
        radial = gaussian_basis(graph.distances, self.radial_count, self.cutoff)
        for block in self.blocks:
            nodes = block(nodes, graph, harmonics, radial)
        return NativeFeatures(nodes, self.irreps, self.kind, batch.batch, batch.ptr, batch,
                              metadata={"implementation": "equiformer_dot_product_e3nn",
                                        "variant": "single_head_smooth_cutoff_native_torch"})

    forward = encode
