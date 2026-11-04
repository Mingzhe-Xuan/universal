# Capacity probe planning

`schedule_settings(probe, batch_size)` validates index sets and returns the actual warmup,
measurement and worst-case batch counts. `iter_probe_batches` yields batches in that order.
Both are pure Python and import no model or numerical libraries.

After warmup, every declared worst structure is tested in its own homogeneous batch filled
to the candidate size. This includes batch one and short generation sampling checks. Remaining
measurements cycle non-worst probe indices when available. If the caller supplied only worst
indices, the ordinary phase uses that available set rather than inventing other records.
Actual measurements are the greater of the requested
count and the number of worst cases plus one ordinary batch; neither worst cases nor denoising steps are dropped.
Memory peaks must be reset before this entire measured sequence, not after a worst batch.

For example, seven worst cases with one warmup batch and five requested measurements require
one warmup plus eight measured batches, for any candidate size. A hundred requested measurements
with three worst cases still use a hundred measured batches, three of them dedicated to worst cases.

This scheduler covers the caller's declared set. It does not itself prove that a full training-set
graph scan selected every relevant extreme. The original-model graph scanner and real GPU training
or sampling acceptance remain separate requirements. Current worker integration awaits numerical
acceptance in the restored provider environments.

## Complete original graph scanner

`selection.select_probe(rows, records, binding)` verifies all source-ordered training identities and
retains bounded extreme and deterministic ordinary candidates. Counts must include atoms, native
edges, native triplets, auxiliary edges and maximum degree. Native edge semantics distinguish
directed edges from CGCNN's padded slots. Ordinary examples exclude selected extremes when the
dataset contains enough records. The reducer alone keeps `verified_full_training_scan: false`.

`native_scan.scan_training_graphs(config, output)` constructs every source-ordered training
graph through the four original providers' `native_input`. It requires Slurm, the configured
CUDA device, `structures: all`, an explicit train manifest and the reset-head experiment path.
It rejects custom graphs and atom-count cropping. To inspect topology independently of scratch
normalization, it loads the original pretrained constructor, removing initialization/calibration
options only from a copy. This does not validate the scratch constructor or its weights.

The scanner writes `graph-sizes.jsonl`, a status `report.json`, then `probe.json` only on success.
Failed prefixes remain for diagnosis. Existing output directories cannot be reused. It binds raw
source SHA, canonical manifest SHA, precision/device, original artifacts, provider settings,
loaded Python source hashes and dependency versions. It rechecks source/split and checkout
identity before publication. Model module forwards are forbidden during graph construction.
The current seven stdlib controls cover policy, complete-stream identity and count arithmetic;
the five numerical checks in `scripts/validate_graph_scan.py` and actual four-provider full scans
remain pending restored Torch/provider environments. No real graph-scan receipt exists yet.

Run `scripts/scan_training_graphs.py --config CONFIG --output NEW_DIRECTORY` inside a GPU Slurm
allocation in the model's isolated environment. See the [script instructions](../../../../scripts/README.md)
for commands. Use the emitted probe for the paired capacity runner only after separately
verifying the original initialization and derivative checks. The scan itself does not run
training, adapt batch size or prove that selected batches fit memory.

The scan must count auxiliary readout graphs too. The existing
[equivariant adapter](../../adapters/features.py) adds a radius graph for geometric response;
generation's [DirectionReadout](../../tasks/generation.py) builds another graph only when native
polar features are unavailable. The scan must identify the branch actually used. Original backbone edge
counts alone therefore do not describe all allocated graph work. CGCNN's dense padded neighbor
slots must be identified as allocated slots, rather than mislabeled as physical bonds; ALIGNN
requires its line-graph counts as well. Preserve separate counts for these different allocations.

For generation, a complete scan of clean training graphs still does not cover every perturbed
training state or sampling trajectory. Validate the actual corruption/sampling path separately
and state which input states were measured. No finite capacity probe guarantees every possible
stochastic trajectory.
