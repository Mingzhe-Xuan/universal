# Capacity probe planning

`schedule_settings(probe, batch_size)` validates index sets and returns the actual warmup,
measurement and worst-case batch counts. `iter_probe_batches` yields batches in that order.
Both are pure Python and import no model or numerical libraries.

After warmup, every declared worst structure is tested in its own homogeneous batch filled
to the candidate size. This includes batch one and short generation sampling checks. Remaining
measurements cycle ordinary probe indices. Actual measurements are the greater of the requested
count and the number of worst cases; neither worst cases nor denoising steps are dropped.
Memory peaks must be reset before this entire measured sequence, not after a worst batch.

For example, seven worst cases with one warmup batch and five requested measurements require
one warmup plus seven measured batches, for any candidate size. A hundred requested measurements
with three worst cases still use a hundred measured batches, three of them dedicated to worst cases.

This scheduler covers the caller's declared set. It does not itself prove that a full training-set
graph scan selected every relevant extreme. The original-model graph scanner and real GPU training
or sampling acceptance remain separate requirements. Current worker integration awaits numerical
acceptance in the restored provider environments.
