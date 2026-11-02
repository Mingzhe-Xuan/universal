# Task configurations

Run on the cluster through Slurm, using `ugnn train configs/generation.json --output runs/gen`.
The example requires ten real periodic structures at `data/generation-10.json`; obtain and record
their public source before running. No example labels or synthetic structures are substituted.
Choose `mace`, `nequip`, `equiformer`, `alignn`, `cgcnn`, or `megnet`. Use the separate MACE
environment for MACE; model architecture and dependency versions are recorded in output reports.

Generation is fixed-composition denoising; the source structures need no property labels.
The runner overfits one fixed corruption for execution acceptance and samples fresh geometry.
Property training uses `task.kind=supervised` and a registered `task.property`; bind raw dataset
fields in `dataset.bindings`. Force-field training requires total energies in eV, forces in
eV/angstrom, and tensile-positive stress in GPa. Unit/sign conversion belongs in explicit bindings.
