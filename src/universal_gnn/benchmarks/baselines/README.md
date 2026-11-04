# Frozen-split baselines

`evaluate_scalar_mean(config, output)` fits one mean using only the complete train
partition and scores every validation/test record in the label's original unit.
The input is a full supervised UGNN config with `structures: all`, no atom crop,
an explicit train manifest and a raw scalar label binding containing `key`/`unit`.
It constructs no graph and imports no numerical/model package.

Both passes verify source bytes, count and every ordered ID against the frozen
manifest; the manifest's canonical SHA is also required. Labels must be finite
scalars (singleton lists are accepted). Predictions stream to JSONL; outputs
include train count/mean, separate validation/test MAE/RMSE and source/config
fingerprints. Existing output directories are refused. Changed input or incomplete
execution cannot publish a completed report. The manifest's ID list stays in
memory; geometry and predictions are processed one record at a time.

Run `scripts/evaluate_scalar_baseline.py --config CONFIG --output NEW_DIRECTORY`
inside Slurm, or submit `scripts/evaluate_scalar_baseline.slurm` with
`UGNN_BASELINE_CONFIG` and optionally `UGNN_BASELINE_OUTPUT`. The baseline has no
training seed or backbone dependency and is shared when source, split, label and
unit agree. It does not count as one of the formal neural training runs.
