"""Composition-conditioned periodic denoising with a positive-volume cell chart."""

import math
from dataclasses import replace

import torch
from torch import nn

from universal_gnn.adapters.features import invariant_width, scalar_features
from universal_gnn.backbones.invariant import mlp
from universal_gnn.contracts import NativeFeatures, StructureBatch
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.data.geometry import gaussian_basis, radius_graph, scatter_mean, scatter_sum

CONTEXT_DIM = 22


def encode_cell(cell):
    """Six rotation-invariant log-Cholesky coordinates, with row lattice vectors."""
    lower = torch.linalg.cholesky(cell @ cell.transpose(-1, -2))
    diagonal = lower.diagonal(dim1=-2, dim2=-1)
    shear = torch.stack([lower[:, 1, 0] / diagonal[:, 0],
                         lower[:, 2, 0] / diagonal[:, 0],
                         lower[:, 2, 1] / diagonal[:, 1]], dim=-1)
    return torch.cat([diagonal.log(), shear], dim=-1)


def decode_cell(state):
    diagonal = state[:, :3].exp()
    zero = torch.zeros_like(diagonal[:, 0])
    row0 = torch.stack([diagonal[:, 0], zero, zero], dim=-1)
    row1 = torch.stack([state[:, 3] * diagonal[:, 0], diagonal[:, 1], zero], dim=-1)
    row2 = torch.stack([state[:, 4] * diagonal[:, 0], state[:, 5] * diagonal[:, 1],
                        diagonal[:, 2]], dim=-1)
    return torch.stack([row0, row1, row2], dim=1)


def fractional_coordinates(batch):
    return torch.einsum("ni,nij->nj", batch.positions, torch.linalg.inv(batch.cell)[batch.batch])


def periodic_score(delta, sigma, images=3):
    """sigma * grad_x log wrapped_normal(x | x0, sigma), per fractional axis."""
    offsets = torch.arange(-images, images + 1, device=delta.device, dtype=delta.dtype)
    differences = delta[..., None] + offsets
    scaled = differences / sigma[..., None]
    weights = torch.softmax(-.5 * scaled.square(), dim=-1)
    return -(weights * scaled).sum(-1)


def context_embedding(time, cell_state):
    frequencies = torch.exp(torch.linspace(0, math.log(1000), 8, device=time.device,
                                          dtype=time.dtype))
    phase = time[:, None] * frequencies
    return torch.cat([phase.sin(), phase.cos(), cell_state], dim=-1)


def noise_scale(time, minimum=.01, maximum=.3):
    return minimum * (maximum / minimum) ** time


def batch_from_state(reference, fractional, cell_state):
    cell = decode_cell(cell_state)
    positions = torch.einsum("ni,nij->nj", fractional.remainder(1), cell[reference.batch])
    return reference.with_geometry(positions, cell)


def corrupt(batch, *, generator=None):
    if not bool(batch.pbc.all()):
        raise ValueError("Periodic generation requires 3D periodic structures")
    time = torch.rand(batch.num_graphs, device=batch.positions.device,
                      dtype=batch.positions.dtype, generator=generator).clamp(.05, 1)
    sigma = noise_scale(time)
    fractional = fractional_coordinates(batch).remainder(1)
    eps = torch.randn(fractional.shape, device=fractional.device, dtype=fractional.dtype,
                       generator=generator)
    noisy_fractional = (fractional + sigma[batch.batch, None] * eps).remainder(1)
    cell_state = encode_cell(batch.cell)
    eps_cell = torch.randn(cell_state.shape, device=cell_state.device, dtype=cell_state.dtype,
                            generator=generator)
    noisy_cell = cell_state + sigma[:, None] * eps_cell
    target = {"fractional_score": periodic_score(noisy_fractional - fractional,
                                                 sigma[batch.batch, None]),
              "cell_score": -eps_cell}
    return batch_from_state(batch, noisy_fractional, noisy_cell), time, target


