# Original-package runtime acceptance

These cases load original artifacts and use the corresponding provider environment. They are
invoked explicitly by Slurm validation scripts, separately from dependency-independent policy
tests. Do not run them on a login node or count static compilation as numerical acceptance.

`native_neighbors.py` is selected by `scripts/validate_native_neighbors.slurm`: MACE and NequIP
each run five tests for original nonperiodic graphs, complete train-only coverage, no GNN forward,
RNG preservation, bound receipt reuse, saved fresh-artifact provenance and tampering/partial-selection rejection. Provider selection
is mandatory via `UGNN_NEIGHBOR_PROVIDER`; an unavailable provider is a failure, not a silent skip.
Fresh constructors must actually consume the receipt and reject a changed graph during inference
reconstruction as well as training preparation.

Status: provider environments have passed CUDA dependency checks; actual original-constructor
and graph-calibration tests remain pending. Dependency checks do not establish these results.
