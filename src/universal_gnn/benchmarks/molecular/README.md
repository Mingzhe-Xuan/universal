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


Definition source1e19447 passed actualCPU1682/1683, both COMPLETED0:0:
44 standard-library tests,18 Git blobs, complete100000 source records/100000E/
2700000F, all four author files and exact CSV/partition/cohort checks. Nine configs
and four official pairs were independently checked, with26 metadata archives and
all prior310 scientific/20raw/34conversion/17original-input-CPU hashes preserved.
Wall11.5931seconds, process RSS194822144bytes. This is data/definition acceptance
only; no GNN was constructed. Native graphs/CUDA/capacity/physics/full training
and full heldout quality remain unaccepted.

Accepted server definitions: `runs/molecular-definition-control-1682/definitions/`,
SHA `a4226e6fa9460093e3232af39e8a75e5f5651aacfa7e510386eeff4f64045fd3`.
The canonical manifest SHA used in its configs is
`e7ee905372977d76c430a581f4fc9e2f33bfe44a60adb22eae00acb2d78adc69`;
the original split-file SHA remains the separately audited d1072a6c...b469e58a.
Proof: ignored `results/paper-molecular-definitions-20261106/1682-124742/`.

## Full native graph and training-statistics preparation

`contracts.py` selects the complete four original-model pairs or the single
registered directory-plugin group. It verifies accepted definition bytes and
reconstructs all nine recipes. Changing plugin source requires a fresh accepted
definition version; an old source hash is refused before graph construction.
The original1682 data-only proof remains historical and is never rewritten.

`graphs.py` constructs all100000 source inputs and separately records the900
source-ordered training inputs. Official input functions remain unchanged.
Their already-built containers are counted with the existing native graph
counter. The plugin's unlearned graph builder is called directly; global hooks
still forbid its GNN and every model submodule forward. Parameter/buffer hashes
and eval modes must remain exact. Source/split/audit bytes are checked again
after the complete scan. Failed row prefixes remain evidence and no probe is
accepted after a failure.

CGCNN padded computation slots and valid directed messages have separate counts.
The plugin graph excludes self edges; its GNN's internal per-node self updates
are recorded separately. No periodic shift is permitted. Probe selection reuses
the existing full-training aggregation with two extrema per metric,32 ordinary
records,2 warmups and100 measured batches. Selection is not a capacity result.
For MACE/NequIP, the existing native-statistics implementation scans only900
training structures and attaches the same source/manifest/training fingerprints;
pretrained configs and plugin configs do not acquire scratch statistics.

```bash
PYTHONPATH=src python scripts/scan_molecular_graphs.py \
  --model cgcnn --device cpu --output runs/molecular-graphs-NEW
```

Use the model's original environment and a CPU or GPU Slurm allocation. Output
includes complete source/training JSONL graph counts and lossless deterministic
gzip copies, `probe.json`, resolved ordinary configs and `report.json`.
CPU graphs/statistics are preparatory evidence. The required final input graph
validation must run on actual CUDA; even CUDA graph construction does not prove
100batch/mixed-extreme training capacity, finite differences, mixed parameter
gradients, full fitting or heldout quality. `checked_graph_metadata` checks only
this explicit scope; file/Slurm/counter provenance must also be verified.

The KNN+GCN example now explicitly declares its existing live-geometry position,
strain and mixed derivatives. This changes capability/source metadata, without
adding a layer or changing its forward. Original1e19447 constructor RNG/state
and direct-feature equivalence, actual forcefield finite differences/geometry,
force-only parameter updates and standard checkpoint reload must be checked in
Slurm before runtime acceptance. A new nine-config version is required before
the graph selector can use that changed source; the old1682 version is not
relabeled as model validation.

The updated plugin passed eight actual CPU numerical cases in Slurm1692,
including float32/64 original constructor/state/RNG/features, the unchanged
finite-difference/geometry/mixed-gradient policy, force-only diagnostic updates
and standard checkpoint reload. Slurm1693 retained its successful terminal.
The default graph contract now binds the independently accepted new definitions
in `runs/molecular-definition-control-1692/definitions`, SHA256
`68255484022ac5aaf3ad69ffb65eee35c5ff3dcdc8dd5001f2380b14b888ca79`.
The full100000 source and nine definitions were rechecked; original1682 remains
data-only historical evidence. Actual CUDA, full native graphs and capacity
remain separate required gates.
