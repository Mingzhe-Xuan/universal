# Deferred formal submission

`planning.py` takes the frozen144-case matrix, a pair ID, the actual completed
full preparation and its provider Python. It checks both modes through the
existing full scientific gate before producing any submission. Complete capacity
receipts determine the training estimate; the budget is rounded up to minutes,
with50% reserve and900 seconds startup allowance, and a one-hour minimum. A finite
partition limit must cover that allocation. `UNLIMITED` partition policy still
produces a finite measured job budget. No model, graph, data, optimizer, epoch or
generation protocol is changed by this module.

Run a read-only plan in CPU Slurm:

```bash
"$UGNN_PYTHON" scripts/submit_formal_pair.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" --pair "$UGNN_PAIR" \
  --preparation "$UGNN_PREPARATION" --check-only --plan-output runs/new-pair-plan.json
```

Plans show existing case paths, but do not reserve them or submit jobs. Existing
training results do not become safe to rerun just because their evidence passes.
Use the normal provider Python, including its installed package metadata paths.
CGCNN/ALIGNN use `universal-official`, MACE `universal-mace`, NequIP `universal`.

To arm a deferred CPU gate after an existing full preparation succeeds, set
`UGNN_PYTHON`, `UGNN_MATRIX`, `UGNN_MATRIX_SHA256`, `UGNN_PAIR` and
`UGNN_PREPARATION`, then submit:

```bash
sbatch --dependency=afterok:FULL_PREPARATION_JOB scripts/submit_formal_pair.slurm
```

The deployment controller also requires source acceptance before arming gates.
The CPU gate checks source/split/artifacts, complete graphs, paired capacity,
native calibration and applicable physical evidence. Its output lives in
`runs/arxiv-v1/dispatch/PAIR/attempts/PARENT_JOB/`. It then submits two GPU training
jobs using the existing public execution entries. Resource requests are one GPU,
two CPUs and64GiB RAM, matching the public training wrappers, with the derived
finite time limit. These allocation choices are recorded separately from the
unchanged frozen scientific configs.

Generation additionally submits quality afterok each training, then the existing
independent CPU assessment afterok quality. Quality retains1000 attempts,5 draws,
seed456 and100x2 steps. Its estimate uses the full measured sampling probe batch
time per single-sample attempt, with the same reserve, as a conservative heuristic.
It is not a measured trained-model runtime. Independent assessment requests two
CPUs/8GiB/four hours; this is an explicit initial allocation, not a guarantee.
Predictive independent raw-label/physical/full-inference evaluations remain
separate required stages; successful training alone does not certify a paper case.

`dispatch.py` persists each exact Bash request, source/preparation/config hashes,
resources, unique Slurm comment token and parsable job receipt. Training claims
use `runs/arxiv-v1/launches/CASE/`; generation followups use `quality/` and
`assessment/` within that claim. Atomic case/stage creation and a pair-level active
claim prevent concurrent duplicate submission. External/older claims and existing
unmanaged results are refused. A new parent may reuse only the exact recorded
request/receipt after verifying the retained Slurm job's user, name, token and
state; it may then submit stages that have never been claimed. This is not a new
training or a claim that the old job is still running.

A timeout, nonzero RPC exit or malformed reply leaves `submission_unknown` and
the exact request/token; it never automatically repeats `sbatch`. If Slurm no
longer retains a recorded job, reconcile its actual artifacts before proceeding.
A claim left after a hard kill similarly requires authoritative owner-job checks;
age or an observation timeout alone does not permit reclaiming it. Every failed
parent attempt remains available. No existing jobs are canceled or modified.

Submitted CPU gates count as zero formal trainings. Only actual GPU training
receipts increase submitted-case counts, and independent post-evaluation is still
required to increase scientifically accepted cases. Pure mock tests exercise all
72 frozen pair identities, resource budgets, dependency chains and failure
semantics; they do not certify actual data gates or Slurm execution.
