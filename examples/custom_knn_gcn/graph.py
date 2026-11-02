import torch

from universal_gnn.contracts import BaseGraphBuilder, GraphBatch


class MolecularKNN(BaseGraphBuilder):
    def __init__(self, k=2):
        super().__init__()
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("k must be a positive integer")
        self.k = k

    def forward(self, batch):
        if bool(batch.pbc.any()):
            raise ValueError("This example KNN accepts nonperiodic molecules only")
        if any(g is not None and (g.node_features is not None or g.edge_features is not None) for g in batch.graphs):
            raise ValueError("This minimal example uses element embeddings, not stored attributes")
        edges = []
        with torch.no_grad():
            for i in range(batch.num_graphs):
                start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
                n = end - start
                if n < 2:
                    continue
                position = batch.positions[start:end]
                squared = (position[:, None] - position[None, :]).square().sum(-1)
                squared.fill_diagonal_(torch.inf)
                k = min(self.k, n - 1)
                src = torch.argsort(squared, dim=1, stable=True)[:, :k].flatten() + start
                dst = torch.arange(start, end, device=position.device).repeat_interleave(k)
                edges.extend([torch.stack([src, dst]), torch.stack([dst, src])])
        index = (torch.cat(edges, dim=1) if edges else batch.numbers.new_empty(2, 0))
        code = torch.unique(index[0] * len(batch.numbers) + index[1], sorted=True)
        index = torch.stack([code // len(batch.numbers), code % len(batch.numbers)])
        return GraphBatch(batch, index, index.new_zeros(len(code), 3),
                          metadata={"builder": "example molecular KNN", "k": self.k})
