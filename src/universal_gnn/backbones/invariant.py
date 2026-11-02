from __future__ import annotations

import torch
from torch import Tensor, nn

from universal_gnn.contracts import NativeFeatures, StructureBatch
from universal_gnn.data.geometry import (
    gaussian_basis,
    radius_graph,
    scatter_mean,
    scatter_sum,
)


def mlp(input_dim: int, output_dim: int, hidden: int | None = None) -> nn.Sequential:
    hidden = hidden or max(input_dim, output_dim)
    return nn.Sequential(nn.Linear(input_dim, hidden), nn.SiLU(), nn.Linear(hidden, output_dim))


class GatedConvolution(nn.Module):
    def __init__(self, width: int, update_edges: bool = True):
        super().__init__()
        self.message = nn.Linear(3 * width, 2 * width)
        self.edge_update = mlp(3 * width, width) if update_edges else None
        self.norm = nn.LayerNorm(width)
        self.edge_norm = nn.LayerNorm(width) if update_edges else None

    def forward(self, nodes, edges, src, dst, weights):
        pair = torch.cat([nodes[dst], nodes[src], edges], dim=-1)
        gate, content = self.message(pair).chunk(2, dim=-1)
        messages = gate.sigmoid() * nn.functional.softplus(content) * weights[:, None]
        nodes = self.norm(nodes + scatter_sum(messages, dst, len(nodes)))
        if self.edge_update is not None:
            edges = self.edge_norm(edges + self.edge_update(pair))
        return nodes, edges


class InvariantEncoder(nn.Module):
    kind = "invariant"

    def __init__(self, width: int = 32, layers: int = 2, cutoff: float = 4.0,
                 radial: int = 24, context_dim: int = 0):
        super().__init__()
        self.width, self.layers_count, self.cutoff = width, layers, cutoff
        self.radial_count = radial
        self.node_embedding = nn.Embedding(119, width)
        self.edge_embedding = nn.Linear(radial, width)
        self.context_projection = nn.Linear(context_dim, width, bias=False) if context_dim else None
        self.irreps = f"{width}x0e"

    def initialize(self, batch: StructureBatch, context: Tensor | None):
        graph = radius_graph(batch, self.cutoff)
        nodes = self.node_embedding(batch.numbers)
        if self.context_projection is not None:
            if context is None or context.shape[0] != batch.num_graphs:
                raise ValueError("Encoder requires per-structure context")
            nodes = nodes + self.context_projection(context)[batch.batch]
        elif context is not None:
            raise ValueError("Context was supplied to an unconditioned encoder")
        edges = self.edge_embedding(gaussian_basis(graph.distances, self.radial_count, self.cutoff))
        return nodes, edges, graph

    def result(self, nodes, batch, state=None):
        return NativeFeatures(nodes, self.irreps, self.kind, batch.batch, batch.ptr, batch, state,
                              {"implementation": type(self).__name__, "cutoff": self.cutoff})

    def encode(self, batch: StructureBatch, context: Tensor | None = None) -> NativeFeatures:
        return self(batch, context)


class CGCNNEncoder(InvariantEncoder):
    """CGCNN gated neighbor aggregation; see README for normalization/cutoff variant."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.convolutions = nn.ModuleList([
            GatedConvolution(self.width, update_edges=False) for _ in range(self.layers_count)])

    def forward(self, batch, context=None):
        nodes, edges, graph = self.initialize(batch, context)
        # CGCNN uses fixed radial edges across its atom-update layers.
        for convolution in self.convolutions:
            nodes, _ = convolution(nodes, edges, graph.src, graph.dst, graph.weights)
        return self.result(nodes, batch)


class MEGNetBlock(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.edge = mlp(4 * width, width)
        self.node = mlp(3 * width, width)
        self.state = mlp(3 * width, width)
        self.norms = nn.ModuleList([nn.LayerNorm(width) for _ in range(3)])

    def forward(self, nodes, edges, state, batch, graph):
        edge_delta = self.edge(torch.cat(
            [nodes[graph.src], nodes[graph.dst], edges, state[graph.edge_batch]], dim=-1))
        edges = self.norms[0](edges + edge_delta)
        weighted_edges = edges * graph.weights[:, None]
        node_context = scatter_sum(weighted_edges, graph.dst, len(nodes))
        node_delta = self.node(torch.cat([nodes, node_context, state[batch.batch]], dim=-1))
        nodes = self.norms[1](nodes + node_delta)
        graph_nodes = scatter_mean(nodes, batch.batch, batch.num_graphs)
        graph_edges = scatter_sum(weighted_edges, graph.edge_batch, batch.num_graphs)
        state = self.norms[2](state + self.state(torch.cat([graph_nodes, graph_edges, state], dim=-1)))
        return nodes, edges, state


class MEGNetEncoder(InvariantEncoder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initial_state = nn.Parameter(torch.zeros(self.width))
        self.blocks = nn.ModuleList([MEGNetBlock(self.width) for _ in range(self.layers_count)])
        self.irreps = f"{2 * self.width}x0e"

    def forward(self, batch, context=None):
        nodes, edges, graph = self.initialize(batch, context)
        state = self.initial_state.expand(batch.num_graphs, -1)
        if self.context_projection is not None:
            state = state + self.context_projection(context)
        for block in self.blocks:
            nodes, edges, state = block(nodes, edges, state, batch, graph)
        return self.result(torch.cat([nodes, state[batch.batch]], dim=-1), batch, state)


class ALIGNNEncoder(InvariantEncoder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle_embedding = nn.Linear(self.radial_count, self.width)
        self.line_layers = nn.ModuleList([GatedConvolution(self.width) for _ in range(self.layers_count)])
        self.atom_layers = nn.ModuleList([GatedConvolution(self.width) for _ in range(self.layers_count)])

    def forward(self, batch, context=None):
        nodes, edges, graph = self.initialize(batch, context)
        first, second = graph.triplets()
        cosines = (graph.vectors[first] * graph.vectors[second]).sum(-1)
        cosines = cosines / (graph.distances[first] * graph.distances[second]).clamp_min(1e-12)
        angles = self.angle_embedding(gaussian_basis(cosines, self.radial_count, 1., -1.))
        relevance = graph.weights[first] * graph.weights[second]
        for line_layer, atom_layer in zip(self.line_layers, self.atom_layers):
            edges, angles = line_layer(edges, angles, first, second, relevance)
            nodes, edges = atom_layer(nodes, edges, graph.src, graph.dst, graph.weights)
        return self.result(nodes, batch)
