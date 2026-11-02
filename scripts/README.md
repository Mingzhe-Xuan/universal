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
The base manifest writes 66 cases for six models and eleven tasks; append the DFPT, Raman and
optical cohorts below for the complete 96-case execution matrix. Submit only after
the required environments and dataset files are present:
`sbatch --array=0-65%8 scripts/matrix.slurm` for the base manifest, or `--array=0-95%6`
for the fully prepared manifest. For another output directory set `UGNN_MATRIX` explicitly.
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

`prepare_raman_data.py` derives 200-bin peak-normalized curves from CRD original tensors and
signed frequencies. Require exactly 3N frequency and tensor slots; reject incomplete mode mapping.
`prepare_optical_data.py` resamples published NIST TBmBJ trace-average epsilon2 and records a
finite-window principal-value KK postprocess. Both scripts append ten real structures to the manifest.
Numerical preprocessing and model execution on Guqq2 belong in Slurm.

`workflows.slurm` calls `run_workflows.py` for six backbones using matched forcefield/Born/dielectric
checkpoints. Each model runs ten structures through fixed-cell FIRE, short MD, Gamma modes,
IR/Raman/neutron broadening and real abTEM multislice STEM from MD snapshots.
`collect_evidence.py --matrices ... --workflows runs/workflows` checks actual saved reports,
unique IDs, optimization/checkpoint evidence, and finite nonconstant STEM image arrays.
It refuses missing/failed entries; controller retention is never used to invent historical job states.

`ugnn.slurm` forwards all user CLI arguments unchanged to `python -m universal_gnn.cli` in the
submission directory; create `runs/` before submitting. Set `UGNN_PYTHON` for a different task venv.
`validate_cli.slurm` checks the documented flags on ten real ALIGNN bandgap structures: 15 epochs,
resume to 30, inference, and parameter equality with an uninterrupted 30-epoch run.

`prepare_molecular_data.py` exports ten original ASE G2-1 molecular geometries and published
experimental ionization energies, plus matching local KNN edge records, in canonical dataset v1.
No new DFT or synthetic target is used. `validate_extensions.slurm` trains the custom KNN+GCN
directory example, resumes, predicts, and compares with uninterrupted training and imported graphs.
Use `sbatch scripts/validate_extensions.slurm` on Guqq2; reports/checkpoints remain ignored.

`validate_official.py` is an implementation-stage Slurm acceptance harness. It requires a published
checkpoint, ten labelled real structures and an independent native reference for the provider;
unsupported reference branches fail explicitly. It checks original descriptors/predictions, finite
first/second input derivatives, decreased ten-structure training loss, changes to original backbone
parameters and self-contained reload with deliberately absent external artifact paths. It does not
replace held-out evaluation or declare providers verified before their actual validation JSON exists.

`fetch_official_sources.py` downloads fixed CGCNN/Equiformer/OCP archives into ignored models/,
verifies and packages their original Python package files/licenses into a small offline tar.gz,
and rechecks every member against its source hash. It supports Python3.10. Source bytes are not
patched; unsupported symbolic links inside selected packages fail. Resource download/packing is
separate from the Slurm-only model validation and training scripts.

`diagnose_nequip_parity.py` is a bounded Slurm-only numerical diagnostic using the published NequIP
profile and ten real bandgap structures. It first verifies original/cloned model states exactly,
then records independent calculator and adapter force repeatability with JIT optimization on/off.
The JSON report is diagnostic evidence, not a relaxed acceptance test or a training benchmark.
The historical run_matrix uses explicit legacy variants; validate_official is the separate original
checkpoint/reference/ten-structure acceptance path.
