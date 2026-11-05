# Scripts

## Published pretraining IDs

`audit_pretraining_ids.py` compares complete frozen material IDs with a
SHA-bound published checkpoint's train/validation/test roster. It records
parameter-training and model-selection exposure separately; a missing ID is
never interpreted as proof of unseen geometry or labels. Run through Slurm
using `audit_pretraining_ids.slurm`; configure `UGNN_AUDIT_CONFIG`,
`UGNN_AUDIT_OUTPUT` and the explicit `UGNN_REFERENCE_RELATION`.
See the [audit contract](../src/universal_gnn/benchmarks/audits/README.md).
The selected ALIGNN archive has two published train/test material-ID overlaps.
To report these explicitly, set `UGNN_REFERENCE_POLICY=report_ambiguity`;
the default strict policy rejects them. Neither mode certifies unseen geometry.

## Saved tensor groups

`evaluate_tensor_groups.py --report runs/CASE/report.json --shape 3 3 --output NEW`
independently verifies saved complete test predictions and their source labels,
then reports absolute/component errors for zero and nonzero target groups.
Use `evaluate_tensor_groups.slurm` with `UGNN_TENSOR_REPORT` and
`UGNN_TENSOR_OUTPUT`. It does not train or run inference. See the
[assessment contract](../src/universal_gnn/benchmarks/assessment/README.md).

## Scalar training-mean baseline

`evaluate_scalar_baseline.slurm` uses `UGNN_BASELINE_CONFIG` to fit the entire
frozen training partition's scalar mean and independently score every validation
and test record. `UGNN_BASELINE_OUTPUT` must be new. The CLI refuses execution
outside Slurm; it writes original-unit MAE/RMSE, complete prediction JSONL and
source/split/config/execution provenance. No GNN or GPU is used. See
[the baseline module](../src/universal_gnn/benchmarks/baselines/README.md).

## Physical-task acceptance

`validate_task_derivatives.py --config CONFIG --output NEW_JSON` requires Slurm
and checks the actual configured force-field or graph-level rank2 response model.
See [the numerical contract](../src/universal_gnn/benchmarks/validation/README.md).
`validate_physical_tasks.slurm` runs the independent finite-difference validator
fixtures on CUDA plus energy-per-atom and held-out/resume regression cases.
Original model acceptance and full-data capacity are separate gates.

`validate_checkpoint_verification.slurm` checks exact tensor state, corrupted
states, deterministic/warn-only restoration, real CUDA comparison and supervised,
force-field, generation and continuation integration. Prediction tolerances stay
unchanged; training updates remain outside the deterministic verification scope.

## Generation protocol acceptance and quality

`validate_generation_protocol.slurm` runs43 numerical/control main cases with zero allowed skips,
including fresh-noise training, complete validation/test, exact continuation, erased sampling
geometry, structural scoring and automatic native-calibration routing. It writes JUnit and
source-bound acceptance metadata. Passing it does not replace original-model GPU task tests.

`evaluate_generation.slurm` requires `UGNN_GENERATION_CHECKPOINT` (the last checkpoint with
validation history) and a new `UGNN_GENERATION_OUTPUT`. It verifies validation-best weights,
uses training-only priors and writes1000 conditional samples by default. Configuration steps
are retained. Small diagnostics and scientifically invalid structures remain explicit; OOM
terminates instead of becoming an invalid scientific sample. See
[the protocol](../docs/plan/generation_protocol.md).

This directory contains Slurm, dependency and dataset preparation entry points. Source changes are
made and committed locally, then pulled on Guqq2. Downloaded datasets and generated job outputs
remain ignored. Each remote session is recorded in docs/agents/gpu.md before connection.

## Arxiv experiment preparation regression

`scan_training_graphs.py` constructs complete original training graphs, including active response
or generation geometry graphs. Use the provider's own environment and a GPU Slurm allocation:

