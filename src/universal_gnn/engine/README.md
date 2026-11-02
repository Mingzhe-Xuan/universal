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
