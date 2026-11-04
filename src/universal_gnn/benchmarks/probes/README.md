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

## Full graph scan still to implement

`selection.select_probe(rows, records, binding)` verifies all source-ordered training identities and
retains bounded extreme and deterministic ordinary candidates. Counts must include atoms, native
edges, native triplets, auxiliary edges and maximum degree. Native edge semantics distinguish
directed edges from CGCNN's padded slots. Ordinary examples exclude selected extremes when the
dataset contains enough records. The reducer alone keeps `verified_full_training_scan: false`.

`native_scan.py` is still planned for Slurm-only construction with the original providers.
It is not implemented yet. Receipts must bind the complete source-ordered train
partition, input precision, native artifacts, actual graph implementations and active cutoffs.

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
