# Explicit molecular inputs for original CGCNN and ALIGNN

This module changes the input graph while keeping original learned modules,
parameter/buffer names, element descriptors and feature widths. Select it explicitly:

```yaml
backbone:
  name: cgcnn  # or alignn
  implementation: official
  initialization: pretrained  # or scratch
  input_profile: molecular_radius
  input_cutoff: 6.0
task: {kind: forcefield, supervised_outputs: [total_energy, forces]}
prediction:
  version: 1
  head_mode: reset
  readout: {name: node_mlp, pooling: sum, hidden_features: [64], activation: silu}
optimization: {train_backbone: true, train_readout: true, backbone_eval: true}
```

CGCNN forcefields require `backbone_eval` because original node BatchNorm couples
structures in train mode. ALIGNN can retain its ordinary mode. Parameter training
and mode remain separate. Use the registered profile instead of a top-level
`graph` for these providers. Omitting the profile, or using `official`, retains
original periodic graphs and old artifact fields. Gaussian bases and original
model configuration are not changed to accommodate the new topology.

`profiles.py` validates the optional profile and positive finite molecular cutoff,
default6 angstroms. Checkpoints embed its version and five adapter source hashes,
normalized to LF for cross-platform reconstruction. Changed/partial profile or
implementation metadata fails explicitly. Graph provenance includes that identity;
the original source-artifact checks remain active.

`geometry.py` selects every directed nonperiodic radius neighbor, without images,
top-k or12-neighbor cap. The placeholder cell is never used for topology or
geometry. Coincident/nonfinite positions fail. Live geometry retains coordinate
and mixed parameter gradients, locally on a fixed neighbor list. Autograd does
not supply global continuity across hard neighbor switches; original network
envelopes are not silently replaced.

`cgcnn.py` exposes four original dense inputs as a tuple with `valid_mask`.
Padding cannot be treated as a zero-feature edge: the source convolution has
nonzero gates and edge BatchNorm. A scoped context runs original edge BN only
on valid rows and masks invalid gates before aggregation. Original learned
modules and state paths stay intact. Empty edge batches preserve edge BN
statistics/counters, and modes/hooks are restored on success or exceptions.
Original node BN and its small-train-batch restriction remain; isolated-atom
inference uses eval mode as required by CGCNN forcefields. Call the provider's
`encode`/`native_forward`; direct original `model(*inputs)` needs the scoped
`valid_neighbor_messages` context for padded molecular inputs.

`alignn.py` builds original `TorchGraph` and line-graph containers with original
triplet and cosine functions and the original three-body threshold. It supplies
no invented fractional coordinates, bulk volumes or lattice descriptors.
Artifacts requiring lattice-property input, or native stress heads requiring
a bulk volume, fail explicitly for this profile.

UGNN's common forcefield still derives force/strain outputs from scalar energy.
A strain derivative divided by a nonperiodic placeholder volume is not physical
bulk stress: supervise/report molecular E/F only and do not claim stress accuracy.
Crystal weights transferred to molecular inputs are not an original crystal
zero-shot benchmark. Reset heads are normally appropriate for molecular E/F.

Pure metadata tests need no numerical packages. The original-model tests in
`tests/test_official_molecular.py` require Slurm: original constructors/RNG/state,
float32/64, independent ASE/original-module references, ragged/empty/dense graphs,
mask/BN behavior, geometry/FD/mixed gradients, checkpoint reconstruction and
periodic parity. CPU, CUDA and full-data evidence remain separate gates.

Dense CGCNN batches still allocate slots up to their largest degree. A full-data
capacity gate must cover mixed extreme atom-count/degree batches, not only
homogeneous repeats. Existing graph-scan `padded_neighbor_slots` are computational
slots rather than valid messages; the molecular workflow must bind the explicit
profile and preserve that distinction when certifying graph/capacity coverage.