```bash
sbatch --partition=compute --nodelist=node42 --gres=gpu:1 --cpus-per-task=1 --mem=8G \
  --time=12:00:00 --output=runs/graph-scan-%j.out --error=runs/graph-scan-%j.err \
  --wrap='cd /home/xmz/universal && PYTHONPATH=src /home/xmz/.venvs/universal-official/bin/python scripts/scan_training_graphs.py --config PATH_TO_FROZEN_CONFIG.json --output runs/NEW_GRAPH_SCAN_DIRECTORY'
```

Replace the config, fresh output path and environment for each actual case. Both CGCNN and ALIGNN
use `universal-official`; MACE uses `universal-mace`, NequIP uses `universal`. The scanner retains
all source-ordered training records, native directed edges or CGCNN padded slots, ALIGNN triplets,
active auxiliary graph edges and maximum endpoint degree. It loads the original pretrained
topology reference without running the GNN; this does not validate scratch initialization.
Receipts bind full input identities and graph implementations. Changed source/split/checkout,
failed graph construction or a model forward prevents probe publication. Clean-geometry coverage
does not cover all generated noisy states or sampling trajectories.

Before real scans, run `python scripts/validate_graph_scan.py --output NEW_RESULT.json` in the same
GPU allocation/environment. Its five numerical tests cover native output format fixtures,
actual auxiliary radius graphs, active module selection and eager/scripted forward guards.
They do not replace real provider full scans. Seven stdlib controls can run without Torch.
Neither numerical checks nor real provider full scans have been executed at this publication.

After restoring and recording the task-owned environment, submit
`sbatch scripts/validate_arxiv_preparation.slurm`. It requests a GPU, runs the existing
suite plus held-out integration tests, then runs scalar/classification/spectrum/
tensor-response/force/generation complete-step preflight checks and separate sampling.
Disposable fixture plugins request allocations larger than physical GPU memory to
verify actual CUDA OOM halving and batch-one failure. All fixture data and results
remain under ignored `runs/`. These are synthetic integration checks, not full-data
capacity certification. Use `--export=ALL,UGNN_TEST_ENV=universal-mace` or
`universal-official` for the isolated model environments. The job records the commit,
package inventory, JUnit result and explicit acceptance JSON; failures stop the job.

`sbatch scripts/validate_arxiv_protocols.slurm` independently runs the 18 pure
control/split/metric/selection protocol tests with system Python on a CPU allocation.
It can run while scientific dependencies are restoring, records commit/job/result
JSON, and does not certify neural-model, CUDA or full-data resource behavior.

`recover_environment_cache.slurm` hashes/extracts only the public wheel URLs named
by an official SHA256 catalog. It handles pip's separate `http-v2/*.body` format and
legacy `http/` cc4 msgpack bodies, preserving source caches. Verified modern bodies
are hardlinked where possible; legacy bodies need a copy. A 20 GiB free-space reserve
is enforced, and missing/mismatched resources remain explicit in the JSON report.
It never scans arbitrary cache entries or installs a partial environment. Large cache
verification needs the provided 12 GiB CPU Slurm allocation; do not run it on login.

`prepare_arxiv_jarvis.slurm` prepares full fixed JARVIS releases, independently of
Torch/environment restoration. Default bandgap preparation also creates binary
classification in the same JSONL/split. Set `UGNN_DATA_KIND=phonon_dos` for all valid
200-channel phonon DOS, or `electron_dos` for optional 300-channel electronic DOS.
Source archive paths and fresh output folders are explicit; all source records are
visited with audited exclusions and no atom-count/first-N cap. The job runs the five
preparation fixture tests before full conversion and writes actual counts/hashes.
See [the preparation module](../src/universal_gnn/data/preparation/README.md).

`prepare_arxiv_mlearn.slurm` verifies and streams the twelve pinned MLearn E/F
sources. It retains the released test frames and makes validation groups only
from released training, with no structure-size cap. It audits shared AIMD families
between the author's train/test files rather than claiming trajectory independence.
All twelve JSON files and their download receipt must be prepared before submission.

After a successful common-resource transfer, `restore_common_base.slurm` verifies
all chunks, the complete archive and each listed wheel, then installs the pinned
foundation packages into the task-owned base with `--no-index`. It preserves a
20 GiB reserve, rejects conflicting output files and runs archive fixture tests.
This staged base is still incomplete until Torch/CUDA, provider extras and actual
model/GPU checks pass; `pip check` alone is not a model-readiness certificate.

