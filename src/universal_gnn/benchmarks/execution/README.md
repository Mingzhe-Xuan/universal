# Formal predictive execution

This public entry covers classification, bandgap, dielectric,200-channel spectrum
and forcefield cases of the unchanged144-case matrix. Generation retains its
separate full training/quality protocol and is rejected here. This boundary does
not remove generation or supplementary experiments from the paper requirements.

`case_spec(matrix, id)` checks the complete corrected144-case definition and the
selected original frozen recipe. `check_preparation(..., budget_seconds=...)`
runs through Slurm without a neural import: it verifies full source bytes and
canonical split, all original/auxiliary graph-size rows and extrema, both capacity
initializations and their full attempt/SHA chains, common batch/resolved configs,
full scratch calibration, original parameter coverage, dependency versions,
unchanged model/training/graph Python source and required CUDA derivative checks.
No caller-supplied readiness boolean or diagnostic subset replaces these gates.
NequIP scratch adds exactly its registered author-constructor blueprint to the
same public package used by the clean pretrained topology reference. Both hashes
must match the frozen registry; arbitrary extra artifacts remain invalid.

Example read-only check from a clean fixed checkout with data/models/runs links:

```bash
PYTHONPATH=src /home/xmz/.venvs/universal-mace/bin/python scripts/run_formal_case.py \
  runs/arxiv-v1/definition-947/matrix.json \
  --matrix-sha256 b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651 \
  --case seed-123--forcefield--mace--pretrained \
  --preparation runs/arxiv-v1/full-ff-preparation-962-mace \
  --budget-seconds 86400 --check-only --gate-output runs/new-gate.json
```

Run that command inside a CPU Slurm allocation; it deliberately refuses login-node
execution. The output must be new. Use the provider's environment: MACE uses
`universal-mace`, NequIP `universal`, CGCNN/ALIGNN `universal-official`.
Version checks apply to the actual provider environment. A completed existing case
may be checked without retraining, but cannot be executed again by this entry.

For a new case whose complete pair preparation has passed, set `UGNN_PYTHON`,
`UGNN_MATRIX`, `UGNN_MATRIX_SHA256`, `UGNN_CASE`, `UGNN_PREPARATION` and
`UGNN_BUDGET_SECONDS`, then `sbatch scripts/run_formal_case.slurm`. Override Slurm
memory/time from measured preparation costs as needed; scheduling changes do not
alter the frozen model/data/optimization recipe. Keep budgets consistent with the
allocation. The gate requires a probe-based train-time estimate plus50% reserve;
this is a declared estimate, not a guarantee of full-run time. If insufficient,
request more wall time rather than reducing epochs/data or silently resuming.

The runner verifies a real GPU allocation and remaining wall budget, requires
20GiB disk reserve, creates the matrix case directory atomically, and calls the
unchanged training engine. Preflight-updated model weights are discarded. Each
complete epoch must cover every training structure/minibatch and validation role.
The original300-epoch cap and validation-best/patience30 protocol stay intact.
Every initialization starts fresh as declared; no resume or warm-start is implied.

`execution-gate.json`, requested/resolved configs, all events, best/last checkpoints,
test predictions and `formal-status.json` remain under the case directory. The
runner checks actual backbone gradients/initialization, exact state/deterministic
reload, true validation minimum, complete ordered test predictions and shapes,
and records GPU/RSS/disk/wall costs. No runtime CUDA OOM retry changes a formal
configuration: only the preparation controller performs typed-OOM batch selection.
Failed formal attempts retain evidence and require an explicit recovery plan.

A passed formal training report still needs independent raw-source re-score,
trained-model physics where applicable, and full inference/cost assessment before
the paper's independent acceptance count is updated. The entry records
`independent_postevaluation_verified:false` explicitly. Existing running requests
and immutable source caches are unaffected by adding this orchestration.

`slurm.py` handles modern `AllocTRES`, older allocated `TRES` GPU entries and
the cluster's legacy `TresPerNode=gres:gpu:1` representation. It first requires
the current job ID, owner, RUNNING state and allocated nodes. Explicit allocated
CPU/zero-GPU records cannot fall back to request fields. The legacy fallback
also requires a positive allocated node count and positive per-node GPU count;
a pending GPU request never qualifies. Both predictive and generation execution
use this check. Actual CUDA visibility is checked separately by the runtime.
See [Slurm states](https://slurm.schedmd.com/job_state_codes.html) and
[GPU resources](https://slurm.schedmd.com/gres.html). Resource-field compatibility
does not alter model/data/precision, derivatives or the measured finite budget.

Source17be214 passed CPU1076:37 main tests/350 JUnit records without failures,
errors or skips, exact historical991 legacy-record rejection reproduced in the
old guard and corrected in the new guard, own actual CPU allocation rejected,
and six existing full mode gates rechecked. Seven executed Git blobs match.
Real GPU visibility/tiny backward control1077 is separately queued after991;
its pending state is not GPU acceptance. Replacement CPU launch gates wait for
that control and their original full preparations to succeed. Running training
and original scientific configs remain unchanged.
