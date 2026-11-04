# Engine

Configuration and property/dataset bindings are saved with model state. Training and predictions
must identify real structure IDs and source hashes. Derivative inference uses `eval()` with input
autograd enabled. Acceptance reports distinguish training data from held-out predictions and do not
interpret a 10-structure execution test as generalization performance.
# Generation and inference

`ugnn train CONFIG --output runs/NAME` also accepts `task.kind=generation`; denoising targets
come from known periodic corruption of real structures, without DFT. New training uses
`per_epoch_structure_v2`: stable IDs and epochs determine fresh noise, with separate fixed
validation/test streams and a training-only volume prior. Explicit legacy fixed noise remains
available. Checkpoint reload, complete held-out denoising and independent generated-structure
quality have separate reports. See [generation protocol](generative/README.md).

`ugnn infer CHECKPOINT DATASET --output results/predictions.json [--limit 10]` runs reloaded
models on structures without requiring labels. Property and force-field outputs retain the
checkpoint's units; generative checkpoints emit structures with the requested composition.

# Flag CLI and continuation

`configuration.py` safely reads YAML/JSON and merges explicit CLI identity/path flags above file
settings, then checkpoint defaults. `runtime.py` owns run-scoped append logs and atomic checkpoint
writes. The flag CLI uses separate logging directory, checkpoint file and prediction JSON paths;
legacy subcommands remain compatible. Checkpoint format remains 2 for model reconstruction;
optional `training_state.version=1` stores Adam, completed epochs, data fingerprint, history and
Torch RNG. Legacy weight-only files are explicitly identified as warm starts.

`run_training(..., resume=..., checkpoint_path=..., event_callback=...)` works for supervised,
forcefield and generation tasks. Epochs is the cumulative target. Full continuation requires the
same selected labelled structures/bindings and seed; model/task mismatch fails before training.
The CLI defaults to atomic per-epoch snapshots, while the legacy API keeps final-only saving unless
`checkpoint_every` is set. Generation preserves its explicit noise version and declared sampling
settings on full resume; unversioned objectives require a weights-only warm start. Fresh-noise
training resumes by epoch/ID without changing perturbations or validation selection history.

## Extension/version reconstruction

Checkpoint containers remain format 2. New snapshots also store four `contract_versions` and
extension source fingerprints; model/graph code mismatches fail before loading weights. Resume
fingerprints include imported topology and graph attributes, while data without graphs retain their
old fingerprint convention. Graph configuration is part of model compatibility. Dataset/config files
without explicit versions remain legacy-compatible; unsupported explicit versions fail closed.
The normative specification is [docs/standards.md](../../../docs/standards.md).

## Dataset size, batches and precision

Training uses all records by default. `structures: 10` is an explicit execution-test subset;
`structures: null` or `all` means all records. Subsets use `dataset.selection: first` (default)
or `random` with `dataset.selection_seed` (otherwise the training seed). Reports and epoch events
state the selected count; reports also state the available count and complete data fingerprint.
Only the first `report_structure_limit` records (default 1000) are embedded in a report, explicitly
marked when truncated. Predictions are embedded by default up to 1000 records; set
`report_predictions` explicitly or run inference for the complete output. Report truncation does
not limit training, evaluation or checkpoint reload verification.

`batching.py` owns `batch_size` (default 32), optional `max_atoms`, `shuffle` (default true for
training) and per-epoch deterministic ordering. Every selected record is visited each epoch,
including the final partial batch. A structure exceeding max_atoms fails explicitly.
`metrics.py` computes label scales over the complete selected dataset and accumulates regression
errors by finite label elements (classification by samples), independently of batch boundaries.
Epoch loss describes minibatch predictions before their respective updates. Initial/final metrics
use complete dataset evaluation. Ordinary training does not require monotonic loss decrease;
real-data fine-tuning acceptance additionally checks decrease and backbone updates externally.

An explicit source-bound split manifest opts supervised/force-field training into
[independent validation/test scoring](evaluation/README.md). Training requires the
train partition; validation selects a weights-only best checkpoint and optional early
stopping, then the best model scores the complete test partition. Reports keep these
held-out results separate from training loss. This new path awaits numerical Slurm
validation; no-manifest runs retain the training-only interpretation above.

