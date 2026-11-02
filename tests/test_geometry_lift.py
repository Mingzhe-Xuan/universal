import pytest
import torch

from universal_gnn.adapters.features import EquivariantAdapter
from universal_gnn.contracts import NativeFeatures, Structure, StructureBatch
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.properties import property_spec
from universal_gnn.readouts import ResponseReadout


PROFILE = "2x0e + 2x0o + 2x1o + 2x1e + 2x2e + 2x2o + 2x3o + 2x3e + 2x4e"


def features_for(neighbors):
    positions = torch.cat([torch.zeros(1, 3, dtype=torch.float64), neighbors])
    structure = Structure(torch.ones(len(positions), dtype=torch.long), positions,
                          torch.eye(3, dtype=torch.float64) * 12,
                          torch.zeros(3, dtype=torch.bool), "point-group-capacity")
    batch = StructureBatch.from_structures([structure])
    return NativeFeatures(torch.ones(len(positions), 2, dtype=torch.float64), "2x0e", "invariant",
                          batch.batch, batch.ptr, batch)


def central_type_norm(features, irrep_name):
    o3 = load_o3()
    values = [features.nodes[0, block] for (_, irrep), block in
              zip(o3.Irreps(features.irreps), o3.Irreps(features.irreps).slices())
              if str(irrep) == irrep_name]
    return torch.cat(values).norm()


def test_nonpolar_centrosymmetric_site_can_read_antisymmetric_born_tensor():
    torch.manual_seed(23)
    seeds = torch.tensor([[1., .4, 0], [.3, 1.6, 0], [0, 0, 1.5]], dtype=torch.float64)
    native = features_for(torch.cat([seeds, -seeds]))
    adapter = EquivariantAdapter("2x0e", PROFILE, cutoff=2., channels=3).double()
    lifted = adapter(native)
    assert central_type_norm(lifted, "1o") < 1e-12
    assert central_type_norm(lifted, "1e") > 1e-8
    head = ResponseReadout(PROFILE, "equivariant", property_spec("born_charge")).double()
    tensor = head(lifted)[0]
    assert (tensor - tensor.T).norm() > 1e-8


def test_d2d_nonpolar_site_retains_allowed_odd_quadrupole():
    torch.manual_seed(19)
    identity = torch.eye(3, dtype=torch.float64)
    generators = [torch.diag(torch.tensor([1., -1., -1.], dtype=torch.float64)),
                  torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., -1.]], dtype=torch.float64)]
    group = [identity]
    for matrix in group:
        for generator in generators:
            candidate = matrix @ generator
            if not any(torch.equal(candidate, item) for item in group):
                group.append(candidate)
    assert len(group) == 8
    seed = torch.tensor([.8, .5, 1.2], dtype=torch.float64)
    native = features_for(torch.stack([matrix @ seed for matrix in group]))
    adapter = EquivariantAdapter("2x0e", PROFILE, cutoff=2., channels=3).double()
    lifted = adapter(native)
    assert central_type_norm(lifted, "1o") < 1e-12
    assert central_type_norm(lifted, "2o") > 1e-8


@pytest.mark.parametrize("determinant", [1, -1])
def test_enriched_geometry_lift_transforms_under_rotation_and_inversion(determinant):
    o3 = load_o3()
    torch.manual_seed(8)
    neighbors = torch.tensor([[1., .3, .2], [-.4, 1.4, .7], [.6, -.7, 1.1]], dtype=torch.float64)
    native = features_for(neighbors)
    native.geometry.positions.requires_grad_()
    adapter = EquivariantAdapter("2x0e", PROFILE, cutoff=2., channels=3).double()
    original = adapter(native)
    rotation = determinant * o3.rand_matrix(dtype=torch.float64)
    geometry = native.geometry.with_geometry(native.geometry.positions @ rotation.T,
                                              native.geometry.cell @ rotation.T)
    rotated_native = NativeFeatures(native.nodes, native.irreps, native.kind, native.batch, native.ptr, geometry)
    result = adapter(rotated_native)
    torch.testing.assert_close(result.nodes, original.nodes @ o3.Irreps(PROFILE).D_from_matrix(rotation).T,
                               atol=2e-7, rtol=2e-6)
    gradient = torch.autograd.grad(original.nodes.square().sum(), native.geometry.positions)[0]
    assert torch.isfinite(gradient).all() and gradient.norm() > 0