After all 16 Torch/CUDA wheels are transferred, `install_offline_cuda_base.slurm`
rechecks their fixed official SHA256 catalog, refuses missing resources, installs
the exact CUDA build offline, runs `pip check`, and adds only the new shared-base
path to the four task-owned model environments. It does not alter their isolated
e3nn/PyG packages or any other project's environment. Provider extras and the full
Slurm model/GPU regression remain separate gates before scientific training.
# Real small-data matrix

Download the named author archives listed in `prepare_acceptance_data.py` to `data/downloads`.
Run `python scripts/prepare_acceptance_data.py` for bounded small-cohort extraction; use Slurm
for larger processing. It stores original URLs/SHA256/record indexes, refuses duplicate geometries
and missing labels, and explicitly lists data that remain pending.

Prepare configurations with `python scripts/run_matrix.py prepare --output runs/acceptance`.
The base manifest writes 66 cases for six models and eleven tasks; append the DFPT, Raman and
optical cohorts below for the complete 96-case execution matrix. Submit only after
the required environments and dataset files are present:
`sbatch --array=0-65%8 scripts/matrix.slurm` for the base manifest, or `--array=0-95%6`
for the fully prepared manifest. For another output directory set `UGNN_MATRIX` explicitly.
Use `python scripts/run_matrix.py summarize --matrix runs/acceptance/matrix.json` to collect
reports; missing data and failed cases remain visible. MACE automatically selects its isolated
environment. No job treats unexecuted cases as passed. Each report includes its Git/Slurm provenance.

`run_matrix.py verify` replays a saved checkpoint against its original JSON predictions. Submit it
through `verify.slurm`, with the existing matrix path and matching array range. Old tensor bases
are reconstructed from checkpoint format, rather than silently using a new adapter default.

`prepare_dfpt_data.py` appends matched E/F/S, Born, and dielectric cohorts from published raw DFPT
ZIPs and their SHA manifest. Run batch XML parsing on Slurm. Energy supervision uses VASP's
electronic free energy, and stress is explicitly converted from ASE units; original Born components
are retained. Missing/invalid archives produce recorded failures, not fabricated labels.

`prepare_raman_data.py` derives 200-bin peak-normalized curves from CRD original tensors and
signed frequencies. Require exactly 3N frequency and tensor slots; reject incomplete mode mapping.
`prepare_optical_data.py` resamples published NIST TBmBJ trace-average epsilon2 and records a
finite-window principal-value KK postprocess. Both scripts append ten real structures to the manifest.
Numerical preprocessing and model execution on Guqq2 belong in Slurm.

`workflows.slurm` calls `run_workflows.py` for six backbones using matched forcefield/Born/dielectric
checkpoints. Each model runs ten structures through fixed-cell FIRE, short MD, Gamma modes,
IR/Raman/neutron broadening and real abTEM multislice STEM from MD snapshots.
`collect_evidence.py --matrices ... --workflows runs/workflows` checks actual saved reports,
unique IDs, optimization/checkpoint evidence, and finite nonconstant STEM image arrays.
It refuses missing/failed entries; controller retention is never used to invent historical job states.

`ugnn.slurm` forwards all user CLI arguments unchanged to `python -m universal_gnn.cli` in the
submission directory; create `runs/` before submitting. Set `UGNN_PYTHON` for a different task venv.
`validate_cli.slurm` checks the documented flags on ten real ALIGNN bandgap structures: 15 epochs,
resume to 30, inference, and parameter equality with an uninterrupted 30-epoch run.

`prepare_molecular_data.py` exports ten original ASE G2-1 molecular geometries and published
experimental ionization energies, plus matching local KNN edge records, in canonical dataset v1.
No new DFT or synthetic target is used. `validate_extensions.slurm` trains the custom KNN+GCN
directory example, resumes, predicts, and compares with uninterrupted training and imported graphs.
Use `sbatch scripts/validate_extensions.slurm` on Guqq2; reports/checkpoints remain ignored.

