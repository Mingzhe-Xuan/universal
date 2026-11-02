import os

import pytest
import torch

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.contracts.e3nn_compat import load_o3

from test_backbones import tiny_batch


@pytest.mark.parametrize("name", os.environ.get("UGNN_NATIVE_BACKBONES", "equiformer").split(","))
def test_equivariant_native_features_condition_and_second_derivatives(name):
    o3 = load_o3()
    torch.manual_seed(12)
    model = make_backbone(name, width=8, layers=2, cutoff=2., context_dim=2).double()
    batch = tiny_batch()
    batch.positions.requires_grad_()
    context = torch.tensor([[.3, -.2]], dtype=torch.float64, requires_grad=True)
    native = model.encode(batch, context)
    native.validate()
    assert native.kind == "equivariant"
    irreps = o3.Irreps(native.irreps)
    assert any(irrep.l > 0 for _, irrep in irreps)
    objective = native.nodes.square().sum()
    dx, dc = torch.autograd.grad(objective, (batch.positions, context), create_graph=True)
    assert torch.isfinite(dx).all() and dx.norm() > 0
    assert torch.isfinite(dc).all() and dc.norm() > 0
    gradients = torch.autograd.grad(dx.square().sum(), list(model.parameters()), allow_unused=True)
    active = [gradient for gradient in gradients if gradient is not None]
    assert active and all(torch.isfinite(gradient).all() for gradient in active)
    assert sum(float(gradient.norm()) for gradient in active) > 0
    for determinant in [1, -1]:
        rotation = determinant * o3.rand_matrix(dtype=torch.float64)
        rotated_batch = batch.with_geometry(batch.positions @ rotation.T, batch.cell @ rotation.T)
        rotated = model.encode(rotated_batch, context)
        expected = native.nodes @ irreps.D_from_matrix(rotation).T
        torch.testing.assert_close(rotated.nodes, expected, rtol=5e-5, atol=5e-7)