New training defaults to `dtype: float32`; `float64` remains available for derivative accuracy.
Checkpoint reload/inference uses its saved dtype. Legacy checkpoints lacking dtype retain float64.

## CUDA capacity preflight

The isolated [benchmark preflight](../benchmarks/README.md) tests the complete training
step and reduces batch size only after confirmed CUDA OOM. Each attempt starts in a new
process, and its updates never enter formal training. A successful candidate writes its
batch size into a resolved config; dataset-wide coverage and generation sampling need
their own checks. Ordinary training does not silently retry OOM or change batch size.
Full resume requires the same batch size, atom budget, shuffle, dtype and selected labelled data;
ordering is derived from seed and completed epoch, while Torch stochastic state and Adam are saved.
Derivative inference keeps autograd enabled. Fixed-corruption generation uses per-structure seeds
(`generation_corruption: per_structure_v1`) and minibatches; old fixed-batch generation checkpoints
remain inferable but require an explicit weights-only warm start to change that training objective.

JSONL datasets use byte offsets and a streaming hash (`data/indexed.py`); records become tensors
only when requested. JSON envelopes and ASE/plugin inputs currently retain their existing eager
loader, so convert large datasets to standard JSONL for bounded tensor memory. JSONL inference
(`--results predictions.jsonl`) writes metadata, per-structure prediction/generation records and a
completion record incrementally to an atomic output file. Ordinary JSON output retains CPU results
for compatibility but still evaluates geometry/model graphs one minibatch at a time.

Force-field `task.supervised_outputs` selects labels and losses independently of prediction keys.
Only selected data bindings/scales/labels are required; missing selected labels remain errors.
The default is E/F/S for old configurations/checkpoints. Changing supervision is rejected for full
continuation; reports record supervised_outputs and checkpoints persist the selected scales/config.

## Component training and reconstruction

`optimization.py` owns disjoint backbone/readout/optional-adapter parameter groups, persistent eval
mode on frozen components, parameter/buffer state guards and auditable component specifications.
Freezing never wraps forward in no_grad or detaches native features: coordinate/mixed gradients
and gradients through a frozen head to its input are preserved. All-frozen models are inference-only.
`warm_start.py` preflights keys/shapes/implementations/semantics and strictly initializes explicitly
selected compatible components, records source hashes, and builds a new optimizer. Full resume
requires identical architecture, policy and parameter-group maps. prediction and optimization are
rejected for generation. Old configs retain their original flat optimizer and state keys.

`optimization.backbone_eval: true` keeps the backbone in eval mode while train_backbone may
remain true: parameter and input derivatives stay enabled, with running-statistics/dropout
behavior fixed. This is explicit and part of resume compatibility; absent/false retains the
historical policy representation. New official CGCNN/Equiformer forcefields require it when
training backbone parameters, following observed BN coupling/stochastic batch evaluations.
Verified FeatureSpec derivative-capability upgrades from false to true alone are recorded and
accepted on checkpoint replay. Capability downgrades, dimensions, representation, layer or policy
changes still fail strict reconstruction; native tensor state and optimizer mapping do not change.
# Native component ownership

`component_views.py` provides non-registering views of the unchanged official
model. Native `backbone` owns the original body; `readout` owns the original
pooling/head/normalization modules listed in its task contract. Optimizers contain
each parameter once. Shared parameters between the roles are rejected. Frozen
components keep parameters, persistent buffers and eval modes fixed while input
gradients remain enabled.

Full resume requires the same head mode. Explicit backbone warm-start between
native/reset modes transfers only the body, preserving the target's head. Original
head tensors and the transfer boundary are listed in the warm-start report.

Checkpoint reload acceptance compares every persistent state tensor exactly
(including shapes/dtypes), then compares predictions under a strict deterministic
algorithm scope. Existing numerical tolerances are unchanged. The previous
deterministic/warn-only settings are restored even on exceptions; training updates
remain outside this scope. `reload_verification` records this distinction.
`run_training` defaults `CUBLAS_WORKSPACE_CONFIG=:4096:8` before its CUDA work;
set that environment variable at process startup when calling from an application
that already initializes CUDA. Explicit caller settings are preserved.