`validate_official.py` is an implementation-stage Slurm acceptance harness. It requires a published
checkpoint, ten labelled real structures and an independent native reference for the provider;
unsupported reference branches fail explicitly. It checks original descriptors/predictions, finite
first/second input derivatives, decreased ten-structure training loss, changes to original backbone
parameters and self-contained reload with deliberately absent external artifact paths. It does not
replace held-out evaluation or declare providers verified before their actual validation JSON exists.

`fetch_official_sources.py` downloads fixed CGCNN/Equiformer/OCP archives into ignored models/,
verifies and packages their original Python package files/licenses into a small offline tar.gz,
and rechecks every member against its source hash. It supports Python3.10. Source bytes are not
patched; unsupported symbolic links inside selected packages fail. Resource download/packing is
separate from the Slurm-only model validation and training scripts.

`diagnose_nequip_parity.py` is a bounded Slurm-only numerical diagnostic using the published NequIP
profile and ten real bandgap structures. It first verifies original/cloned model states exactly,
then records independent calculator and adapter force repeatability with JIT optimization on/off.
The JSON report is diagnostic evidence, not a relaxed acceptance test or a training benchmark.
The historical run_matrix uses explicit legacy variants; validate_official is the separate original
checkpoint/reference/ten-structure acceptance path.

`validate_force_only.py --output runs/NAME` runs on Slurm. It retains only original force labels
from ten real acceptance structures, initializes the official MACE backbone, trains the energy-derived
force predictor, checks trunk updates/loss decrease, full continuation and streamed reloaded inference.
No energy/stress labels are fabricated; reports keep geometry/source IDs and the force-only label set.

`validate_prediction_components.py --model cgcnn|mace --output runs/NAME` must run through Slurm.
It checks original-provider reference parity and ten-real-structure native linear/MLP frozen/full
training; CGCNN adds a real200-bin spectrum, MACE adds explicit-profile dielectric response and
frozen-backbone force-only training/resume/all-frozen inference. It checks component state deltas,
first-layer F, mode/parameter audits, rotation and force/strain finite differences. Native float32
finite differences use step.002,rtol.02,atol.002; analytic float64 units use stricter tolerances.
This is bounded execution acceptance, not held-out accuracy evaluation.

`sbatch scripts/validate_other_forcefields.slurm` assesses the other five original official
providers on the same ten-real-force-label cohort, frozen/full modes, with at most two array jobs
running concurrently. The script routes NequIP and Equiformer to their existing isolated envs.
`validate_other_forcefields.py` scopes provisional capability metadata to test-only factory instances;
production guards/default declarations remain unchanged until actual results justify enabling them.
It records original reference parity, force/strain finite differences, mixed gradients, eval/train
batch independence, frozen states, force-only optimization and checkpoint inference independently,
including failed stages. No original backbone layer/graph is changed and no DFT is executed.
`--fd-sweep` holds the model/probe fixed and records step convergence without training;
`--fd-step` changes only the numerical differentiation step, never rtol/atol. This diagnoses
truncation versus derivative failures before a candidate can be accepted.

`validate_forcefield_release.py --assessment runs/PASSED_CASE --output runs/RELEASE_CASE`
requires Slurm and a fully passed frozen/full assessment. It uses ordinary production constructors
without the candidate factory, resumes each saved mode by one epoch and performs fully frozen
force/stress inference. CGCNN additionally replays the real old771 bandgap checkpoint to verify
that newly verified derivative capability metadata preserves previous predictions.

`inspect_native_heads.py --model NAME --output runs/FILE.json` is a Slurm-only, bounded
inspection of the original artifact metadata, head module paths, scalar normalizers and original
forward sources. It runs no training and does not change model layers; tensor weights are
summarized by shape rather than exported. This establishes native-task contracts before wiring
the official prediction head into UGNN.

