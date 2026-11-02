# Task configurations

Run on the cluster through Slurm, using `ugnn train configs/generation.json --output runs/gen`.
The example requires ten real periodic structures at `data/acceptance/generation-10.json`; obtain and record
their public source before running. No example labels or synthetic structures are substituted.
Choose `mace`, `nequip`, `equiformer`, `alignn`, `cgcnn`, or `megnet`. Use the separate MACE
environment for MACE; model architecture and dependency versions are recorded in output reports.

Generation is fixed-composition denoising; the source structures need no property labels.
The runner overfits one fixed corruption for execution acceptance and samples fresh geometry.
Property training uses `task.kind=supervised` and a registered `task.property`; bind raw dataset
fields in `dataset.bindings`. Force-field training requires total energies in eV, forces in
eV/angstrom, and tensile-positive stress in GPa. Unit/sign conversion belongs in explicit bindings.

Available examples: `formation_energy.json`, `forcefield.json`, `born_charge.json`,
`raman.json` and `generation.json`. Change `backbone.name` and the dataset path/bindings.
The real execution cohorts live on the server under `data/acceptance`; raw-source hashes,
IDs and preprocessing are recorded in each cohort and its manifest. Downloaded data is ignored
by Git. `scripts/run_matrix.py prepare --tasks TASKS --output runs/NAME` generates configurations
for every built-in model from a prepared manifest; `--models cgcnn,mace` selects a subset.

For a new property, set `task.spec` with explicit scope/shape/unit/kind/construction.
For a dataset directory, use `dataset.path=plugin:/path` and implement `build_dataset` in
that directory's `plugin.py`. See the data and properties module READMEs for contracts.

The flag CLI also accepts YAML: `bandgap.yaml` is a runnable ALIGNN/OptB88vdW gap example.
`formation_energy.yaml` is the template for docs/plan/usage.md; supply `--model` and `--dataset`.
CLI fields override file settings. `--resume` inherits omitted settings from the checkpoint;
set a larger total `--epochs` when continuing a complete run. See docs/plan/usage.md for paths/logs.

`custom_knn_gcn.yaml` follows schema_version 1 and selects independent graph/GNN directory factories.
It uses ten real ASE G2-1 molecules prepared with `scripts/prepare_molecular_data.py` on Slurm.
See docs/standards.md for the single config/dataset/checkpoint/interface specification.
