import torch
from torch import nn

from universal_gnn.contracts import BaseGNN, GNNOutput


class MolecularGCN(BaseGNN):
    def __init__(self, width=16, layers=2, context_dim=0):
        super().__init__(f"{width}x0e", "invariant", context_dim,
                         gradient_capabilities={"positions": True, "strain": True, "mixed": True})
        if width < 1 or layers < 1:
            raise ValueError("width and layers must be positive")
        self.element_embedding = nn.Embedding(119, width)
        self.layers = nn.ModuleList([nn.Linear(width, width) for _ in range(layers)])
        self.condition = nn.Linear(context_dim, width, bias=False) if context_dim else None

    def forward(self, graph, context=None):
        batch = graph.geometry
        nodes = self.element_embedding(batch.numbers)
        if self.condition is not None:
            nodes = nodes + self.condition(context)[batch.batch]
        keep = (graph.src != graph.dst) | (graph.cell_shifts != 0).any(-1)
        src, dst = graph.src[keep], graph.dst[keep]
        weights = torch.exp(-graph.vectors[keep].square().sum(-1))
        self_nodes = torch.arange(len(nodes), device=nodes.device)
        src, dst = torch.cat([src, self_nodes]), torch.cat([dst, self_nodes])
        weights = torch.cat([weights, weights.new_ones(len(nodes))])
        degree = weights.new_zeros(len(nodes)).index_add(0, dst, weights)
        normalized = weights / (degree[src] * degree[dst]).sqrt()
        for layer in self.layers:
            messages = layer(nodes)[src] * normalized[:, None]
            nodes = torch.nn.functional.silu(nodes.new_zeros(nodes.shape).index_add(0, dst, messages))
        return GNNOutput(nodes)
