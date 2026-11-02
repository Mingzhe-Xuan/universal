# Contracts

`Structure` stores one labelled structure; `StructureBatch` stores Cartesian positions in angstrom,
row-vector cells, atomic numbers and sample/atom mappings. Labels and their provenance remain
per structure so graph and ragged atom targets cannot be confused. `NativeFeatures` describes
unpooled Torch node features with explicit irreps and optional graph state.

Never detach geometry in a differentiable forward. Batch construction preserves tensor graphs;
`with_geometry` replaces geometry for strain and diffusion without changing atom identities.

## Standard graph/model extensions

`GraphRecord` describes local imported topology/attributes; `GraphBatch` carries live batched geometry.
`BaseGraphBuilder` and `BaseGNN` define extension input/output; `GNNOutput` carries unpooled nodes.
Shapes, versioning, code provenance and all file formats are defined together in
[docs/standards.md](../../../docs/standards.md).
