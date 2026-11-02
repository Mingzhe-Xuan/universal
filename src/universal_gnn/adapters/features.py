from __future__ import annotations

import torch
import math
from torch import Tensor, nn

from universal_gnn.backbones.invariant import mlp
from universal_gnn.contracts import NativeFeatures
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.data.geometry import gaussian_basis, radius_graph, scatter_sum

o3 = load_o3()


def scalar_features(nodes: Tensor, irreps: str) -> Tensor:
    result = []
    for (multiplicity, irrep), block in zip(o3.Irreps(irreps), o3.Irreps(irreps).slices()):
        values = nodes[:, block].reshape(len(nodes), multiplicity, irrep.dim)
        if irrep.l == 0 and irrep.p == 1:
            result.append(values[..., 0])
        else:
            result.append(values.square().mean(-1))
    return torch.cat(result, dim=-1)


def invariant_width(irreps: str) -> int:
    return sum(multiplicity for multiplicity, _ in o3.Irreps(irreps))


class ScalarAdapter(nn.Module):
    kind = "invariant"

    def __init__(self, irreps_in: str, width: int = 32):
        super().__init__()
        self.irreps_in, self.irreps = irreps_in, f"{width}x0e"
        self.projection = mlp(invariant_width(irreps_in), width)

    def forward(self, native: NativeFeatures) -> NativeFeatures:
        native.validate()
        return NativeFeatures(self.projection(scalar_features(native.nodes, self.irreps_in)),
                              self.irreps, self.kind, native.batch, native.ptr, native.geometry,
                              native.graph_features, {**native.metadata, "route": "invariant_alignn"})


SMALL_RESPONSE_IRREPS = "8x0e + 4x0o + 8x1o + 8x1e + 8x2e + 4x2o + 4x3o + 4x3e + 4x4e"


class EquivariantAdapter(nn.Module):
    kind = "equivariant"

    def __init__(self, irreps_in: str, irreps_out: str = SMALL_RESPONSE_IRREPS,
                 cutoff: float = 4.0, channels: int = 8, basis_version: int = 2):
        super().__init__()
        if basis_version not in {1, 2}:
            raise ValueError("Geometry basis_version must be 1 or 2")
        self.basis_version = basis_version
        self.irreps_in, self.irreps, self.cutoff, self.channels = irreps_in, irreps_out, cutoff, channels
        self.native_projection = o3.Linear(irreps_in, irreps_out)
        self.weights = mlp(2 * invariant_width(irreps_in) + 16, 5 * channels)
        self.axial_to_quadrupole = o3.ElementwiseTensorProduct("1e", "1o", ["2o"])
        self.vector_to_octupole = o3.ElementwiseTensorProduct("1o", "3o", ["3e"])
        if basis_version == 2:
            self.quadrupoles_to_axial = o3.ElementwiseTensorProduct("2e", "2e", ["1e"])
            self.quadrupoles_to_octupole = o3.ElementwiseTensorProduct("2e", "2e", ["3e"])
            self.quadrupole_octupole_to_odd = o3.ElementwiseTensorProduct("2e", "3o", ["2o"])
            self.quadrupole_odd_to_scalar = o3.ElementwiseTensorProduct("2e", "2o", ["0o"])
        self.geometry_irreps = " + ".join(f"{channels}x{ir}" for ir in
                                         ["0e", "1o", "2e", "3o", "4e", "1e", "0o", "2o", "3e"])
        self.geometry_projection = o3.Linear(self.geometry_irreps, irreps_out)

    def forward(self, native: NativeFeatures) -> NativeFeatures:
        native.validate()
        batch = native.geometry
        graph = radius_graph(batch, self.cutoff)
        scalars = scalar_features(native.nodes, self.irreps_in)
        radial = gaussian_basis(graph.distances, 16, self.cutoff)
        weights = self.weights(torch.cat([scalars[graph.src], scalars[graph.dst], radial], dim=-1))
        weights = weights.reshape(len(graph.src), 5, self.channels)
        moments = []
        for ell in range(5):
            harmonics = o3.spherical_harmonics(ell, graph.vectors, normalize=True,
                                              normalization="component")
            values = weights[:, ell, :, None] * harmonics[:, None, :] * graph.weights[:, None, None]
            moments.append(scatter_sum(values, graph.dst, len(batch.numbers)))
        vector_a = moments[1]
        vector_b = torch.roll(moments[1], shifts=1, dims=1)
        vector_c = torch.roll(moments[1], shifts=2, dims=1)
        axial = torch.cross(vector_a, vector_b, dim=-1)
        if self.basis_version == 2:
            # Nonpolar sites can allow axial/odd tensor modes although every polar moment is zero.
            axial = (axial + self.quadrupoles_to_axial(
                moments[2], torch.roll(moments[2], shifts=1, dims=1))) / math.sqrt(2)
        odd_scalar = (axial * vector_c).sum(-1, keepdim=True)
        odd_quadrupole = self.axial_to_quadrupole(axial, vector_c)
        even_octupole = self.vector_to_octupole(vector_b, moments[3])
        if self.basis_version == 2:
            odd_quadrupole = (odd_quadrupole + self.quadrupole_octupole_to_odd(
                moments[2], torch.roll(moments[3], shifts=1, dims=1))) / math.sqrt(2)
            even_octupole = (even_octupole + self.quadrupoles_to_octupole(
                moments[2], torch.roll(moments[2], shifts=2, dims=1))) / math.sqrt(2)
            odd_scalar = (odd_scalar + self.quadrupole_odd_to_scalar(
                torch.roll(moments[2], shifts=1, dims=1), odd_quadrupole)) / math.sqrt(2)
        blocks = moments + [axial, odd_scalar, odd_quadrupole, even_octupole]
        geometric = torch.cat([block.flatten(1) for block in blocks], dim=-1)
        nodes = self.native_projection(native.nodes) + self.geometry_projection(geometric)
        return NativeFeatures(nodes, self.irreps, self.kind, native.batch, native.ptr,
                              batch, native.graph_features, {**native.metadata, "route": "common_equivariant",
                                                            "geometry_basis_version": self.basis_version})