`install_official_extras.slurm` follows the shared CUDA base installer and verified native-wheel
staging. It checks all six pinned resource sizes/SHA values before installation, requires the
existing shared-base links and exact shared Torch metadata, and installs only into
`universal-official` without resolving dependencies from the network. It retains MACE's e3nn0.4.4
and the official environment's documented MACE/e3nn0.4.4 parent; NequIP retains its own e3nn0.5.8.
An exact child-owned e3nn0.5.8 overlay from the earlier installer is removed before installation;
unexpected versions or roots stop the operation without uninstalling parent packages. The installer
checks the three task environments and records complete package lists. A successful report proves
dependency metadata acceptance; original model/CUDA/derivative validation remains separate.
`sbatch scripts/prepare_arxiv_matrix.slurm` verifies all five complete primary input sources,
their source-ordered manifests and original model artifacts, then writes 144 separate configurations
and a frozen matrix into a new ignored run directory. It runs without Torch and launches no training.
Configurations pin both source bytes and canonical split SHA values. Initial batches and the
300-epoch/0.0003 learning-rate/30-patience baseline remain declared defaults; original-model,
derivative and paired CUDA capacity acceptance must still precede formal runs. See
[experiment definitions](../src/universal_gnn/benchmarks/experiments/README.md).

`download_offline_cuda_resources.py` resumes the fixed sixteen-resource CUDA catalog through
the approved loopback HTTP/SOCKS endpoint. Run inside Slurm after checking proxy health:

```bash
python scripts/download_offline_cuda_resources.py \
  --report "runs/cuda-transfer-${SLURM_JOB_ID}.json"
```

Stop any older writer to the same partial files before starting this replacement. It retains the
existing filenames, partial positions, official SHA values and 20GiB disk reserve. One curl process
appends up to eight bounded 1MiB ranges, reusing its connection; only the first operation generally
needs a new SOCKS handshake. Each operation has a 20-second connection and 30-second total budget.
Response Content-Range and received-byte accounting are checked; invalid appended suffixes roll
back to that group's prior prefix. Expected network interruptions retain contiguous received bytes.
Final SHA verification precedes atomic publication. A POSIX cache lock prevents two new writers;
the older downloader does not hold that lock and must be stopped separately. Rule rejections and
unknown errors stop the job. This stages resources only and performs no environment installation
or model computation. The complete verification receipt remains compatible with the existing
offline base installer, which independently hashes all sixteen wheels again.

# Original head acceptance

`augment_binary_metrics.py --reports REPORT... --output NEW_JSON` runs through Slurm
and derives balanced accuracy from the original binary held-out confusion counts.
It verifies reported test counts, retains original metrics and report SHA256 values,
and writes a separate supplement without changing reports, predictions or checkpoints.
Single-class tests have null balanced accuracy. New training reports include it directly.
The generation regression receipt checks all43 unique main cases by module and zero
errors/failures/skips; JUnit's total can additionally include successful unittest subtests.

Original scratch construction is separate from resetting a task head. Run
`validate_official_scratch.slurm` for CGCNN/ALIGNN and
`validate_native_neighbors.slurm` for MACE/NequIP before paper training. The latter
checks the original graph builders and complete train-only normalization. Use
`prepare_native_neighbors.slurm` with `UGNN_CONFIG`, `UGNN_RESOLVED_CONFIG` and
the provider's `UGNN_PYTHON` to produce a new bound scratch configuration.
See [initialization preparation](../src/universal_gnn/engine/initialization/README.md).

`validate_native_heads.py --model MODEL --output runs/native-heads/MODEL` must run
through Slurm. It compares original public predictions and physical normalization,
checks each independent freeze policy and mixed force gradients, trains on ten
real matching records where available, and checks checkpoint reload/resume.
Equiformer's registered IS2RE head has no matching labels in this cohort: only
original prediction and gradient diagnostics run; band-gap labels are never
substituted for relaxed-energy labels.

`validate_native_transfer.py` performs real-artifact body-only warm starts in
both head-mode directions, preserves target heads, streams all-frozen native
inference and replays actual pre-headmode checkpoints. Run through Slurm after
`validate_native_heads.py`; it writes bounded reports separately from weights.

`prepare_generation_pair.py` and `prepare_generation_pair.slurm` prepare one frozen full-data generation pair. See [generation preparation](../src/universal_gnn/benchmarks/generation/README.md) for required variables and separate train/sample outputs. They launch no formal training.

