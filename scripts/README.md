# Scripts

This directory contains Slurm, dependency and dataset preparation entry points. Source changes are
made and committed locally, then pulled on Guqq2. Downloaded datasets and generated job outputs
remain ignored. Each remote session is recorded in docs/agents/gpu.md before connection.
# Real small-data matrix

Download the named author archives listed in `prepare_acceptance_data.py` to `data/downloads`.
Run `python scripts/prepare_acceptance_data.py` for bounded small-cohort extraction; use Slurm
for larger processing. It stores original URLs/SHA256/record indexes, refuses duplicate geometries
and missing labels, and explicitly lists data that remain pending.

Prepare configurations with `python scripts/run_matrix.py prepare --output runs/acceptance`.
This writes 66 cases for six models and the eleven currently curated tasks. Submit only after
the required environments and dataset files are present:
`sbatch --array=0-65%8 scripts/matrix.slurm`.
Use `python scripts/run_matrix.py summarize --matrix runs/acceptance/matrix.json` to collect
reports; missing data and failed cases remain visible. MACE automatically selects its isolated
environment. No job treats unexecuted cases as passed. Each report includes its Git/Slurm provenance.

`run_matrix.py verify` replays a saved checkpoint against its original JSON predictions. Submit it
through `verify.slurm`, with the existing matrix path and matching array range. Old tensor bases
are reconstructed from checkpoint format, rather than silently using a new adapter default.

`prepare_dfpt_data.py` appends matched E/F/S, Born, and dielectric cohorts from published raw DFPT
ZIPs and their SHA manifest. Run batch XML parsing on Slurm. Energy supervision uses VASP's
electronic free energy, and stress is explicitly converted from ASE units; original Born components
are retained. Missing/invalid archives produce recorded failures, not fabricated labels.
