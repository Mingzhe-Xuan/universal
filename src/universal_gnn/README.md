# Universal GNN runtime

Each backend emits typed unpooled node features. Adapters normalize scalar/irreps layouts, readouts
implement configured outputs and Jacobians, and tasks implement joint energy derivatives. Data
binding preserves geometry and provenance; the engine records optimization and checkpoint reload.
External model dependencies are loaded only when selected, with no silent substitute backend.

Use `python -m universal_gnn.cli train config.json --output runs/name` after installation. Runtime
training/inference is subject to the repository Slurm policy. See sibling module READMEs and the
implementation acceptance matrix before interpreting any result as supported.
