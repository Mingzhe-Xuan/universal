"""Minimal distance-weighted GCN; graph topology is supplied independently."""

import torch
from torch import nn

from universal_gnn.contracts import BaseGNN, GNNOutput
from universal_gnn.data.geometry import scatter_sum


class GCN(BaseGNN):
    def __init__(self, width=16, layers=2, context_dim=0, input_dim=None, distance_scale=1.):
        super().__init__(f"{width}x0e", "invariant", context_dim)
        self.gradient_capabilities = {"positions": True, "strain": True, "mixed": True}
        if width < 1 or layers < 1 or distance_scale <= 0:
            raise ValueError("GCN requires positive width, layers and distance_scale")
        self.input_dim, self.distance_scale = input_dim, distance_scale
        self.embedding = nn.Embedding(119, width) if input_dim is None else nn.Linear(input_dim, width)
        self.context = nn.Linear(context_dim, width, bias=False) if context_dim else None
        self.layers = nn.ModuleList([nn.Linear(width, width) for _ in range(layers)])

    def forward(self, graph, context=None):
        geometry = graph.geometry
        if self.input_dim is None:
            if graph.node_features is not None:
                raise ValueError("Set GCN input_dim to consume provided node_features")
            nodes = self.embedding(geometry.numbers)
        else:
            if graph.node_features is None or graph.node_features.shape[1] != self.input_dim:
                raise ValueError("GCN node_features do not match input_dim")
            nodes = self.embedding(graph.node_features)
        if self.context is not None:
            nodes = nodes + self.context(context)[geometry.batch]
        keep = (graph.src != graph.dst) | (graph.cell_shifts != 0).any(-1)
        src, dst = graph.src[keep], graph.dst[keep]
        weights = torch.exp(-graph.vectors[keep].square().sum(-1) / self.distance_scale ** 2)
        self_nodes = torch.arange(len(nodes), device=nodes.device)
        src, dst = torch.cat([src, self_nodes]), torch.cat([dst, self_nodes])
        weights = torch.cat([weights, weights.new_ones(len(nodes))])
        degree = scatter_sum(weights, dst, len(nodes))
        normalized = weights / (degree[src] * degree[dst]).sqrt()
        for layer in self.layers:
            nodes = torch.nn.functional.silu(scatter_sum(layer(nodes)[src] * normalized[:, None], dst, len(nodes)))
        return GNNOutput(nodes, metadata={"implementation": "distance-weighted GCN"})
