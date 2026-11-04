# Held-out metric accumulation

`RegressionMetrics.update(prediction, target)` consumes numeric nested sequences for
**one structure** at a time. `result()` returns scalar-element MAE/RMSE, mean
per-structure Frobenius error, and relative Frobenius error over nonzero target norms.
Zero tensors remain in absolute metrics; zero-norm targets are excluded only from
relative error and counted explicitly. Nonfinite targets are masked per element;
nonfinite predictions fail. Arrays must have the same scalar-element count and
must already use the configured Cartesian/component and unit conventions.

`BinaryClassificationMetrics(path)` owns a new SQLite score spool. Call
`update(positive_probability, integer_target)` and `result()`, then `close()`, or use
a context manager. It reports accuracy, balanced accuracy, precision, recall, F1 and **exact** AUROC
with ties handled as half a correct ordering. A single-class evaluation has null
AUROC and balanced accuracy. Balanced accuracy is the mean of the two true-class
recalls; it is null when either true class is absent. Python memory is bounded;
sorting scores uses SQLite disk storage. The
default threshold is 0.5; pass `predicted_class` to preserve the model's actual
argmax/tie convention. Keep these spools with ignored experiment results, not Git.

These accumulators fit no statistics and select no checkpoints themselves.

## Manifest-based training integration

`dataset.split_manifest` and `dataset.partition: train` opt supervised/force-field
training into `heldout.py`. It uses only selected training records for label scales,
evaluates the complete validation partition every epoch, and saves the actual
minimum validation loss as `<checkpoint-stem>.best.pt`. `evaluation.patience`
(positive integer or null) and nonnegative `evaluation.min_delta` control early
stopping. `min_delta` affects patience only; every new actual minimum still saves
the best weights. Full ordinary training without a manifest keeps its existing
behavior and reports training metrics only.

The last checkpoint retains optimizer/RNG and validation selection history; the
best checkpoint contains weights/config/scales without an optimizer. A temporary
best candidate survives until the atomic last checkpoint commits its hash, so
resume can recover either side of an interrupted rename. Normal completion retains
only best and last; allow one candidate's temporary disk overhead. Full continuation
requires the same source/split hash and selection protocol, replay-valid history,
and the best artifact named by the last checkpoint. Resume into another output
directory copies that verified artifact. Keep both files together when archiving.

After training, the validation-best weights are evaluated on the test partition
once. `report.heldout` identifies the selection, complete partition counts,
train-only scales and metrics. JSONL predictions/targets and disk-backed AUROC
scores live under `evaluation/epoch-N/`; masked target elements serialize as null.
Test labels do not determine loss scales, best epoch or stopping. Both full-record
counts and explicit training-subset size remain visible. The current held-out
classification evaluator supports binary tasks; existing no-manifest multiclass
training is unchanged. Tensor errors use the supplied component order/units and
apply no symmetry projection.

Numerical integration tests cover training-only scales, true best selection,
continuation, early stopping, missing/corrupt artifacts, force mixed derivatives,
tensor response and classification. They must run through Slurm; only protocol
tests can run without numerical dependencies locally. Generation uses its separate
[held-out and quality evaluators](../generative/README.md). No full experiment is
considered ready from these unit checks alone.
