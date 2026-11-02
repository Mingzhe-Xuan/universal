import numpy as np
import torch
from torch import nn

from universal_gnn.contracts import Structure
from universal_gnn.workflows.calculator import (UniversalCalculator, atoms_from_structure,
                                               molecular_dynamics, relax)
from universal_gnn.workflows.spectroscopy import (FREQUENCY_CM, broaden, kramers_kronig,
                                                 mode_responses, normal_modes, raman_activity)


class HarmonicPair(nn.Module):
    def __init__(self):
        super().__init__()
        self.k = nn.Parameter(torch.tensor(2., dtype=torch.float64))

    def forward(self, batch, create_graph=False):
        position = batch.positions
        if not position.requires_grad:
            position = position.detach().requires_grad_()
        displacement = position[1] - position[0] - position.new_tensor([1., 0., 0.])
        energy = .5 * self.k * displacement.square().sum()
        force = -torch.autograd.grad(energy, position, create_graph=create_graph)[0]
        return {"total_energy": energy.reshape(1, 1), "forces": force,
                "stress": position.new_ones(1, 3, 3) * 160.21766208}


def pair():
    return Structure(torch.tensor([1, 1]), torch.tensor([[0., 0., 0.], [1.1, .1, 0.]],
                                                       dtype=torch.float64),
                     torch.eye(3, dtype=torch.float64) * 8, torch.tensor([False] * 3), "pair")


def test_calculator_units_cache_relax_and_md():
    model, structure = HarmonicPair(), pair()
    atoms = atoms_from_structure(structure)
    atoms.calc = UniversalCalculator(model)
    assert np.isclose(atoms.get_potential_energy(), .02)
    np.testing.assert_allclose(atoms.get_forces()[1], [-.2, -.2, 0.], atol=1e-12)
    np.testing.assert_allclose(atoms.get_stress(), np.ones(6))
    atoms.positions[1, 0] += .1
    assert np.isclose(atoms.get_potential_energy(), .05)
    _, result = relax(model, structure, steps=100, fmax=.01)
    assert result["converged"] and result["max_force_eV_A"] < .01
    frames, md = molecular_dynamics(model, structure, steps=5, timestep_fs=.1)
    assert len(frames) == 6 and md["max_energy_change_eV_atom"] < 1e-4


def test_mass_weighted_hessian_and_born_modes():
    modes = normal_modes(HarmonicPair(), pair())
    torch.testing.assert_close(modes.frequencies_cm[:3], torch.zeros(3, dtype=torch.float64), atol=1e-4, rtol=0)
    expected = (4 / modes.masses[0]).sqrt() * FREQUENCY_CM
    torch.testing.assert_close(modes.frequencies_cm[3:], expected.expand(3))
    # Equal charges have no optical activity for the antisymmetric relative modes.
    activity = mode_responses(modes, torch.eye(3, dtype=torch.float64).expand(2, -1, -1))
    torch.testing.assert_close(activity[3:], torch.zeros(3, dtype=torch.float64), atol=1e-12, rtol=0)
    activity = mode_responses(modes, torch.stack([torch.eye(3), -torch.eye(3)]).double())
    torch.testing.assert_close(activity[3:], (2 / modes.masses[0]).expand(3))


def test_raman_rotation_imaginary_exclusion_and_kk_principal_value():
    tensor = torch.tensor([[[1., 2., 0.], [2., 4., 1.], [0., 1., 3.]]], dtype=torch.float64)
    rotation, _ = torch.linalg.qr(torch.randn(3, 3, dtype=torch.float64))
    torch.testing.assert_close(raman_activity(tensor), raman_activity(rotation @ tensor @ rotation.T))
    grid = torch.linspace(1, 20, 200, dtype=torch.float64)
    freq, weights = torch.tensor([-8., 0., 10.]), torch.tensor([100., 100., 2.])
    torch.testing.assert_close(broaden(freq.double(), weights.double(), grid),
                               broaden(freq[2:].double(), weights[2:].double(), grid))
    epsilon2 = 3 / grid
    expected = 1 + 3 / (np.pi * grid) * torch.log(
        (((grid[-1] - grid) * (grid[0] + grid)) / ((grid[-1] + grid) * (grid[0] - grid))).abs())
    torch.testing.assert_close(kramers_kronig(grid, epsilon2)[1:-1], expected[1:-1])
