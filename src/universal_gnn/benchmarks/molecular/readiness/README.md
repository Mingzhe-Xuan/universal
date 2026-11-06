# Joint molecular preparation evidence

This module joins the existing complete CUDA graph/capacity/physics evidence
with the separately executed, complete900-frame original-network CPU comparison.
It reads metadata and files without importing a numerical framework, constructing
a model, training, submitting jobs, or changing existing preparation requests.
Run the checker through CPU Slurm in the registered provider environment.

Inputs are the selected closed molecular definition, a CUDA capacity directory,
its retained successful parent terminal, a parity directory, and that comparison's
retained successful parent terminal. Request bytes, receipts, report hashes,
source checkouts, versions, source/split/audit, all100000 graph rows,900 training
rows, original paired capacity trials, full homogeneous100 plus mixed100 batches,
per-mode original force/stress/geometry checks and all900 parity rows must match.
CPU graph evidence cannot substitute for CUDA capacity. Only the original typed
CUDA OOM chain can reduce the common batch. Both initialization modes are
required for an official provider; the plugin has its single scratch mode.

```bash
PYTHONPATH=src python scripts/check_molecular_readiness.py \
  --model cgcnn --capacity runs/CAPACITY \
  --capacity-terminal runs/CAPACITY/terminal-parent.json \
  --parity runs/PARITY/parity \
  --parity-terminal runs/PARITY/terminal-parent.json \
  --output runs/NEW-JOINT-CHECK
```

Output is a new report and the checked resolved configuration for each mode,
with an input hash map. A passed report says `preparation_gate_passed=true`,
`formal_training_ready=false`, and `formal_training_runs=0`. Formal runtime
budgeting, managed launch, full900-frame fitting and99000-frame/author-cohort
quality acceptance remain separate work. Missing evidence fails; a negative
check or a synthetic unit-test fixture is never numerical acceptance evidence.


CPU control acceptance: source `fc7cf0c`, Slurm1817/1818 both completed0:0;
73 pure tests passed without skips. All five original pending CUDA groups were
correctly refused for their missing capacity reports. Six executed source hashes
and70 control artifacts were verified. The previous1815 fixture failure remains
archived; only the tests' temporary working-directory setup changed. This is
negative-evidence validation, not positive CUDA/preparation/formal readiness.
See the [execution record](../../../../../docs/plan/arxiv_v1_experiments.md).
