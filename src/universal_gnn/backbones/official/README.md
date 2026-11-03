# Official pretrained backbones

This module is the default route for the six canonical model names. Providers are not declared
verified until published-checkpoint and ten-real-structure Slurm evidence has been recorded.

Providers load the original architecture and all its parameters and buffers, and call the original
forward. No normalization, element encoding, interaction block, cutoff envelope or graph rule is
replaced to fit UGNN. Node features are exposed before native pooling/readout. Optional conditioning
is appended at the output adapter, outside the original backbone. Feature extraction retains the
input autograd graph, including when parameter training is disabled.

`OfficialBackbone` supplies NativeFeatures, provenance and exact source artifact hashes. Original
artifact bytes are embedded in UGNN checkpoints so reconstructing the model does not require the
original download path. Official serialization may require the corresponding pinned package/source
version. An unsupported provider fails explicitly and never falls back to a native architecture variant.

`ReferenceValue` preserves the original NumPy preprocessing values while differentiating a
mathematically equivalent Torch expression. It is only for differentiable geometry reconstruction;
official model layers and forward values remain unchanged. Topology remains the official discrete
topology, so derivatives are piecewise on a fixed neighbor list; global cutoff smoothness is not
silently changed. Providers must verify original input/feature/prediction parity and first/second
derivatives separately.

## Provider boundaries and references

All six have passed original-checkpoint/reference/ten-real-structure fine-tuning and self-contained
reload: MACE743, CGCNN744, MEGNet745, ALIGNN753, NequIP758 and Equiformer759. The original
NequIP calculator itself shows float32 force roundoff across CPU threads;758 uses one thread and
has exactly zero feature/energy/force differences, with unchanged strict tolerances. Equiformer
uses a separate environment with original PyG2.0.4 for the original OCP imports. Earlier failed
runs remain recorded rather than relabelled as passed. `implementation: legacy` explicitly
selects old variants; official never falls back to them.

## Configuration and cache

`backbone: {name: alignn}` uses the published profile registered in `profiles.py`. Each profile
declares source, exact relative files and SHA256. The default cache is repository `models/official`
for an editable checkout, otherwise `~/.cache/universal_gnn/official`; `UGNN_MODEL_CACHE` overrides
it. Model construction never downloads inside training jobs. Explicit `checkpoint` accepts the
provider's original format; CGCNN also needs its matching `atom_init`. Backend packages/pinned
vendor source must be installed separately as recorded in docs/agents/env.md.

The official object is loaded strictly, including its original head and buffers, before extracting
features at the head boundary. New task heads use random initialization. Full fine-tuning is the
default; model widths/layers/cutoff are determined by the original artifact and cannot be overridden
with old variant knobs. Conditioning is only an output adapter. Missing irreps are handled by the
existing task readouts rather than changing the original trunk.

An UGNN checkpoint embeds official source-artifact bytes, per-file checksums and implementation
signatures in `official_backbone` version1. Reload needs the compatible official Python packages,
but does not need the old external weight paths/cache. The separately saved state_dict is the
fine-tuned model plus the new heads; the embedded artifact reconstructs the original architecture.

- MACE: original model object and AtomicData, concatenated product-block node features.
- CGCNN: original `cgcnn.model`, element table, neighbor rules and GaussianDistance values; features
  after the final original convolution. Its upstream repository has no pip install metadata.
- MEGNet: the authors' MatGL1.0.0 implementation, original three-file pretrained serialization and
  target normalizer. Final node and broadcast global features are concatenated at the output only.
- ALIGNN: original pure-Torch ALIGNN2 model/config and graph/line-graph builders, final node features.
- NequIP: original eager `.nequip.zip` package and species/neighbor transforms, features before the
  original `per_atom_energy_readout`; the package carries its own source snapshot.
- Equiformer: original V1 OC20 `GraphAttentionTransformerOC20`, source commit64cb7866..., original
  OCPb5a197f input conversion and graph routines, and published IS2RE best checkpoint. Its final
  features are scalars and its upstream symmetry is SO(3); reflection equivariance is not claimed.
  V2 checkpoints are not interchangeable with this provider and its rotation detach is not patched.

For V1, original OCP radius_graph_pbc executes only its discrete topology selection under no_grad,
then the original model's supported precomputed-topology path computes distances/vectors from the
unchanged live pos/cell tensors. This avoids OCP arange accepting strain-dependent cell-repeat
bounds. No upstream code, neighbor rule, distance expression or model layer is replaced; both
native parity and coordinate/strain/mixed derivatives must pass separately.

`reference.py` exercises independent upstream entry points: MACE/NequIP calculators, MatGL
predict_structure, ALIGNN Graph, CGCNN CIFData/collate_pool and the standalone original Equiformer
constructor/forward. CGCNN adapts only CIFData's file-reading call to supply the exact in-memory
real Pymatgen structures, avoiding CIF rounding; the original preprocessing and model code execute
unchanged. Reference results and ten-real-structure fine-tuning are separate acceptance checks.

Feature extraction stops at the original readout boundary where no upstream feature output exists.
MACE instead uses its original node_feats output with force/virial/stress derivatives disabled;
old force heads cannot consume and free the graph needed by new readouts. A scalar-only final representation uses the existing
geometry-weighted vector readout for generation; the backbone is not widened to add missing irreps.
Original source/version signatures are recorded inside the embedded artifact and checked on reload.
Pinned code can be obtained with `scripts/fetch_official_sources.py`; it bundles only unmodified
upstream packages/licenses with per-file hashes, never weights/logs or symlinks.

NequIP0.14 returns a ModuleDict from its original package loader; the adapter selects the sole
original model, or requires an explicit model_key for an ambiguous package. No model is rebuilt.
Its geometry now starts from the same official from_ase protocol as the reference calculator.
The MatGL loader's model-version warning remains visible; the tested MatGL1.0.0 MEGNet source is
byte-identical to v1.1.3, and actual original-API prediction/feature and strict-state checks passed.

## Tested environments

On Guqq2, universal-official supports MACE/CGCNN/MEGNet/ALIGNN; universal uses NequIP0.14/e3nn0.5.8
to load the package's original0.15 source snapshot; universal-equiformer isolates PyG2.0.4 while
reusing the original Torch2.7/e3nn0.4.4/scatter/cluster/sparse binaries read-only. See
[environment records](../../../../docs/agents/env.md) for exact paths. These are selected published
formats/versions, not a promise that arbitrary third-party checkpoints are interchangeable.

## Prediction component capability metadata

Provider changes for prediction v1 add only basis/transformation/derivative metadata and declared
unused original head prefixes; original graph preprocessing and model layers remain intact.
All six registered published profiles now declare verified positions/strain/mixed feature derivatives.
CGCNN and Equiformer new forcefields require explicit optimization.backbone_eval=true while
training backbone parameters: original BN/stochastic behavior remains fixed with gradients enabled.
Frozen backbones already stay eval. Equiformer guarantees SO3. Exact checkpoints, real-data evidence,
finite-difference convergence and release checks are in
[forcefield validation](../../../../docs/agents/forcefield-backbones.md); arbitrary other artifacts
still need their own capability validation.
Original registered task heads may remain in the backbone state but do not contribute to the
new prediction path; component audits list known prefixes and capacity upper bounds, not an exact
measurement of effective task parameters. Dependencies/reference checks remain unchanged.
