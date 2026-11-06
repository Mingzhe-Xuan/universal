# Complete nonperiodic and directory-plugin supplements

These nine seed123 forcefield cases are separate from primary48 and its eight
accepted MLearn runs. Eight cases compare original CGCNN/ALIGNN/MACE/NequIP,
whole-backbone pretrained versus scratch. One case trains the existing directory
KNN+GCN plugin from scratch; it has no invented pretrained checkpoint.

`source.py` audits all100000 original ethanol records, their unmodified source
order/geometry/species/nonPBC metadata and finite revised E/F labels. It verifies
all four author files, the fixed conversion audit and raw split-file SHA, and
rebuilds the declared partition from original author CSVs:900training,
100validation and99000test. The original1000test cohort is separately retained.
Validation comes only from the original1000development pool. Training seed123
never selects the partition. Zero force labels are kept. This complete scan
requires CPU Slurm; importing the module needs neither Torch nor NumPy.

The canonical manifest SHA used by training configurations differs from the raw
pretty-printed split-file SHA in the conversion audit. Both identities are kept
and checked. Units are already eV total energy and eV/angstrom forces; this module
does not convert labels a second time or supervise placeholder-cell stress.
These correlated trajectory tests do not establish new-molecule or independent
trajectory generalization, and no DFT is performed.

`definitions.py` takes the immutable947 primary matrix and complete input audit.
It inherits the original forcefield heads, loss bindings, full-body optimization,
float32, batch4 initial candidate,300epoch/patience30 and optimizer budget.
Both official initializations share the same molecular source and input profile.
CGCNN/ALIGNN explicitly select `molecular_radius`6angstrom/allneighbors/noPBC;
MACE/NequIP retain their original nonperiodic preprocessing. CGCNN retains its
forcefield backbone-eval policy. Native statistics must use only900training
records. The four paired-capacity groups remain explicit.

The plugin case uses `plugin:examples/custom_knn_gcn` for both standard GNN and
graph contracts, width16/two layers, explicit symmetrized KNNk2 and live distance
weights. It requires no supplied edge features. Source SHA values of its three
Python files are recorded after declared LF normalization. It reuses the same
E/F readout, data partition and training budget, with its own capacity/physics
and direct-plugin feature checks. Its `scratch` case label describes random
construction; no unsupported official-initialization keyword is passed to the
plugin factory.

```bash
PYTHONPATH=src python scripts/prepare_molecular_experiment_definitions.py \
  --matrix runs/arxiv-v1/definition-947/matrix.json \
  --output runs/arxiv-v1/molecular-definitions-NEW
```

Run the command inside a CPU Slurm allocation. A fresh output is mandatory.
The output contains `definitions.json`, `input-audit.json` and nine ordinary
training configurations in `configs/`. No job, optimizer or model is launched.
The reusable function returns the same definitions mapping and accepts explicit
data/raw/repository paths. A20GiB disk reserve is required before export.

Definitions and complete source validation do not certify original-model CUDA,
all native graphs,100batch paired capacity or mixed-size extrema, position finite
differences/mixed gradients, full best-validation training,99000heldout tests,
the original1000test cohort or separate independent assessment. Those remain
required before scientific acceptance. A plugin case has its own single-model
capacity gate; it does not claim an official pretrained/scratch pair.
