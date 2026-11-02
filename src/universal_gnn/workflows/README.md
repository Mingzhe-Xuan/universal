# Workflows

`UniversalCalculator(model)` exposes energy/free_energy (eV), forces (eV/angstrom),
and tensile-positive ASE stress (eV/angstrom^3; converted from model GPa).
`relax(model, structure)` runs fixed-cell FIRE and returns atoms plus convergence/step report.
`molecular_dynamics(model, structure)` runs seeded velocity-Verlet and returns snapshots/energy drift.
These accept a reloaded `ForceFieldModel`; neither performs DFT.

`normal_modes(model, structure)` differentiates forces at Gamma in the supplied periodic cell.
It returns signed frequencies in cm^-1, mass-weighted orthonormal eigenvectors, masses and Hessian.
No acoustic sum-rule or crystal symmetry projection is applied. Unstable modes remain signed;
`broaden` excludes frequencies <= 1 cm^-1 and reports must retain the excluded count.
This Gamma preset does not approximate a converged Brillouin-zone integral.

`mode_responses` contracts Born charges with mass-normalized modes (IR).
`dielectric_raman` differentiates the electronic dielectric predictor along each mode;
its relative powder activity uses the symmetric response in the Placzek average, without
constraining the model output. `neutron_weights` uses natural-abundance total scattering
cross sections from periodictable (barn/amu), and fails on absent cross sections.
`kramers_kronig` uses finite-window principal-value quadrature with analytic pole subtraction.
It assumes zero missing spectral weight; interval endpoints are unreliable.

`frozen_phonon_stem(frames)` uses abTEM multislice with a convergent probe and annular detector.
The short preset uses correlated MLFF-MD snapshots, finite clusters in a common orthogonal
vacuum box, adaptive potential grid and a small scan. It preserves Cartesian geometry;
it is not a converged thermal ensemble or a periodic bulk/slab microscope benchmark.
Install `.[simulation]` in a compatible environment; MACE and NequIP require separate e3nn versions.

Run `python scripts/run_workflows.py --model cgcnn` against three task checkpoints from
`runs/dfpt-tasks`. On Guqq2 submit `sbatch --array=0-5 scripts/workflows.slurm`.
Each report identifies checkpoint directory, source commit/Slurm, ten real structures,
convergence, imaginary modes, all spectra and saved STEM images. Presence of a property
predictor alone is not evidence that a workflow has completed.
