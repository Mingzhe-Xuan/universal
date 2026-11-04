# Experiment resource preflight

[Published-ID audits](audits/README.md) compare frozen data with published
pretraining rosters without running a model or changing any split. They preserve
unknown label/geometry overlap rather than inferring no leakage from absent IDs.

Saved predictions have a separate [tensor assessment module](assessment/README.md).
It independently verifies original labels, frozen test IDs and overall metrics,
then adds zero/nonzero target groups and component errors without modifying the
training or resource-preflight paths.

`resolution.py` accepts only actual worker-derived generation priors and original
scratch neighbor statistics. It preserves every explicit setting and verifies
fresh zero source-weight coverage, source/graph identity, precision and training
counts before writing a resolved config. Invalid metadata stops the attempt and
does not trigger OOM halving. Training, generation and capacity share the same
native calibration routine; numerical integration acceptance is still required.

Run inside a Slurm GPU allocation, using the same environment and configuration as
the intended training run:

```bash
python -m universal_gnn.benchmarks.preflight configs/experiment.json \
  --probe data/experiment/train-probe.json --output runs/preflight/experiment
```

The probe is JSON, for example:

```json
{
  "indices": [0, 2, 7],
  "worst_indices": [7],
  "warmup_batches": 2,
  "measure_batches": 100,
  "coverage": {"verified_full_training_scan": false}
}
```

Indices refer to the selected, bound **training** dataset. Construct the probe from
a full training-set graph-size scan: include largest atom/edge/triplet cases and
ordinary structures; retain scan counts, source fingerprints and IDs in `coverage`.
The controller does not certify caller-supplied coverage. An unchecked small probe
passing is not sufficient to launch a full experiment. The worker uses
[the probe scheduler](probes/README.md) to test each declared worst case separately in a full
homogeneous batch after warmup, before ordinary measurements. If there are more worst cases
than requested measurements, the actual count grows to include every case. No training samples
may be dropped. Pure scheduling checks do not establish actual GPU coverage; numerical acceptance
in the restored provider environment remains required.

Each attempt creates a new Python process and reconstructs the configured model
from its original initialization. The worker performs forward, loss, backward and
Adam step, including force/response derivative paths. Preflight weights and optimizer
updates are discarded. Only a typed CUDA OOM with the dedicated worker result/exit
code halves batch size (`32,16,8,...,1`, or `5,2,1`). Host RAM kills, timeouts,
incompatible CUDA extensions, invalid labels and numerical errors stop the check.
At batch 1, CUDA OOM fails the check. The controller never changes graph, precision,
trainable components, dataset or device. `max_atoms` must be unset for this check.

Output must be a fresh empty directory. `report.json` and each attempt directory
retain configs, stage, error, stdout/stderr and metrics. A successful check writes
`config.resolved.json` with the tested batch; formal training must use it and start
again from its specified initialization. Compare pretrained and scratch separately,
then recheck both at their common smaller batch. No gradient accumulation is implied.

Generation needs a separate `--phase sample` check with the full intended `task.sampling`
settings. Sampling batch can differ from training; the requested sample count and
number of denoising steps must not be reduced. The current worker supports configured
initialization, not resuming a partially trained optimizer; precheck resumed training
requires a dedicated continuation probe before changing any checkpoint settings.

Peak CUDA memory and measured throughput cover the supplied probe after warmup.
Capacity alone does not establish scientific accuracy, held-out evaluation, full-data
coverage or checkpoint compatibility. See [the experiment plan](../../../docs/plan/arxiv_v1_experiments.md).

For the original-pretrained versus whole-backbone-scratch comparison, use
[paired capacity](pairing/README.md). It checks both modes independently, then checks both again
at their common smaller batch. If another OOM lowers this common size, both are rechecked again.
Only the final shared size is exported; the original full-matrix definitions remain unchanged.
This orchestration retains the supplied-probe scope above and launches no formal training.

Full-data generation has a public [pair preparation entry](generation/README.md): separate training/sampling capacity, complete train-only prior and original graphs. Formal1000-sample quality remains a separate run.
