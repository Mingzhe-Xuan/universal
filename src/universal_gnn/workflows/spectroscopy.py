"""Differentiable Gamma phonons and derived spectra; no crystal symmetry projection."""

from dataclasses import dataclass

import numpy as np
import torch
from ase import units
from ase.data import atomic_masses

from universal_gnn.contracts import StructureBatch


# sqrt(eV / (angstrom^2 amu)) -> angular frequency -> spectroscopic cm^-1.
FREQUENCY_CM = (units._e / (units._amu * 1e-20)) ** .5 / (2 * np.pi * units._c * 100)


@dataclass
class NormalModes:
    frequencies_cm: torch.Tensor
    eigenvectors: torch.Tensor  # [mode, atom, Cartesian], mass-weighted orthonormal
    masses: torch.Tensor
    hessian: torch.Tensor


def normal_modes(model, structure):
    parameter = next(model.parameters())
    batch = StructureBatch.from_structures([structure]).to(parameter.device, parameter.dtype)
    positions = batch.positions.detach().clone().requires_grad_(True)
    batch = batch.with_geometry(positions, batch.cell)
    forces = model(batch, create_graph=True)["forces"]
    rows = []
    for component in forces.reshape(-1):
        gradient = (torch.autograd.grad(component, positions, retain_graph=True, allow_unused=True)[0]
                    if component.requires_grad else None)
        rows.append(torch.zeros_like(positions).reshape(-1) if gradient is None else -gradient.reshape(-1))
    hessian = torch.stack(rows)
    # The energy Hessian is mathematically symmetric; averaging removes numerical roundoff only.
    hessian = .5 * (hessian + hessian.T)
    masses = positions.new_tensor(atomic_masses[batch.numbers.detach().cpu().numpy()])
    roots = masses.sqrt().repeat_interleave(3)
    eigenvalues, vectors = torch.linalg.eigh(hessian / roots[:, None] / roots[None, :])
    frequencies = eigenvalues.sign() * eigenvalues.abs().sqrt() * FREQUENCY_CM
    return NormalModes(frequencies.detach(), vectors.T.reshape(-1, len(masses), 3).detach(),
                       masses, hessian.detach())


def broaden(frequencies, intensities, grid, *, width=5., cutoff=1.):
    """Lorentzian HWHM in grid units. Imaginary/near-zero modes are explicitly excluded."""
    if width <= 0 or grid.ndim != 1 or not bool((grid[1:] > grid[:-1]).all()):
        raise ValueError("Need positive width and strictly increasing grid")
    keep = frequencies > cutoff
    values = width / np.pi / ((grid[:, None] - frequencies[keep]) ** 2 + width ** 2)
    return values @ intensities[keep]


def raman_activity(tensors):
    """Orientational average for the symmetric polarizability response (Placzek)."""
    tensor = .5 * (tensors + tensors.transpose(-1, -2))
    diagonal = tensor.diagonal(dim1=-2, dim2=-1)
    mean = diagonal.mean(-1)
    gamma = .5 * ((diagonal[..., 0] - diagonal[..., 1]) ** 2
                  + (diagonal[..., 1] - diagonal[..., 2]) ** 2
                  + (diagonal[..., 2] - diagonal[..., 0]) ** 2
                  + 6 * (tensor[..., 0, 1] ** 2 + tensor[..., 0, 2] ** 2
                         + tensor[..., 1, 2] ** 2))
    return 45 * mean.square() + 7 * gamma


def mode_responses(modes, born):
    displacements = modes.eigenvectors / modes.masses.sqrt()[None, :, None]
    dipole = torch.einsum("aij,maj->mi", born, displacements)
    return dipole.square().sum(-1)


def dielectric_raman(model, structure, modes):
    parameter = next(model.parameters())
    batch = StructureBatch.from_structures([structure]).to(parameter.device, parameter.dtype)
    positions = batch.positions.detach().clone().requires_grad_(True)
    value = model(batch.with_geometry(positions, batch.cell), create_graph=True).reshape(3, 3)
    jacobian = []
    for component in value.reshape(-1):
        grad = torch.autograd.grad(component, positions, retain_graph=True, allow_unused=True)[0]
        jacobian.append(torch.zeros_like(positions) if grad is None else grad)
    jacobian = torch.stack(jacobian).reshape(3, 3, -1, 3)
    displacement = modes.eigenvectors.to(positions) / modes.masses.to(positions).sqrt()[None, :, None]
    # Paper Eq. 10 uses dielectric derivatives, with relative Raman activities.
    tensors = torch.einsum("ijan,man->mij", jacobian, displacement)
    return raman_activity(tensors).detach(), tensors.detach()


def neutron_weights(modes, numbers):
    import periodictable

    cross_sections = []
    for number in numbers.detach().cpu().tolist():
        value = periodictable.elements[number].neutron.total
        if value is None or not np.isfinite(value):
            raise ValueError(f"No natural-abundance total scattering cross section for Z={number}")
        cross_sections.append(value)
    weights = modes.masses.new_tensor(cross_sections) / modes.masses
    return (modes.eigenvectors.square().sum(-1) * weights[None, :]).sum(-1)


def kramers_kronig(grid, epsilon2):
    """Finite-window principal-value quadrature, epsilon1(infinity)=1.

    The analytic subtraction removes the pole instead of dropping a singular grid point.
    All missing spectral weight outside the supplied interval is assumed zero.
    """
    if grid.ndim != 1 or len(grid) < 3 or grid[0] <= 0 or not bool((grid[1:] > grid[:-1]).all()):
        raise ValueError("KK requires an increasing, strictly positive frequency grid")
    if epsilon2.shape[-1] != len(grid):
        raise ValueError("Spectrum/grid length mismatch")
    x, w = grid[:, None], grid[None, :]
    numerator = x * epsilon2[..., :, None] - w * epsilon2[..., None, :]
    denominator = x.square() - w.square()
    diagonal = torch.eye(len(grid), dtype=torch.bool, device=grid.device)
    smooth = numerator / torch.where(diagonal, torch.ones_like(denominator), denominator)
    derivative = torch.gradient(grid * epsilon2, spacing=(grid,), dim=-1)[0] / (2 * grid)
    smooth = torch.where(diagonal, derivative[..., None, :], smooth)
    # Endpoints use the inward nextafter limit; endpoint estimates should not be used as data.
    inside = grid.clone()
    inside[0] = torch.nextafter(grid[0], grid[-1])
    inside[-1] = torch.nextafter(grid[-1], grid[0])
    integral_pole = torch.log(((grid[-1] - inside) * (grid[0] + inside)
                              / ((grid[-1] + inside) * (grid[0] - inside))).abs()) / (2 * inside)
    return 1 + 2 / np.pi * (torch.trapezoid(smooth, grid, dim=-2)
                            + grid * epsilon2 * integral_pole)