`evaluate_native_baseline.py` and `.slurm` run [full native-head baselines](../src/universal_gnn/benchmarks/native_heads/README.md) on the matching7580 bandgap or164 forcefield test records. These CPU Slurm evaluations do not add formal trainings.

`run_formal_case.py` and `.slurm` expose [formal predictive execution](../src/universal_gnn/benchmarks/execution/README.md) for the five predictive tasks. The Slurm-only `--check-only` mode audits real full preparation evidence without training; a formal run refuses existing case directories.

`run_generation_case.py` and `.slurm` provide separate [full generation training and quality stages](../src/universal_gnn/benchmarks/generation/README.md#formal-training-and-quality). `--stage check` validates both actual capacity chains; `train` preserves the full recipe and `quality` preserves1000 attempts/5 draws. Partial quality attempts remain available for audit and never reset the trained backbone.

`assess_generation_quality.py` and `.slurm` provide [independent saved-sample assessment](../src/universal_gnn/benchmarks/generation/README.md#independent-saved-sample-assessment) in CPU Slurm. Formal mode binds a completed full matrix case; explicit `--diagnostic` replays only the registered8-attempt protocol. Both recompute geometry/matching/distributions and full train-only priors from saved outputs/raw source, with no model loading or sampling.

`submit_formal_pair.py` and `.slurm` provide [deferred full-preparation gates and Slurm submission](../src/universal_gnn/benchmarks/submission/README.md). The CPU gate checks both initialization modes before submitting finite-budget GPU training. Generation quality and independent assessment follow via afterok dependencies; receipts and ambiguous attempts are preserved without blind resubmission.

`prepare_supplemental_tensors.py` and `.slurm` prepare [complete rank3/4 tensor datasets](../src/universal_gnn/benchmarks/supplemental_tensors/README.md) in CPU Slurm, retaining source values and jointly anchoring cross-task material groups to the frozen dielectric partitions. They produce data/audits, not training results.

`prepare_predictive_pair.py` and `.slurm` prepare [any full predictive initialization pair](../src/universal_gnn/benchmarks/preparation/README.md) from the original144-case definition, with each actual seed, original upstream parity, complete graph scan, paired100-batch capacity and applicable two-mode CUDA derivative checks. They submit no formal model training.


`run_tensor_case.py train|post|verify` is the separate full-data supplemental
rank3/4 entry; see the
[tensor execution contract](../src/universal_gnn/benchmarks/supplemental_tensors/README.md).
`run_tensor_case.slurm` requires an already successful independent pair gate
and measured reserved training budget. `assess_tensor_case.slurm` provides
CPU-only trained-best postprocessing and separate no-model full-output
acceptance. All stages require Slurm, fixed seed123/closed16 definitions and
fresh case/output paths; none submits or retries jobs automatically.

`submit_tensor_pair.py` and its Slurm wrapper provide managed submission only
after both original independent full tensor gates and exact retained successful
terminal proof. Each pair has two train/post/verify chains plus six afterany
recorders. `record_tensor_terminal.py gate|stage` preserves raw terminal
identities and report hashes. See the tensor module README for dependencies,
resources, separate claim paths and strict no-duplicate/unknown-claim behavior.

`prepare_frozen_experiment_definitions.py --output NEW_DIRECTORY` audits the
complete original dielectric/forcefield sources and emits8 separate seed123
head-only configurations, changing only `optimization.train_backbone=false`
relative to each original full pretrained recipe. See the
[frozen ablation module](../src/universal_gnn/benchmarks/frozen_backbones/README.md).
Run via CPU Slurm; this does not run official frozen preparation or training.

`run_generation_staged.py --stage check|train|quality|verify` separates complete
paired training readiness from failed untrained sampling preparation, preserving
original failed reports and the mandatory trained-best1000-attempt quality and
separate no-model CPU assessment. It accepts only active seed123 generation
cases. See the [generation module](../src/universal_gnn/benchmarks/generation/README.md)
for finite budgets, explicit invalid-sample policy and no-overwrite semantics.
