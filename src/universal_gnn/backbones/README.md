# Backbones

`blueprints.py` prepares native constructor arguments without importing model
libraries. It retains architectural settings and replaces fitted energy shifts,
scales and atomic reference energies with fresh constants. Native neighbor counts
must come from the complete declared training partition, with source/manifest/ID
fingerprints, dtype and the original cutoff. MACE uses edges/nonzero receivers;
NequIP uses edges/all nodes, matching their native statistics conventions.
The NequIP helper extracts only the author's original GNN recipe, supplies the
current seed, and omits nonpersistent accelerator modifiers for eager construction.
These helpers do not construct or numerically validate a network. The complete
fresh-provider and engine-calibration paths still require Slurm acceptance.
This package lazily resolves the existing invariant encoder aliases, preserving
their original class identities while allowing metadata-only imports.

All encoders return unpooled `NativeFeatures`. The six canonical names select the original
[official providers](official/README.md) by default. Published weights must be prepared in the
profile cache or specified explicitly; missing weights/dependencies fail without a fallback.
Original preprocessing, normalization and model modules stay intact; only the feature boundary
and new task readouts are adapted. Official context is appended after the original backbone.

## Explicit legacy variants

The following implementations require `implementation: legacy`. Old UGNN checkpoints without
an official artifact retain these implementations automatically. Their historical execution
matrix is separate from official-checkpoint validation. Legacy scalar context is projected into
the initial embedding before message passing; geometry is computed live.

`CGCNNEncoder`, `MEGNetEncoder`, and `ALIGNNEncoder` implement their respective gated graph,
node/edge/global graph-network, and alternating crystal/line-graph architectures in native Torch.
LayerNorm replaces batch-wide normalization to keep independent structures isolated; smooth
cutoff weights replace abrupt neighbor truncation. These are explicitly recorded implementation
variants, not checkpoint-compatible copies of the original packages. Element embeddings are learned.
`MACEEncoder` uses official MACE interaction/product blocks; `NequIPEncoder` uses the official
embedding/convolution stack before its scalar-only final block. Version/layout mismatch fails.
`EquiformerEncoder` implements the dot-product-attention architecture variant with spherical
tensor-product key/values, invariant attention, equivariant feedforward, a single head and smooth
cutoffs. It is a documented Torch/e3nn reimplementation, not the original OCP checkpoint format.
None of the equivariant backends are substituted with an invariant encoder. All six passed the recorded ten-structure training/inference matrix; this is execution
acceptance and does not imply original-package checkpoint compatibility or benchmark accuracy.

Sources: [MACE](https://github.com/ACEsuit/mace), [NequIP](https://github.com/mir-group/nequip),
[Equiformer dot-product variant](https://github.com/atomicarchitects/equiformer/blob/master/nets/dp_attention_transformer.py),
[CGCNN](https://github.com/txie-93/cgcnn), [MEGNet](https://github.com/materialyzeai/megnet),
[ALIGNN](https://github.com/atomgptlab/alignn).

## User GNNs and independent graphs

`StandardBackbone(BaseGNN, BaseGraphBuilder)` converts GNNOutput to NativeFeatures and validates
shape, precision/device and mappings before the existing readouts. `gcn` is a minimal distance-weighted
GCN; `plugin:/directory` may expose `build_gnn(**options)` with the same protocol. A top-level graph
configuration is supported for these wrapped models. Native backbones continue building their own
required graphs; unsupported overrides fail explicitly. Legacy build_backbone plugins remain readable.
See [the single standard](../../../docs/standards.md) and examples/custom_knn_gcn.

## Native output metadata

New prediction assembly reads feature_spec/irreps/feature_dim and transformation/gradient metadata;
config backbone.feature_dim is an assertion/fallback, never a hidden-layer width override. Standard
custom GNNs may omit irreps only for explicitly invariant scalar features, declaring feature_dim.
All encoders still return unpooled NativeFeatures in input atom order. See contracts/components.py.

## Original constructor statistics

`blueprints.aggregate_native_neighbor_counts` aggregates counts supplied by the original graph
preprocessor and requires the complete declared training partition. Its receipt records the source,
manifest and training fingerprints, precision and native cutoff. Individual isolated structures are
included: MACE normalizes by receivers with neighbors, whereas NequIP includes all nodes in the
denominator. Inconsistent per-structure counts and a completely edgeless training partition fail.
This helper does not construct graphs or establish which records were scanned; the caller must
verify the receipt against the selected training data. Original graph scanning and automatic training
integration require separate runtime validation before being described as supported scratch training.

`blueprints.nequip_full_constructor_config` prepares parameters for the original
`nequip.model.FullNequIPGNNModel` using the author recipe and a layout extracted from the original
package modules. OAM-S's `[128, 64]` specifies angular-order multiplicities: its type embedding is
32 even scalars, its first hidden layer is `128x0e + 64x1e`, and its final layer is `128x0e`.
The installed 0.14 simplified builder cannot accept that list and separate embedding width;
the [official 0.15 simplified builder](https://github.com/mir-group/nequip/blob/v0.15.0/nequip/model/nequip_models.py)
has the same restriction. Use the original full builder with explicit irreps and radial settings.
The converter rejects disagreement between the package layout and recipe rather than guessing
successive layer widths. It resets seed, energy shift/scale and training-fitted neighbor statistics
according to the existing scratch policy, retaining species, cutoff, ZBL and trainability flags.
Five stdlib conversion tests passed locally and in Slurm887 with executed-source hashes verified;
constructor integration, strict state-layout and numerical
acceptance still await Slurm. Metadata conversion alone does not establish usable scratch training.
