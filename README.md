# Universal GNN tasks

Output-driven material prediction, response derivatives, force fields and crystal generation.
Initial backbones: MACE, NequIP, Equiformer, ALIGNN, CGCNN and MEGNet.

Implementation and acceptance are in progress. A planned adapter or passing unit test is not a
completed model/task acceptance. See [implementation scope](docs/plan/implementation.md),
[architecture](docs/plan/gnn_task_toolkit.md), and [current state](docs/agents/state.md).

```bash
python -m venv .venv
python -m pip install -e '.[dev]'
pytest
```

Training, inference and evaluation on Guqq2 must be submitted through Slurm. Keep downloaded data,
weights and generated reports outside Git. The acceptance protocol uses 10 real structures per
model/task, checks optimization, checkpoint reload and prediction, and measures execution correctness,
not generalization accuracy.
