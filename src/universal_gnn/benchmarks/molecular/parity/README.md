# Complete molecular original-network comparisons

This module compares pre-readout features and the original task output for all900
source-ordered ethanol training records, separately for each declared whole-body
initialization. CGCNN/ALIGNN/MACE/NequIP have two modes; the directory KNN+GCN
plugin has only scratch. It uses no test labels, target fitting or optimizer.
The100000-record source,900/100/99000 partition and original author cohort stay
unchanged. This is numerical compatibility evidence, not full fitting or quality.

`contracts.py` checks complete ordered comparison metadata without Torch/NumPy.
`runtime.py` requires a CPU Slurm allocation, the registered provider environment,
the reviewed complete graph-report SHA and its exact exported configurations.
Only the execution device changes to CPU. MACE/NequIP scratch retain the accepted
900training-only statistics. Registered public artifact hashes, whole-body
initialization coverage and original graph provenance are checked again.

`references.py` uses a same-state copy of the original learned network. This
isolates input/feature adaptation; it does not independently certify checkpoint
loading or a fresh constructor. Those remain tied to the previous registered
provider/initialization acceptance. Independent nonperiodic ASE topology feeds
CGCNN's original Gaussian basis/network and ALIGNN's upstream graph builder and
network. The frozen ethanol data have regular nonempty neighborhoods, which this
CGCNN reference explicitly requires; it does not claim an original unpadded
reference for arbitrary ragged molecules.

MACE uses the original calculator's full descriptors, energy and forces. NequIP
uses the original calculator, type mapping and `NeighborListTransform(NL="ase")`.
The ASE backend avoids the previously reproduced nonzero nonperiodic image
offsets in installed matscipy. All native/reference neighbor pairs must agree,
all image offsets must be zero and other original input fields remain exact.
The learned network, published weights and production input code are unchanged.
The plugin compares its direct GNN/graph-builder calls with StandardBackbone.

Original comparison tolerances remain rtol3e-5/atol3e-6, or MACE's existing
rtol2e-5/atol2e-6. Nonfinite values, any comparison failure, changed persistent
state or accumulated parameter gradients fail the run. State/config/source
hashes and complete900-row per-mode numerical summaries are saved. The summaries
include shapes, errors and actual/reference tensor hashes; they are not raw
feature arrays and do not support a claim of independent saved-array rescoring.
Failed prefixes remain evidence and an existing output directory is refused.

```bash
PYTHONPATH=src python scripts/verify_molecular_parity.py \
  --model cgcnn --graph-scan runs/REVIEWED-COMPLETE-GRAPHS \
  --graph-report-sha256 REVIEWED_REPORT_SHA --output runs/NEW-PARITY
```

Submit through Slurm using the model's existing environment. A successful report
certifies this explicit CPU same-state reference scope only. It keeps
`formal_training_ready=false` and `cuda_capacity_acceptance=false`; the existing
actual-CUDA, paired-capacity/physics, formal launch and full heldout quality gates
still apply. The original fixed-source CUDA requests are not changed by this
module. See the [parent module](../README.md) and
[experiment plan](../../../../../docs/plan/arxiv_v1_experiments.md).
