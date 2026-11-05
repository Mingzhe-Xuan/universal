# Frozen-backbone response ablations

This module defines eight separate full-data comparisons: dielectric/forcefield
x CGCNN/ALIGNN/MACE/NequIP x pretrained seed123. They complement the original
finetuned and scratch primary cases. Native-head inference and the separate
rank3/4 experiments remain distinct. Definitions do not submit or complete jobs.

`definitions.py` checks the exact original947 matrix and each original primary
pretrained recipe. The sole training-config change is
`optimization.train_backbone: false`. Dataset/splits/raw bindings, official
architecture/weights/cutoff, reset task head, feature processing, full data,
float32, initial common batch4,300epoch/patience30 and optimizer settings remain.
Cases live under `runs/arxiv-v1/frozen-cases/`, outside primary/higher-rank paths.
No dataset or historical primary definition is rewritten.

`inspect_frozen_inputs` streams both complete original sources (4999 dielectric
and1566 MLearn records), verifies registry/source/audit/split hashes and ordered
IDs, then checks every original finite raw label:9 dielectric components, one
total energy and3 components per atom for forces. It preserves zero labels,
large structures and original units. No fitting, downsampling or label/target
transformation occurs. This audit must run through CPU Slurm.

```bash
python scripts/prepare_frozen_experiment_definitions.py --output NEW_DIRECTORY
```

The CLI writes `definitions.json` and8 ordinary training configs under `configs/`.
It requires a fresh directory and a clean immutable source checkout. The default
primary matrix is `runs/arxiv-v1/definition-947/matrix.json`.

Freezing parameters does not mean `no_grad` around the backbone: forces and
auxiliary response derivatives still require input autograd. The existing
runtime sets frozen modules to eval, excludes their parameters from the optimizer
and uses `FrozenStateGuard` to reject any parameter/persistent-buffer mutation.
Each new frozen case must independently prove zero backbone parameter gradients,
nonzero readout mixed gradients and live geometry/auxiliary derivatives, with
original finite-difference and geometry/batch tolerances. Exact frozen state and
all submodule eval modes must survive optimizer updates and checkpoint reload.

Original unfrozen capacity/physics or completed primary training is not frozen
training evidence. Official frozen full graph/capacity/physical preparation,
selection/complete test and separate independent postprocessing still require
their own explicit gates. Full-FT executors that require positive backbone
gradients must not be bypassed to accept a frozen case. Current exported cases
are only `defined_not_preflighted`, with formal training count0.


Definition source0c9120c passed actualCPU1288/1289:159 main tests/981 JUnit
counts without failure/error/skip,15 executed Git blobs, all6565 ordered source
records/393783 finite raw labels and8 exact exports. Six live frozen small-model
reports preserve initial predictions, backbone parameters/buffers/eval modes
and optimizer exclusion while readout updates and input derivatives remain live;
five existing freeze/buffer/checkpoint-resume controls pass.269 all-zero force
labels are retained. Source/eight original primary full gate regressions passed.
Proof: ignored `results/paper-frozen-definition-20261105/1288/`.
Server definitions: `runs/frozen-definition-control-1288/definitions/`, SHA
`e6104992bc86dfbbc0bdc67b9d20105f79dcb5ba95dc3fabbdac7ef708c4b8f0`.
Official frozen CUDA capacity/physics and full execution acceptance remain pending;
none of these checks submits or completes an official frozen training.

## Official frozen preparation

`contracts.py` selects only the eight byte-bound accepted definitions. It requires
the complete original finetune reference gate, which also verifies its original
scratch pair, artifacts, full source/split and all clean native/auxiliary graph
rows. `readiness.py` reuses those exact source-bound graph extrema; freezing
parameters changes neither graph construction nor the dataset. Each frozen case
still performs its own actual CUDA training capacity and physical checks.

`worker.py` delegates the same disposable training loop and optimizer arithmetic
to the unchanged `probe_worker.py`. A scoped optimizer wrapper checks all frozen
parameters and persistent buffers exactly before/after each real step, eval
modes, optimizer ownership and missing backbone gradients. Readout parameter
hashes and finite positive gradients prove its actual updates. It does not
detach geometry, change seeds, weights, losses, clipping or optimizer steps.
The source hashes of both worker layers are retained. Full worst homogeneous
batches plus at least100 measured batches remain mandatory.

The accepted frozen batch must match the original reference's common batch
(currently4). Only typed CUDA OOM may reduce an exploratory capacity attempt.
An exploratory smaller batch is retained but does not qualify the advertised
one-flag ablation until a matching reference protocol is established; no existing
scientific result is silently replaced. Unknown errors and timeouts stop.

On the two worst original training structures, the actual frozen model must
satisfy the original force/stress or rank2 response finite-difference, geometry
and batch checks with unchanged tolerances. Its backbone mixed gradients must
be zero and readout mixed gradients positive, and its full backbone state must
match both before/after physics and the independent capacity worker. The existing
primary physics checker keeps positive-backbone gradients as its default; only
the explicit frozen path uses the zero-backbone policy. CPU evidence cannot
qualify CUDA readiness.

From the clean pinned checkout, in a Slurm GPU allocation and original provider
environment:

```bash
python scripts/prepare_frozen_case.py prepare \
  --case frozen--seed-123--forcefield--cgcnn \
  --reference-preparation runs/arxiv-v1/full-ff-preparation-995-cgcnn \
  --output runs/arxiv-v1/new-frozen-cgcnn-forcefield-preparation
```

Then independently replay from a CPU Slurm allocation using that provider:

```bash
python scripts/prepare_frozen_case.py check \
  --case frozen--seed-123--forcefield--cgcnn \
  --preparation runs/arxiv-v1/new-frozen-cgcnn-forcefield-preparation \
  --output runs/new-frozen-cgcnn-gate.json
```

Both outputs must be new. Preparation records its executed commit even on
failure. Readiness is neither full training nor scientific completion: each case
still needs full head training, validation-best heldout/physical/all-source
inference and independent no-model acceptance. This new preparation code has
not yet qualified any official frozen case until actual Slurm evidence passes.
