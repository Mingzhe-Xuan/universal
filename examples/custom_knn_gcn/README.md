# Minimal KNN + GCN plugin

`plugin.py` exports `build_gnn(**options)` and `build_graph_builder(**options)`.
`model.py` implements `BaseGNN.forward(GraphBatch, context) -> GNNOutput`; `graph.py`
implements `BaseGraphBuilder.forward(StructureBatch) -> GraphBatch`.
The GNN returns unpooled even-scalar node features, with no task-specific prediction layer.
No edge features or third-party graph library are required. This example uses learned element
embeddings, distance-weighted GCN normalization and SiLU. Distance weights permit geometric
derivatives within a fixed topology; KNN neighbor changes/ties remain discrete.
The GNN explicitly declares position, strain and mixed parameter derivatives in
its `BaseGNN` constructor. These declarations permit forcefield construction;
actual finite differences and force-loss parameter gradients must still pass the
task's numerical gate. They add no learned layer or parameter. A nonperiodic
placeholder cell does not provide a bulk-stress accuracy label.

Select `backbone.name: plugin:examples/custom_knn_gcn` and
`graph.name: plugin:examples/custom_knn_gcn` using `configs/custom_knn_gcn.yaml`.
For imported edges, keep the same GNN and select `graph.name: stored`, with a GraphRecord for
every molecule. Nonperiodic molecules require `pbc: [false,false,false]`; this builder refuses PBC.
The reference-data preparation and Slurm validation scripts are described in scripts/README.md.

Input/output and file formats are defined in [docs/standards.md](../../docs/standards.md).
