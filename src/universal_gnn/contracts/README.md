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

## Native prediction features v1

`components.py` defines `FeatureSpec`, `ReadoutRequirement`, static dimension discovery and
runtime `NativeFeatures` validation. Dimension precedence is feature_spec, irreps, model.feature_dim,
then config backbone.feature_dim; all supplied dimensions must agree. Width alone does not describe
non-scalar representations. Basis/transformation and position/strain/mixed derivative capabilities
are explicit. New prediction assembly validates native nodes before any readout; optional graph
features are preserved and the built-in heads declare that they do not consume them.
# Original-head task contract

`native.NativeTaskContract` declares the original property, scope, shape, kind,
unit, reduction, head module paths, pooling, normalization and artifact hashes.
`native` selection validates the complete task contract, not merely output width.
Custom providers can implement `native_task_contract()` and
`native_prediction(batch, contract)` using the same protocol. Providers without
an explicit verified contract must use `head_mode: reset`.

`NativeFeatures.validate()` raises `FloatingPointError` for NaN/Inf node or graph
values. Shape, basis, atom mapping and dtype/device violations remain structural
errors. Generation quality counts the numerical failure as an invalid attempted
sample; structural failures and CUDA OOM still stop evaluation. This distinction
does not accept nonfinite features during training or inference.
