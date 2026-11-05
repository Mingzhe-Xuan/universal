# Independent predictive assessment

The campaign runs only training seed123 (48 primary cases); archived144-case
definitions remain provenance. See [the active scope](../../../../configs/arxiv_v1_scope.json).

`contracts.py` validates raw source IDs, label bindings, precision and output shapes.
`rescoring.py` re-scores all saved test outputs without loading a GNN, using the
original metric accumulators and CPU softmax convention. `streaming.py` checks
every complete-source inference record, shape, finite scalar and completion marker.
`runtime.py` binds formal training/preparation evidence, runs unchanged trained-best
physics and CPU inference, then provides separate independent saved-output validation.
Numerical model operations are lazy and isolated in `numerics.py`.

Inputs are the frozen original matrix, one selected completed case and fresh output
directories. Outputs preserve source/config/checkpoint/report hashes and metrics;
failed attempts remain. CPU model post-processing and the independent validator
run as separate Slurm jobs. Both refuse existing output directories and preserve
all original training, last/best checkpoint and source bytes.
Saved forcefield test rows require `natoms`; graph-level gap/classification/tensor/
spectrum rows use the raw source atom counts and do not require that field. Any
explicitly recorded count is still checked against the original source.
The post-processing validator has its own source hashes, which must match the
independent stage. Its version is separate from the earlier training commit;
model/training/data compatibility still uses the original full preparation gate.

## Public stages

Use the matching original provider Python from a clean immutable source checkout.
Submit `scripts/assess_prediction.slurm` with these exported variables:

```bash
export UGNN_PYTHON=/home/xmz/.venvs/universal/bin/python
export UGNN_MATRIX=runs/arxiv-v1/definition-947/matrix.json
export UGNN_MATRIX_SHA256=b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651
export UGNN_CASE=seed-123--forcefield--nequip--scratch
export UGNN_STAGE=post
export UGNN_OUTPUT=runs/arxiv-v1/postprocessing/seed-123--forcefield--nequip--scratch-attempt-001
sbatch --no-requeue scripts/assess_prediction.slurm
```

Record the actual post-processing job receipt. Submit a separate `verify` job only
after its success (`--dependency=afterok:POST_JOB` for a still-retained job handle),
with `UGNN_POSTPROCESSING` pointing to that output and `UGNN_OUTPUT` a fresh
independent-validation directory. Never resubmit a case or assume a timeout means
failure. For purged terminal handles, reconcile the retained request and artifacts
instead of adding a dependency on an unknown job.

The wrapper requests2CPU/32GiB/16hours and noGPU. These are finite initial CPU
post-processing limits, not measured guarantees or the GPU training allocation.
All source structures are inferred in the original common mini-batch size and
float32. Forcefield and dielectric use their original two worst training inputs
and unchanged trained-best physical validator. No new DFT is involved.

`post` ends with `awaiting_independent_validation`, not scientific acceptance.
`verify` prohibits Torch/JIT checkpoint loads and neural module calls, independently
re-scores the saved raw labels and validates every ordered source prediction,
output shape, finite scalar, header, final marker and input/output hash. Forcefield
stress is checked for format/physical consistency, with no supervised accuracy claim.

For saved-output diagnostics only, use this inside a CPU Slurm allocation:

```bash
"$UGNN_PYTHON" scripts/assess_prediction.py rescore --diagnostic \
  --training-report SAVED_TRAINING_REPORT --output NEW_DIAGNOSTIC_DIRECTORY
```

Re-scoring preserves the original physical-unit metric accumulators, including
CPU dtype-bound softmax and tied-score AUROC, per-component errors and zero-label
tensor groups without symmetry projection. It does not recompute normalized loss
or turn a small diagnostic split into a formal full-data result. Direct metrics
retain1e-12 comparison tolerances; derived float32 energy/atom retains the existing
1e-5 relative/1e-6 absolute division-rounding tolerance. No training count is added.

Early saved classification diagnostics predate the two balanced-accuracy fields.
Only saved-only diagnostics can opt into `--allow-legacy-classification`; this
still compares every originally recorded field at the same tolerance and marks
balanced accuracy as newly computed. Formal post/verify always require the full
current metric schema. No archived report is rewritten.

## Accepted numerical scope

Sourceba41cf2 passed CPU1201:37 main controls/291 JUnit records,40 original
diagnostic reports (640 test structures), six complete forcefield training gates,
984 raw test structures and9396 saved source predictions, with17 executed source
Git blobs verified. Fresh991 CPU1202 trained-best physics/full1566 inference and
independent no-model1203 both completed successfully. This establishes saved-output
replay across five task formats and a real forcefield post/verify run. Full-data
scalar/classification/tensor/spectrum model inference remains to be exercised as
those formal cases complete; preparation or fixtures are not scientific results.
