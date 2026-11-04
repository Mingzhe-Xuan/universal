# Full matching-task native baselines

`native_baseline_config(matrix, provider)` derives an evaluation configuration
from the full frozen primary matrix. CGCNN/ALIGNN retain their original bandgap
heads; MACE/NequIP retain original total-energy heads and derived forces. Every
parameter is frozen and no optimizer, target shift, scale fit, threshold tuning or
checkpoint selection runs. The actual native pooling and normalization stay in
the original model. These are supplementary zero-shot evaluations, outside144
formal reset-head/scratch trainings.

From a clean fixed checkout with existing data/models/runs:

```bash
UGNN_PYTHON=/home/xmz/.venvs/universal-mace/bin/python \
UGNN_MATRIX=runs/arxiv-v1/definition-947/matrix.json \
UGNN_MATRIX_SHA256=b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651 \
UGNN_PROVIDER=mace \
UGNN_OUTPUT=runs/arxiv-v1/new-native-mace \
sbatch scripts/evaluate_native_baseline.slurm
```

Use `universal-official` for CGCNN/ALIGNN, `universal` for NequIP.
The full7580 JARVIS bandgap or164 MLearn test structures use the main frozen
source/split, all structures, float32 and the declared task batch. CPU calculations
run only through Slurm. The main GPU training queue and all training cases remain
unchanged. Output must be new; create `runs` before submission for Slurm logs.

`report.json` stores the parent case/config, complete counts, execution and package
versions, original API parity, hashes of all persistent model state before/after,
ordered test-ID coverage, prediction-file SHA, physical-unit metrics and CPU cost.
`test/predictions.jsonl` retains every test prediction/label. The score helper's
aggregation scales are fixed1 and fit no labels; they do not change predictions.
Force paths retain autograd even though all parameter gradients are disabled.

These heads have different original target/reference conventions. In particular,
unshifted absolute energies may use different energy zeros; no heldout calibration
is performed. Known material-ID exposure for ALIGNN still applies; other exact
intersections remain unknown. Report these as native transfer baselines rather
than leak-free or matched-functional model rankings. Native forward parity is
tested separately from downstream accuracy. No DFT calculations are required.
