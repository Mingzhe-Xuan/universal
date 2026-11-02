# Contracts

`Structure` stores one labelled structure; `StructureBatch` stores Cartesian positions in angstrom,
row-vector cells, atomic numbers and sample/atom mappings. Labels and their provenance remain
per structure so graph and ragged atom targets cannot be confused. `NativeFeatures` describes
unpooled Torch node features with explicit irreps and optional graph state.

Never detach geometry in a differentiable forward. Batch construction preserves tensor graphs;
`with_geometry` replaces geometry for strain and diffusion without changing atom identities.
