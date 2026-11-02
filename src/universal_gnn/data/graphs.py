"""Graph construction/import for standard wrapped GNNs."""

import torch

from universal_gnn.contracts import BaseGraphBuilder, GraphBatch
from universal_gnn.data.geometry import radius_graph


def _features(batch, name):
    values = [getattr(record, name) if record is not None else None for record in batch.graphs]
    if not values or all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError(f"All structures must consistently provide {name}")
    if len({value.shape[1] for value in values}) != 1:
        raise ValueError(f"Inconsistent {name} widths")
    return torch.cat([value.to(batch.positions) for value in values])


def _rebuilt(batch, edge_index, shifts, metadata):
    if any(record is not None and record.edge_features is not None for record in batch.graphs):
        raise ValueError("Stored edge_features require graph.name=stored or a custom builder that remaps them")
    result = GraphBatch(batch, edge_index, shifts, _features(batch, "node_features"), metadata=metadata)
    result.validate()
    return result


class KNNGraphBuilder(BaseGraphBuilder):
    def __init__(self, k=3, symmetrize=True):
        super().__init__()
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("KNN k must be a positive integer")
        self.k, self.symmetrize = k, symmetrize

    def forward(self, batch):
        if bool(batch.pbc.any()):
            raise ValueError("Molecular KNN requires pbc=false; use radius or a periodic graph plugin")
        indices = []
        with torch.no_grad():
            for i in range(batch.num_graphs):
                start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
                n = end - start
                count = min(self.k, n - 1)
                if count == 0:
                    continue
                position = batch.positions[start:end]
                distance2 = (position[:, None] - position[None, :]).square().sum(-1)
                distance2.fill_diagonal_(torch.inf)
                source = torch.argsort(distance2, dim=1, stable=True)[:, :count].reshape(-1) + start
                destination = torch.arange(start, end, device=position.device).repeat_interleave(count)
                edges = torch.stack([source, destination])
                if self.symmetrize:
                    edges = torch.cat([edges, edges.flip(0)], dim=1)
                indices.append(edges)
        index = (torch.cat(indices, dim=1) if indices else
                 torch.empty((2, 0), dtype=torch.long, device=batch.positions.device))
        if index.numel():
            code = torch.unique(index[0] * len(batch.numbers) + index[1], sorted=True)
            index = torch.stack([code // len(batch.numbers), code % len(batch.numbers)])
        return _rebuilt(batch, index, index.new_zeros(index.shape[1], 3),
                        {"builder": "knn", "k": self.k, "symmetrize": self.symmetrize,
                         "tie_break": "stable local atom index"})


class RadiusGraphBuilder(BaseGraphBuilder):
    def __init__(self, cutoff=4.):
        super().__init__()
        self.cutoff = cutoff

    def forward(self, batch):
        graph = radius_graph(batch, self.cutoff)
        return _rebuilt(batch, graph.edge_index, graph.images, {"builder": "radius", "cutoff": self.cutoff})


class StoredGraphBuilder(BaseGraphBuilder):
    def forward(self, batch):
        if len(batch.graphs) != batch.num_graphs or any(graph is None for graph in batch.graphs):
            raise ValueError("graph.name=stored requires a GraphRecord for every structure")
        indices, shifts = [], []
        for i, graph in enumerate(batch.graphs):
            graph.validate(int(batch.natoms[i]), batch.pbc[i])
            graph = graph.to(device=batch.positions.device, dtype=batch.positions.dtype)
            indices.append(graph.edge_index + batch.ptr[i])
            shifts.append(graph.cell_shifts if graph.cell_shifts is not None else
                          graph.edge_index.new_zeros(graph.edge_index.shape[1], 3))
        result = GraphBatch(batch, torch.cat(indices, dim=1), torch.cat(shifts),
                            _features(batch, "node_features"), _features(batch, "edge_features"),
                            {"builder": "stored"})
        result.validate()
        return result


def make_graph_builder(config):
    config = dict(config)
    name = config.pop("name")
    factories = {"knn": KNNGraphBuilder, "radius": RadiusGraphBuilder, "stored": StoredGraphBuilder}
    if name in factories:
        return factories[name](**config)
    if name.startswith("plugin:"):
        from universal_gnn.contracts.plugins import load_plugin

        module = load_plugin(name.removeprefix("plugin:"))
        builder = module.build_graph_builder(**config)
        if not isinstance(builder, BaseGraphBuilder):
            raise TypeError("build_graph_builder must return a BaseGraphBuilder")
        builder.extension_provenance = {**module.__ugnn_provenance__, "factory": "build_graph_builder"}
        return builder
    raise ValueError(f"Unknown graph builder {name!r}")
