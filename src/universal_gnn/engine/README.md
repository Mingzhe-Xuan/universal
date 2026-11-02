# Engine

Configuration and property/dataset bindings are saved with model state. Training and predictions
must identify real structure IDs and source hashes. Derivative inference uses `eval()` with input
autograd enabled. Acceptance reports distinguish training data from held-out predictions and do not
interpret a 10-structure execution test as generalization performance.
