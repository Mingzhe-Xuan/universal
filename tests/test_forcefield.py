import torch

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.data.geometry import strain_batch
from universal_gnn.tasks import ForceFieldModel

from test_backbones import tiny_batch


def test_force_stress_finite_difference_and_parameter_chain():
    torch.manual_seed(4)
    model = ForceFieldModel(make_backbone("cgcnn", width=8, layers=1, cutoff=2.)).double()
    batch = tiny_batch()
    predictions = model(batch)
    assert predictions["forces"].shape == (2, 3)
    assert predictions["stress"].shape == (1, 3, 3)
    step = 1e-5
    offset = torch.zeros_like(batch.positions)
    offset[1, 0] = step
    plus = model.energy_model(batch.with_geometry(batch.positions + offset, batch.cell))
    minus = model.energy_model(batch.with_geometry(batch.positions - offset, batch.cell))
    numeric_force = -(plus - minus).squeeze() / (2 * step)
    torch.testing.assert_close(predictions["forces"][1, 0], numeric_force, rtol=2e-5, atol=1e-9)
    strain = torch.zeros_like(batch.cell)
    strain[0, 0, 1] = step
    plus = model.energy_model(strain_batch(batch, strain))
    minus = model.energy_model(strain_batch(batch, -strain))
    numeric_stress = (plus - minus).squeeze() / (2 * step * torch.linalg.det(batch.cell)[0]) * 160.21766208
    torch.testing.assert_close(predictions["stress"][0, 0, 1], numeric_stress, rtol=2e-5, atol=1e-9)
    objective = predictions["forces"].square().sum() + predictions["stress"].square().sum()
    gradients = torch.autograd.grad(objective, list(model.backbone.parameters()), allow_unused=True)
    active = [gradient for gradient in gradients if gradient is not None]
    assert active and all(torch.isfinite(gradient).all() for gradient in active)
    assert sum(float(gradient.norm()) for gradient in active) > 0


def test_force_hessian_keeps_external_position_graph():
    torch.manual_seed(11)
    model = ForceFieldModel(make_backbone("cgcnn", width=8, layers=1, cutoff=2.)).double()
    batch = tiny_batch()
    batch.positions.requires_grad_()
    forces = model.eval()(batch, create_graph=True)["forces"]
    hessian_row = torch.autograd.grad(forces[0, 0], batch.positions)[0]
    assert torch.isfinite(hessian_row).all() and hessian_row.norm() > 0
    torch.testing.assert_close(forces.sum(0), torch.zeros(3, dtype=forces.dtype), atol=1e-10, rtol=0)
