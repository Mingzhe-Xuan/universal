# Engine

Configuration and property/dataset bindings are saved with model state. Training and predictions
must identify real structure IDs and source hashes. Derivative inference uses `eval()` with input
autograd enabled. Acceptance reports distinguish training data from held-out predictions and do not
interpret a 10-structure execution test as generalization performance.
# Generation and inference

`ugnn train CONFIG --output runs/NAME` also accepts `task.kind=generation`; denoising targets
come from known periodic corruption of real structures, without DFT. The small-data acceptance
runner intentionally overfits one fixed corruption and records that limitation. It reloads the
checkpoint, compares both score heads, and samples from random fractional coordinates and a
composition-based initial volume. Sampling quality and close contacts are reported separately.

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
`checkpoint_every` is set. Fixed-corruption generation rebuilds the same corruption from the saved
seed; this preserves the existing small-data objective, not fresh-noise diffusion training.
