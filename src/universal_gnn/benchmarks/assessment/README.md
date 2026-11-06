# Saved tensor assessment

This module rescores saved graph-level regression outputs. It does not import a
model or change training, checkpoints, predictions or tensor symmetries.
`GroupedRegressionMetrics(shape)` accepts one tensor per update, with explicit
Cartesian/component layout. Outputs include overall and zero/nonzero-target
MAE/RMSE, structure Frobenius errors and per-component errors in C order.

A zero target has all observed finite components exactly zero. A tiny nonzero
component remains nonzero; no threshold is fitted. Nonfinite/null target elements
are masked, and wholly masked structures belong to neither group. Missing groups
have null metrics, and unobserved components have null component errors. Zero
targets remain in absolute errors; only relative Frobenius error excludes them.

`groups` partitions whole tensors by their observed target norm. Separately,
`component_label_groups` partitions individual observed components by whether
their label is exactly zero, reporting element counts and absolute/component
errors. These groups expose zero off-diagonal labels even when every dielectric
tensor has a nonzero norm. Neither grouping constrains or projects predictions.

`evaluate_tensor_groups(training_report, output, shape=(3, 3))` reads a completed
validation-best held-out report and its saved predictions. It verifies the entire
source SHA and ordered IDs, split SHA, all test IDs exactly once, the explicitly
declared shape, raw target equality at the recorded float32/float64 dtype, and
agreement with the original overall metric populations/errors. Currently it
supports explicit `key`/`unit` bindings without transformations and one graph-level
tensor per structure; it refuses unsupported bindings instead of reinterpreting
their labels. Whole-source verification is streamed; only test labels/IDs are held.

Run numerical/data work through Slurm:

```bash
python -S scripts/evaluate_tensor_groups.py --report runs/CASE/report.json \
  --shape 3 3 --output runs/CASE-tensor-groups
```

The CLI requires a Slurm allocation. `scripts/evaluate_tensor_groups.slurm` uses
`UGNN_TENSOR_REPORT` and `UGNN_TENSOR_OUTPUT`, with an optional immutable
`UGNN_SOURCE_SNAPSHOT`. Output is a new directory containing `groups.jsonl` (ID
and assigned group) and `report.json` (metrics, source/prediction/report SHA and
execution provenance). Existing outputs are never overwritten. Invalid or
incomplete data cannot publish a passed report. Failed partial files are retained.

This is an independent assessment of saved predictions, not new inference or
training. Reprocessing a diagnostic subset does not make it a full-data training
result. See the [experiment plan](../../../../docs/plan/arxiv_v1_experiments.md).


Executed full-data evidence: source `c2155e2` preserves all eight numerical/input
sources byte-for-byte from the original1003 control. Slurm1863/1865 and their
recorders1864/1866 all completed0:0 for all eight accepted dielectric models:
499 test structures each,3992 records total,2611 zero and1880 nonzero target
components per model. A separate stdlib process independently checked raw
source/dtype/ordered IDs and every numerical/component/group result at1e-12
without importing UGNN metrics or a model. All original overall metrics and
predictions remain unchanged; this supplement adds no training or inference.
See the [full execution record](../../../../docs/plan/arxiv_v1_experiments.md).
