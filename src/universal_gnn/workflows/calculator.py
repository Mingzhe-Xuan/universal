"""ASE bridge: the model contract uses eV, angstrom and tensile-positive GPa."""

import numpy as np
import torch
from ase.calculators.calculator import Calculator, all_changes

from universal_gnn.contracts import Structure, StructureBatch


def structure_from_atoms(atoms, *, identifier="ase", dtype=torch.float64):
    atoms = atoms.copy()
    if abs(atoms.cell.volume) < 1e-9:
        atoms.center(vacuum=6.)
    return Structure(torch.tensor(atoms.numbers, dtype=torch.long),
                     torch.tensor(atoms.positions, dtype=dtype),
                     torch.tensor(atoms.cell.array, dtype=dtype),
                     torch.tensor(atoms.pbc, dtype=torch.bool), identifier)


def atoms_from_structure(structure):
    from ase import Atoms

    return Atoms(numbers=structure.numbers.detach().cpu().numpy(),
                 positions=structure.positions.detach().cpu().numpy(),
                 cell=structure.cell.detach().cpu().numpy(),
                 pbc=structure.pbc.detach().cpu().numpy())


class UniversalCalculator(Calculator):
    implemented_properties = ["energy", "free_energy", "forces", "stress"]

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model.eval()

    def calculate(self, atoms=None, properties=None, system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        parameter = next(self.model.parameters())
        structure = structure_from_atoms(self.atoms, dtype=parameter.dtype)
        batch = StructureBatch.from_structures([structure]).to(parameter.device, parameter.dtype)
        prediction = self.model(batch, create_graph=False)
        stress = prediction["stress"][0].detach().cpu().numpy() / 160.21766208
        self.results = {"energy": float(prediction["total_energy"].detach().reshape(-1)[0]),
                        "forces": prediction["forces"].detach().cpu().numpy(),
                        "stress": np.array([stress[i, j] for i, j in
                                            [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]])}
        self.results["free_energy"] = self.results["energy"]


def relax(model, structure, *, steps=20, fmax=.05):
    """Fixed-cell FIRE; report convergence even when the step budget is exhausted."""
    from ase.optimize import FIRE

    if steps < 0 or fmax <= 0:
        raise ValueError("Need nonnegative steps and positive fmax")
    atoms = atoms_from_structure(structure)
    atoms.calc = UniversalCalculator(model)
    optimizer = FIRE(atoms, logfile=None, maxstep=.05)
    converged = optimizer.run(fmax=fmax, steps=steps)
    return atoms, {"converged": bool(converged), "steps": optimizer.nsteps,
                   "energy_eV": atoms.get_potential_energy(),
                   "max_force_eV_A": float(np.linalg.norm(atoms.get_forces(), axis=1).max()),
                   "fixed_cell": True}


def molecular_dynamics(model, structure, *, steps=10, timestep_fs=.25,
                       temperature_K=100., seed=123):
    from ase import units
    from ase.md.verlet import VelocityVerlet
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution

    if steps < 1 or timestep_fs <= 0 or temperature_K < 0:
        raise ValueError("Invalid MD budget, timestep or temperature")
    atoms = atoms_from_structure(structure)
    atoms.calc = UniversalCalculator(model)
    MaxwellBoltzmannDistribution(atoms, temperature_K=temperature_K,
                                rng=np.random.default_rng(seed))
    integrator = VelocityVerlet(atoms, timestep_fs * units.fs, logfile=None)
    frames, energy = [atoms.copy()], []
    for _ in range(steps):
        integrator.run(1)
        energy.append(atoms.get_total_energy())
        frames.append(atoms.copy())
    if not np.isfinite(energy).all() or not all(np.isfinite(a.positions).all() for a in frames):
        raise FloatingPointError("Nonfinite MD trajectory")
    return frames, {"steps": steps, "timestep_fs": timestep_fs, "temperature_K": temperature_K,
                    "seed": seed, "total_energy_eV": energy,
                    "max_energy_change_eV_atom": float(np.max(np.abs(np.array(energy) - energy[0]))
                                                        / len(atoms))}
