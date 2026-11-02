"""Wrap a graph builder and user GNN in the framework's pre-readout encoder contract."""

import math

from torch import nn

from universal_gnn.contracts import BaseGNN, BaseGraphBuilder, GNNOutput, NativeFeatures


class StandardBackbone(nn.Module):
    def __init__(self, gnn: BaseGNN, graph_builder: BaseGraphBuilder, *, cutoff=4.):
        super().__init__()
        if not isinstance(gnn, BaseGNN) or not isinstance(graph_builder, BaseGraphBuilder):
            raise TypeError("StandardBackbone requires BaseGNN and BaseGraphBuilder instances")
        if not math.isfinite(cutoff) or cutoff <= 0:
            raise ValueError("Adapter geometry cutoff must be positive and finite")
        self.gnn, self.graph_builder = gnn, graph_builder
        self.irreps, self.kind, self.cutoff = gnn.irreps, gnn.kind, cutoff
        self.context_dim = gnn.context_dim
        self.extension_provenance = {}
        for role, component in [("gnn", gnn), ("graph", graph_builder)]:
            if hasattr(component, "extension_provenance"):
                self.extension_provenance[role] = component.extension_provenance

    def encode(self, batch, context=None):
        return self(batch, context)

    def forward(self, batch, context=None):
        if self.context_dim:
            if context is None or context.shape != (batch.num_graphs, self.context_dim):
                raise ValueError(f"GNN requires context [B,{self.context_dim}]")
        elif context is not None:
            raise ValueError("Context supplied to an unconditioned GNN")
        graph = self.graph_builder(batch)
        if graph.geometry is not batch:
            raise ValueError("Graph builder must preserve the provided StructureBatch geometry")
        graph.validate()
        output = self.gnn(graph, context)
        if not isinstance(output, GNNOutput):
            raise TypeError("GNN.forward must return GNNOutput")
        features = NativeFeatures(output.nodes, self.irreps, self.kind, batch.batch, batch.ptr, batch,
                                  output.graph_features, {**output.metadata, "graph": graph.metadata,
                                                          "protocol_version": 1})
        features.validate()
        return features
