# Official pretrained backbones

CGCNN and ALIGNN offer an explicit `backbone.input_profile: molecular_radius`,
with `input_cutoff: 6.0` by default. Original learned modules and source artifacts
remain, while the input uses nonperiodic all-neighbor topology. Omitting it
retains original periodic preprocessing. See the
[molecular input/checkpoint contract](molecular/README.md); CPU/CUDA and full-data
acceptance are separate from the original periodic checkpoint checks below.

## Backbone initialization

The `backbone.initialization: pretrained|scratch` implementation separates
body initialization from `prediction.head_mode`. Default `pretrained` keeps the
existing strict original-weight load. CGCNN/ALIGNN `scratch` builds the same
upstream class/configuration and checks every state key/shape against the source
blueprint, without copying any learned parameters or BatchNorm statistics. It
does not recursively reset an already trained module. Published source artifacts,
element descriptors and geometry settings remain the architecture blueprint.

MACE uses the original ScaleShiftMACE constructor with neutral energy offsets/scales.
NequIP uses the original FullNequIPGNNModel builder, the author's pinned blueprint,
and the exact angular-order layout extracted from the original package. Both require
neighbor normalization fitted on the complete declared training partition using the
original graph builder; see [preparation](../../engine/initialization/README.md).
No learned source parameters or fitted source normalization are copied into scratch.
Legacy CGCNN BatchNorm counters are canonicalized by the original strict loader in
an isolated copy, leaving the fresh instance untouched. MACE's six newly registered
nonempty-contraction flags are structural boolean constants absent from the old
artifact; only known false flags with matching original weights are migrated for
layout comparison. Unknown entries, empty/changed paths and wrong shapes still fail.
NequIP's required official global setup runs inside RNG/default-dtype isolation.

**Constructor acceptance:** Slurm910 passed CGCNN/ALIGNN constructor/RNG/BN/reload checks
and17 compatibility regressions;911 passed five original graph/calibration/fresh tests each
for MACE and NequIP, with no skips. All four models also completed both initialization
modes on the frozen64/16/16 band-gap pilot, including real GPU gradients and reload.
See [evidence and limits](../../../../docs/agents/arxiv-pilots.md).
Other tasks, full-data graph coverage and derivative behavior require their own acceptance;
these results do not certify all144 formal runs. No legacy fallback is used.

Scratch requires `prediction.head_mode: reset` for prediction tasks. Reusing an
original native head contradicts the policy; loading backbone warm-start weights
also rejects a scratch target. Readout-only transfer is a separate initialization
choice and must not be reported as a wholly fresh run. Full checkpoint continuation
requires the same backbone initialization; omitted old official settings mean
`pretrained`. A checkpoint cannot label an actually scratch body as pretrained.
Load reports distinguish zero original-state coverage from strict pretrained load.

This module is the default route for the six canonical model names. Providers are not declared
verified until published-checkpoint and ten-real-structure Slurm evidence has been recorded.

With the default input profile, providers load the original architecture and all its parameters
and buffers, and call the original forward. No normalization, element encoding, interaction block,
cutoff envelope or graph rule is replaced. The optional molecular profile above explicitly changes
input topology and masks padding while preserving learned modules. Node features are exposed before native pooling/readout. Optional conditioning
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
In reset mode, original registered task heads may remain in the backbone state but do not contribute to the
new prediction path; component audits list known prefixes and capacity upper bounds, not an exact
measurement of effective task parameters. Dependencies/reference checks remain unchanged.

## Original task heads

`native_heads.py` provides verified original-head contracts for the registered
artifact hashes: ALIGNN/CGCNN band gap, MEGNet formation energy per atom,
MACE/NequIP total energy potentials, and Equiformer OC20 IS2RE relaxed energy.
Unknown artifacts require an explicit provider contract; output shape alone
does not identify a task. CGCNN and OCP target normalization is restored once;
MatGL inverse_transform and original potential scale/reference layers execute
inside the original model. Native component views never reparent or duplicate
the original modules. See [head selection](../../../../docs/native_heads.md).

NequIP retains its official neighbor transform, cutoff, mapper and learned model.
Its adapter zeros `edge_cell_shift` only along nonperiodic lattice directions:
the installed matscipy backend was observed returning spurious image shifts for
unwrapped molecules with an identity placeholder cell, changing edge vectors by
up to 2 angstrom. Periodic components and the fully periodic input path remain
unchanged. This is an input correctness fix; the failed scan and actual backend
diagnosis are preserved. Neighbor statistics bind the adapter source fingerprint,
so statistics/checkpoints tied to an older adapter require their pinned source
or freshly verified statistics, rather than silently relabeling provenance.

NequIP's three eager geometric embedding classes also keep `_output_dtype` as a
plain Python attribute. The adapter synchronizes it with actual parameter dtype
after `to`/`float`/`double`; otherwise float64 live inference and checkpoint
reload fail in the original MLP despite converted weights. This adds no layer,
parameter or normalization. Float32 operation remains unchanged; independent
finite differences retain their original precision policy and tolerances.
