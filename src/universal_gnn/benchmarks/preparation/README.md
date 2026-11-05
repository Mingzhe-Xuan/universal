# Full predictive pair preparation

This module prepares any of the60 predictive initialization pairs in the frozen
144-case matrix: four original providers, five tasks and three training seeds.
Generation has its own [preparation entry](../generation/README.md).
It creates preflight evidence and resolved configs, with zero formal trainings.

`specification.py` checks both full frozen case recipes and their actual seed,
original provider environment, clean fixed Git checkout, running same-user Slurm
GPU allocation and finite time limit. Complete source/split hashes, counts and
ordered training indices are checked. Existing primary cases/claims and reused
preparation output paths are refused; keep20GiB free disk reserve.

`runtime.py` lazily invokes the existing upstream parity, full graph scanner,
paired capacity, model builder and derivative validators. It imports numerical
dependencies only in Slurm runtime calls. CGCNN native parity uses copied
examples and an unused CSV label slot; model inputs, real labels, actual
training config and original upstream graph/basis/features/head are preserved.

`predictive.py` runs original two-structure parity, constructs every complete
training graph, and probes both initializations with at least100 measured
minibatches, rechecking both at a common accepted batch. Existing typed CUDA OOM
handling alone may lower that common batch. Worker-updated parameters are
discarded; whole-scratch native calibration uses only complete training data.
No data/atoms/neighbors/cutoff/dtype/epochs/task or trainable components are reduced.

Forcefield and dielectric then freshly reconstruct both modes at the actual
training seed and run the existing worst-input numerical derivative/geometry
checks on CUDA float32. Forcefield requires force and stress finite differences;
dielectric requires the response-auxiliary derivative check. Original tolerances
are unchanged. Direct scalar, classification and spectrum readouts omit this
inapplicable derivative stage. Finally both modes pass the full existing
[formal execution gate](../execution/README.md), including original artifacts,
all graph rows/extrema, complete capacity SHA chains, versions and source.

From a clean fixed source checkout, submit:

```bash
export UGNN_PYTHON=/home/xmz/.venvs/universal-mace/bin/python
export UGNN_MATRIX=runs/arxiv-v1/definition-947/matrix.json
export UGNN_MATRIX_SHA256=b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651
export UGNN_PAIR=seed-456--forcefield--mace
export UGNN_OUTPUT=runs/arxiv-v1/new-full-preparation-attempt
sbatch scripts/prepare_predictive_pair.slurm
```

The wrapper requests1GPU/2CPU/64GiB/16h/no-requeue. This is a finite initial
preparation allocation, not a measured formal-training budget. Capacity worker
timeout defaults7200 seconds. CGCNN/ALIGNN use `universal-official`, MACE
`universal-mace`, NequIP `universal`. CLI arguments are the full matrix plus
`--matrix-sha256`, `--pair`, fresh `--output` and optional `--timeout`.

Outputs include `report.json`, two original input configs, complete
`graph-scan/`, independent/common rounds in `capacity/`, final resolved configs
and applicable `derivatives-pretrained.json` / `derivatives-scratch.json`.
Failed attempts remain in place. During the last internal full-gate checks the
report has `final_gate_check_pending:true`; only successful job completion and
the final `false` flag make it ready for a dependent launch gate. External
controllers must use Slurm afterok rather than polling a provisional report.

After successful preparation, use the separate
[pair dispatcher](../submission/README.md). It repeats full checks and allocates
formal training time from measured capacity. Prep request submission or a passed
mock test is not actual full-data graph/capacity/physical acceptance. Formal
training still starts fresh, and paper acceptance requires independent heldout
re-score, applicable trained-model physical checks and full inference evidence.
