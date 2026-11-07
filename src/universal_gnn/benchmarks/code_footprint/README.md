# Committed adapter source inventory

This CPU-only software-cost supplement measures the explicit boundaries in
`manifest.py`: shared contracts, feature adapters, readouts, property definitions,
task wrappers, the common training/inference/generation engine, shared backbone
infrastructure, four official provider adapters, and the KNN+GCN plugin example
with its configuration counted separately. Each path belongs to one group.
Shared code is counted once rather than charged to every task. A provider's
nonperiodic adapter is included where present. Upstream installed packages are
excluded; these counts describe UGNN integration code, not the original GNN size.

Input: a Git repository and `HEAD` or a full immutable commit. The implementation
uses Git tree entries and exact regular blob bytes, never untracked/generated
files or working-tree edits. It rejects missing selectors, overlapping groups,
symlinks/submodules within selected boundaries, unsafe paths and invalid Python.
The executing producer must itself match committed source. Earlier measured
commits can therefore be inventoried by a newer, explicitly identified producer.

Output in a fresh directory: `report.json`, `summary.md`, `files.tsv`, and
`output-sha256.json` (hashes the other three files). JSON retains every selected
path, Git object, SHA256, group and count, plus all unselected tracked paths.
Directory selectors include recursive `.py` files; exact selectors may also
include JSON/YAML configuration. Only the declared boundaries are measured;
graph/data services, experiment machinery, tests, docs and other providers are
outside the inventory. This is not a whole-project total.

Physical lines use UTF-8 `splitlines()` and include comments/docstrings/blanks.
Nonblank lines exclude only whitespace-only lines, retaining comments/docstrings.
Python statement nodes count every `ast.stmt`, including compound statements,
definitions and docstring expressions; configuration contributes zero statements.
Identical blobs at different paths count as different files. These mechanical
counts are not minimum/marginal code for a new property, development time,
maintainability, usability or performance measurements. No comparison with an
unmeasured external implementation is implied.

From a clean pinned checkout, in an allocated CPU Slurm job:

```bash
PYTHONPATH=src "$UGNN_PYTHON" scripts/measure_code_footprint.py \
  --repository . --commit HEAD --output runs/NEW-source-inventory
```

The public CLI requires `SLURM_JOB_ID` and needs no Torch, NumPy, model weights,
datasets, GPU or network. It does not alter experiments or their acceptance index.
