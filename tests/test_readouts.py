import pytest
import torch

from universal_gnn.contracts import NativeFeatures
from universal_gnn.properties import property_spec
from universal_gnn.readouts import ResponseReadout

from test_backbones import tiny_batch


@pytest.mark.parametrize("name,shape", [("dielectric", (3, 3)),
                                        ("piezoelectric", (3, 3, 3)),
                                        ("elastic", (3, 3, 3, 3))])
def test_response_jacobian_retains_parameter_gradient(name, shape):
    batch = tiny_batch()
    nodes = torch.randn(2, 4, dtype=torch.float64, requires_grad=True)
    features = NativeFeatures(nodes, "4x0e", "invariant", batch.batch, batch.ptr, batch)
    model = ResponseReadout("4x0e", "invariant", property_spec(name)).double()
    response = model(features)
    assert response.shape == (1, *shape)
    gradients = torch.autograd.grad(response.square().sum(), [nodes, *model.parameters()])
    assert all(torch.isfinite(gradient).all() for gradient in gradients)
    assert gradients[0].norm() > 0
    model.eval()
    torch.testing.assert_close(model(features), response.detach())


def test_cartesian_response_transforms_with_both_vector_axes():
    from universal_gnn.contracts.e3nn_compat import load_o3
    o3 = load_o3()
    torch.manual_seed(7)
    batch = tiny_batch()
    irreps = o3.Irreps("2x0e + 2x1e + 2x2e")
    nodes = torch.randn(2, irreps.dim, dtype=torch.float64, requires_grad=True)
    model = ResponseReadout(str(irreps), "equivariant", property_spec("dielectric")).double()
    features = NativeFeatures(nodes, str(irreps), "equivariant", batch.batch, batch.ptr, batch)
    reference = model(features)
    rotation = o3.rand_matrix(dtype=torch.float64)
    rotated_nodes = nodes @ irreps.D_from_matrix(rotation).T
    rotated = NativeFeatures(rotated_nodes, str(irreps), "equivariant", batch.batch, batch.ptr, batch)
    expected = torch.einsum("ia,bac,jc->bij", rotation, reference, rotation)
    torch.testing.assert_close(model(rotated), expected, rtol=2e-6, atol=2e-7)
    node_gradient = torch.autograd.grad(reference.square().sum(), nodes)[0]
    assert torch.isfinite(node_gradient).all() and node_gradient.norm() > 0
