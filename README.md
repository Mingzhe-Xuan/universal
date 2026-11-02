# Universal GNN tasks

Output-driven material prediction, response derivatives, force fields and crystal generation.
Initial backbones: MACE, NequIP, Equiformer, ALIGNN, CGCNN and MEGNet.

Implementation and acceptance are in progress. A planned adapter or passing unit test is not a
completed model/task acceptance. See [implementation scope](docs/plan/implementation.md),
[architecture](docs/plan/gnn_task_toolkit.md), and [current state](docs/agents/state.md).
The first 66 real ten-structure training/reloaded-inference cases passed on Slurm;
[the evidence record](docs/agents/acceptance.md) lists the completed subset and remaining work.

```bash
python -m venv .venv
python -m pip install -e '.[dev]'
pytest
```

Training, inference and evaluation on Guqq2 must be submitted through Slurm. Keep downloaded data,
weights and generated reports outside Git. The acceptance protocol uses 10 real structures per
model/task, checks optimization, checkpoint reload and prediction, and measures execution correctness,
not generalization accuracy.

MACE and NequIP require separate environments because of their e3nn constraints. Install
`.[dev,mace]` in the MACE environment and `.[dev,nequip]` in the NequIP environment. The four native
Torch/e3nn architecture variants use the core environment. See each backbone's README for its
implementation boundary and the environment record for the versions actually tested.
