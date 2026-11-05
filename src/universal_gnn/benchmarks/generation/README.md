# Complete generation pair preparation

Input is one corrected, frozen full experiment matrix and a generation pair ID.
The public entry checks both initializations and the full Perov-5 split
11356/3787/3785. All numerical work requires a Slurm GPU allocation.

From a clean fixed source checkout with existing data/models/runs links:

```bash
UGNN_PYTHON=/home/xmz/.venvs/universal-mace/bin/python \
UGNN_MATRIX=runs/arxiv-v1/definition-947/matrix.json \
UGNN_MATRIX_SHA256=b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651 \
UGNN_PAIR=seed-123--generation--mace \
UGNN_OUTPUT=runs/arxiv-v1/new-mace-generation-preparation \
sbatch scripts/prepare_generation_pair.slurm
```

Use `universal-official` for CGCNN/ALIGNN and `universal` for NequIP.
Create `runs` before submission so Slurm can open logs. Use a new output path.
The surrounding launcher must verify original initialization, generation protocol
regressions and diagnostic acceptance before running this preparation. A preparation
pass does not launch or authorize formal training on its own.

The implementation compares original unconditioned body features and native
predictions, constructs every clean training native/auxiliary graph, and fits the
volume prior from the full actual training geometry. CGCNN's reference CIF reader
receives an unused temporary CSV scalar; scientific labels/configs are untouched.
It runs independent paired capacity checks for training (initial batch16,
2 warmup/at least100 measured batches) and sampling (initial batch4,
1 warmup/at least5 measured batches). Every declared worst case receives a full
batch; measured counts grow if necessary. Only typed CUDA OOM halves batch.
Unknown errors, numerical failures and timeouts stop the preparation.

`train-capacity/config.*.resolved.json` are the formal training candidates.
`sample-capacity/config.*.resolved.json` retain a separate sampling batch and must
never overwrite the training candidates. Both phases preserve100 noise levels
and2 inner steps, train-only prior, full partition and precision. Scratch native
neighbor statistics, where required, cover the entire training partition.
`report.json` retains both receipt chains, source-bound prior and probe timing.

Clean graph extrema cannot bound every evolving noisy graph. Actual training
probes corrupt inputs and sampling probes traverse the configured diffusion, but
they do not establish trained-model sample quality or all-run memory safety.
The separate quality evaluator currently samples singly: its formal budget remains
1000 attempted samples,5 draws per condition, seed456 from validation-best weights.
Probe throughput at a different batch is not a measured1000-sample runtime.
No DFT thermodynamic stability claim is made.

## Formal training and quality

`execution.py` consumes both complete capacity chains via the shared preparation
gate. Inputs are the frozen144-case matrix, a generation case ID, a passed full
preparation directory and a declared wall-time budget. It requires unchanged
model/engine/graph sources, matching provider versions and original artifacts.
`evidence.py` checks the complete train-only prior, sampling configuration and
separate sample capacity. These modules do not change a model or training recipe.

Check first from the clean immutable checkout in a CPU Slurm allocation, using
the provider's normal Python so installed dependency metadata remains visible:

```bash
"$UGNN_PYTHON" scripts/run_generation_case.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" \
  --case seed-123--generation--mace--pretrained --stage check \
  --preparation runs/arxiv-v1/new-mace-generation-preparation \
  --budget-seconds 86400 --gate-output runs/new-generation-gate.json
```

After that gate passes, submit training with `UGNN_CASE`, `UGNN_STAGE=train`,
`UGNN_PREPARATION` and `UGNN_BUDGET_SECONDS`, plus the same `UGNN_PYTHON`,
`UGNN_MATRIX`, `UGNN_MATRIX_SHA256` variables:

```bash
sbatch scripts/run_generation_case.slurm
```

This creates the case's new run directory and refuses to overwrite an existing
one. It verifies every complete training/validation epoch, full test denoising
predictions, validation-best selection, source/split bytes and exact reload.
Successful training sets `training_passed_quality_pending`; it is one completed
training, with generation quality and independent post-evaluation still pending.
Keep both the last checkpoint (which contains selection history) and the best
checkpoint. Do not substitute the best file as the quality command's input.

Submit a separate GPU job with the same variables and `UGNN_STAGE=quality` after
training succeeds. Its independent stage budget must cover the measured sample
preflight batch time times1000, plus50% reserve. This deliberately uses a full
probe batch as the estimate for one current single-sample attempt. It is a
conservative heuristic, not a measured trained-model runtime or a guarantee.
The gate also checks the remaining actual Slurm wall time and GPU allocation.
If the declared or remaining budget is insufficient, submit a larger allocation;
do not reduce1000 attempts,5 draws, seed456 or100x2 diffusion steps.

Each quality job writes `quality-SLURM_JOB_ID/` and appends `quality_attempts` to
`formal-status.json`. `quality-active/owner.json` prevents concurrent sampling of
the same case. An ordinary failure keeps the partial attempt, marks
`quality_failed` and releases its own claim, allowing a fresh job with the same
fixed protocol. Completed quality refuses another run. A claim left after a
hard kill requires an operator to verify that exact owning Slurm job is terminal
before recovery; a directory or observation timeout alone is never proof.

All1000 attempted rows, including explicitly invalid samples, are retained.
The integrity validator checks200 deterministic test conditions,5 distinct draws
each, their seeds and order, source-bound compositions, numeric formats,
best/prior identities and reported rates. Empty quality groups stay null; zero
valid samples still constitutes a complete execution and reports zero validity.
Unexpected exceptions or OOM fail the stage. Successful execution sets
`generation_quality_complete=true`, but leaves
`independent_postevaluation_verified=false`: independent geometry/matching and
distribution rescoring is still required before accepting the paper result.

The current code has pure metadata/protocol controls. Full generation gate and
numerical training/1000-attempt acceptance require the actual full preparations;
the existing8-attempt diagnostic reports do not satisfy this formal protocol.
