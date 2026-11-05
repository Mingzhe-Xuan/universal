# Complete generation pair preparation

## Explicit staged readiness for the single-seed campaign

`staging.py` and `scripts/run_generation_staged.py` distinguish complete training
readiness from untrained sampling readiness. `--stage check` replays the same
full source, split, original graph extrema, artifacts, provider versions,
initialization, paired100-batch CUDA training evidence and fitted training prior.
It can consume an original preparation that failed **only** at
`paired_sampling_capacity`, with byte-bound known nonfinite/image-budget failure
evidence. It leaves that original report failed and records sampling readiness
as unqualified. No sampling timing or memory qualification is invented.
The existing strict `check_preparation` and original CLI retain their requirement
for complete sampling preparation. Only the eight active seed123 cases qualify.

```bash
"$UGNN_PYTHON" scripts/run_generation_staged.py "$UGNN_MATRIX" \
  --matrix-sha256 "$UGNN_MATRIX_SHA256" \
  --case seed-123--generation--mace--pretrained --stage check \
  --preparation runs/arxiv-v1/full-generation-preparation-1022-mace \
  --budget-seconds "$UGNN_BUDGET_SECONDS" --output runs/new-staged-generation-gate.json
```

Run each stage through Slurm in a clean pinned checkout using the provider's
environment. `--stage train` uses the same preparation and declared measured
training budget, refuses any existing case output, and executes the unchanged
full training recipe. It stops at `training_passed_quality_pending`.
`--stage quality --budget-seconds SECONDS` revalidates the original evidence and
uses validation-best weights for the original1000 attempts,5 draws, RNG456,
100x2 sampling steps, current batch1. Where no qualified sampling throughput
exists, its finite allocation is explicitly declared and bounded by remaining
actual GPU Slurm wall time; it is no runtime guarantee. Timeout/unknown errors
remain failures and partial attempts remain on disk.

All eight generation cases use the same explicit policy when evaluated through
this staged quality entry. `sampling_failures.py` converts only the exact
periodic-image-budget graph guard to an invalid attempt understood by the
existing evaluator. Known nonfinite outputs already count as invalid attempts.
Unknown errors and CUDA OOM propagate. Successful sampler arguments, outputs,
steps, RNG and model state are unchanged; the model/graph/engine source is
unchanged. Policy version and source SHA are saved with status and metrics.
Every invalid attempt remains in the1000 denominator. There is no retry-until-valid.

`--stage verify --output NEW_DIRECTORY` checks the same readiness and policy,
then independently recomputes quality from all saved raw geometry on CPU, with
model loading/forward forbidden. Full quality plus independent assessment remain
mandatory for scientific completion; training readiness is not final acceptance.
Previously queued training does not need retraining. Its pending quality jobs
must be superseded with exact identity checks before scheduling this entry;
the original strict entry does not silently switch policy.

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

Source57a907b completed CPU Slurm acceptance1043:27 main tests/248 JUnit records,
six real complete predictive preparation gates, four current real generation
report-format checks and four expected legacy-report rejections. The older
ALIGNN939/NequIP941 reports predate exact reload instrumentation and are retained
without invented evidence. Diagnostic epoch metadata was derived from reports
for format interoperability, not an independent epoch audit. All eight diagnostic
quality reports are correctly rejected for the formal1000-attempt protocol.
Fourteen executed source hashes were independently checked against Git blobs.
Full generation gates and numerical training/1000-attempt acceptance still
require the actual full preparations and subsequent full executions.

## Independent saved-sample assessment

After a full generation case completes training and1000 attempts, submit the
CPU-only `scripts/assess_generation_quality.slurm` with `UGNN_PYTHON`,
`UGNN_MATRIX`, `UGNN_MATRIX_SHA256`, `UGNN_CASE` and a new `UGNN_OUTPUT`.
It runs `assessment.assess_generation_case`, binds the frozen full case and
selection history, checks the saved last/best/sample identities and re-scores
every saved attempt. It does not resample, deserialize a model or run a GNN.

`assessment.py` reads the original complete source/split at the runtime's
declared precision. It recomputes the training fingerprint and full train-only
volume prior, then replays the original `StructuralQuality` scorer in a separate
process: geometric validity, uniqueness, training novelty, assigned-reference
matching/RMS and volume/density distributions. Every per-attempt observation and
aggregate must match; null groups stay null. Saved numerical-failure events stay
invalid attempts and are carried over as observations, not regenerated failures.
The comparison is an independent process/data replay of the original scoring
algorithm, not an independently implemented geometry algorithm.

The scorer, geometry loader and fingerprint source must match the recorded
execution commits. Torch, NumPy, ASE and Pymatgen versions must match both original
reports. All input reports/source/split/samples/best bytes and source/version
identity are rechecked after scoring. New output reports retain their SHA chain,
CPU wall time/RSS and source hashes. Inputs and the original case status remain
unchanged. A passed full assessment sets `formal_generation_quality_verified`
in its own report; the collector must still bind this proof to the formal case
and account for every other required training/paper gate.

For the existing64/16/16 diagnostics only, run the explicit diagnostic command
inside CPU Slurm with the matching provider environment:

```bash
"$UGNN_PYTHON" scripts/assess_generation_quality.py --diagnostic \
  --training-report runs/pilot-generation-953-cgcnn/pretrained/report.json \
  --quality-report runs/pilot-generation-953-cgcnn/pretrained/quality/metrics.json \
  --output runs/new-cgcnn-diagnostic-rescore
```

This requires the frozen8-attempt/1-draw/seed456 diagnostic protocol and100x2
steps. Its report is explicitly diagnostic, with
`formal_generation_quality_verified=false`. It may re-score legacy geometry
without inventing missing training reload evidence; it does not accept legacy
reports as complete formal training. Pure controls do not substitute for actual
CPU numerical replay or a future full1000-attempt assessment.

Source d6a71f6 passed CPU Slurm1045 acceptance:29 main tests/236 JUnit records,
including two actual geometry cases, then all eight original-provider diagnostic
CLI replays. All64 saved attempts and full64-structure training priors/fingerprints
matched, including49 valid samples and15 invalid ones; one whole case had zero
valid samples, exercising null groups. Test-process guards forbade `torch.load`,
`torch.jit.load` and neural-module calls during every replay. All original input
bytes stayed unchanged. Ten recorded execution-source hashes and seven scoring
source hashes per replay were checked against Git blobs. These counts establish
diagnostic numerical interoperability only, not full generation quality or a
comparison of model quality.1044's initial controller argv failure is retained.