class DirectionReadout(nn.Module):
    """One interface for native polar vectors and invariant geometry-weighted vectors."""

    def __init__(self, irreps, kind, cutoff):
        super().__init__()
        self.irreps, self.kind, self.cutoff = irreps, kind, cutoff
        if kind == "equivariant":
            o3 = load_o3()
            if not any(irrep.l == 1 and irrep.p == -1 for _, irrep in o3.Irreps(irreps)):
                raise ValueError("Generation needs native polar-vector channels")
            self.projection = o3.Linear(irreps, "1o")
        else:
            self.weights = mlp(2 * invariant_width(irreps) + 16, 1)

    def forward(self, features: NativeFeatures):
        if self.kind == "equivariant":
            return self.projection(features.nodes)
        graph = radius_graph(features.geometry, self.cutoff)
        nodes = scalar_features(features.nodes, self.irreps)
        weights = self.weights(torch.cat([nodes[graph.src], nodes[graph.dst],
                              gaussian_basis(graph.distances, 16, self.cutoff)], dim=-1))
        vectors = graph.vectors / graph.distances.clamp_min(1e-12)[:, None]
        return scatter_sum(weights * vectors * graph.weights[:, None], graph.dst, len(nodes))


class PeriodicDenoiser(nn.Module):
    def __init__(self, backbone):
        super().__init__()
        self.backbone = backbone
        self.coordinate_head = DirectionReadout(backbone.irreps, backbone.kind, backbone.cutoff)
        self.cell_head = mlp(invariant_width(backbone.irreps), 6)

    def forward(self, batch, time):
        state = encode_cell(batch.cell)
        native = self.backbone.encode(batch, context_embedding(time, state))
        cartesian = self.coordinate_head(native)
        # A score is a covector: s_f = s_r L^T for r = f L; displacements use L^-1.
        fractional = torch.einsum("ni,nji->nj", cartesian, batch.cell[batch.batch])
        nodes = scalar_features(native.nodes, native.irreps)
        pooled = scatter_mean(nodes, batch.batch, batch.num_graphs)
        return {"fractional_score": fractional, "cell_score": self.cell_head(pooled)}

    @torch.no_grad()
    def sample(self, reference: StructureBatch, *, steps=12, inner_steps=2, seed=456,
               volume_per_atom=20., min_length=1., max_length=30., max_shear=2.):
        if steps < 2 or inner_steps < 1:
            raise ValueError("Sampling needs at least two noise levels and one inner step")
        generator = torch.Generator(device=reference.positions.device).manual_seed(seed)
        fractional = torch.rand(reference.positions.shape, device=reference.positions.device,
                                 dtype=reference.positions.dtype, generator=generator)
        natoms = reference.ptr[1:] - reference.ptr[:-1]
        length = (natoms * volume_per_atom).pow(1 / 3)
        state = reference.cell.new_zeros((reference.num_graphs, 6))
        state[:, :3] = length[:, None].log()
        schedule = torch.linspace(1, 0, steps, device=state.device, dtype=state.dtype)
        for t in schedule:
            time = t.expand(reference.num_graphs)
            sigma = noise_scale(time)
            step = .1 * sigma.square()
            for _ in range(inner_steps):
                noisy = batch_from_state(reference, fractional, state)
                prediction = self(noisy, time)
                atom_step = step[reference.batch, None]
                eps_f = torch.randn(fractional.shape, device=state.device, dtype=state.dtype,
                                    generator=generator)
                eps_c = torch.randn(state.shape, device=state.device, dtype=state.dtype,
                                    generator=generator)
                fractional = (fractional + atom_step * prediction["fractional_score"] /
                              sigma[reference.batch, None] + (2 * atom_step).sqrt() * eps_f).remainder(1)
                state = state + step[:, None] * prediction["cell_score"] / sigma[:, None] + \
                    (2 * step[:, None]).sqrt() * eps_c
                state[:, :3].clamp_(math.log(min_length), math.log(max_length))
                state[:, 3:].clamp_(-max_shear, max_shear)
        result = batch_from_state(reference, fractional, state)
        if not bool(torch.isfinite(result.positions).all() and torch.isfinite(result.cell).all()):
            raise FloatingPointError("Nonfinite generated structure")
        # Generated samples carry no copied physical labels from the composition templates.
        return replace(result, targets=tuple({} for _ in range(result.num_graphs)))
