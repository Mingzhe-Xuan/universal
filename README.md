# Universal GNN tasks

Output-driven material prediction, response derivatives, force fields and crystal generation.
Initial backbones: MACE, NequIP, Equiformer, ALIGNN, CGCNN and MEGNet.

The implemented toolkit and its ten-structure execution checks cover six backbones. See
[usage](docs/usage.md), [implementation scope](docs/plan/implementation.md),
[architecture](docs/plan/gnn_task_toolkit.md), and [current state](docs/agents/state.md).
All 96 real ten-structure training/reloaded-inference cases and six ten-structure simulation
workflows passed on Slurm; [the evidence record](docs/agents/acceptance.md) records versions, data
and limits. This is execution validation, not reproduction of paper benchmark accuracy.

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

Custom GNN/graph extensions and config/dataset/checkpoint formats share one
[versioned standard](docs/standards.md); [KNN + GCN](examples/custom_knn_gcn/README.md) is the executable example.
