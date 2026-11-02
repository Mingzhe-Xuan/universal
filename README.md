# Universal GNN tasks

Output-driven material prediction, response derivatives, force fields and crystal generation.
Initial backbones: MACE, NequIP, Equiformer, ALIGNN, CGCNN and MEGNet.

The implemented toolkit and its ten-structure execution checks cover six backbones. See
[usage](docs/usage.md), [implementation scope](docs/plan/implementation.md),
[architecture](docs/plan/gnn_task_toolkit.md), and [current state](docs/agents/state.md).
The historical architecture-variant matrix of 96 real ten-structure training/reloaded-inference cases and six ten-structure simulation
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

Canonical model names now select original official implementations and registered published weights.
Prepare their cache and dependencies before training; see [official providers](src/universal_gnn/backbones/official/README.md).
All six passed original-checkpoint/native-reference/ten-real-structure fine-tuning and self-contained
reload; [the official acceptance record](docs/agents/official-pretrained.md) separates these results
from the historical architecture-variant matrix.
MACE and NequIP need separate e3nn environments. The old architecture variants require explicit
`implementation: legacy`; historical variant-matrix results do not certify official checkpoints.
See the environment record for the packages and versions actually tested.

Custom GNN/graph extensions and config/dataset/checkpoint formats share one
[versioned standard](docs/standards.md); [KNN + GCN](examples/custom_knn_gcn/README.md) is the executable example.
