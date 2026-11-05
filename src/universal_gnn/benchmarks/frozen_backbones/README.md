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
