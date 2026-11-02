import torch
from dataclasses import replace

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.tasks.generation import (CONTEXT_DIM, PeriodicDenoiser, corrupt, decode_cell,
                                          encode_cell, fractional_coordinates, periodic_score, DirectionReadout)

from test_backbones import tiny_batch


def test_scalar_only_official_feature_format_uses_differentiable_geometric_vector_readout():
    torch.manual_seed(12)
    batch = tiny_batch()
    batch.positions.requires_grad_(True)
    backbone = make_backbone("cgcnn", implementation="legacy", width=8, layers=1, cutoff=2.).double()
    features = replace(backbone.encode(batch), kind="equivariant")
    readout = DirectionReadout(features.irreps, "equivariant", 2.).double()
    assert not readout.native_polar
    vectors = readout(features)
    rotation = torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]], dtype=torch.float64)
    rotated = batch.with_geometry(batch.positions @ rotation.T, batch.cell @ rotation.T)
    rotated_features = replace(backbone.encode(rotated), kind="equivariant")
    torch.testing.assert_close(readout(rotated_features), vectors @ rotation.T, rtol=1e-8, atol=1e-9)
    gradient = torch.autograd.grad(vectors.square().sum(), batch.positions, create_graph=True)[0]
    second = torch.autograd.grad(gradient.square().sum(), batch.positions)[0]
    assert torch.isfinite(second).all() and gradient.norm() > 0


def test_log_cholesky_preserves_metric_volume_and_has_finite_derivative():
    cell = torch.tensor([[[3., .2, .1], [.4, 4., .3], [.2, .5, 5.]]],
                        dtype=torch.float64, requires_grad=True)
    decoded = decode_cell(encode_cell(cell))
    torch.testing.assert_close(decoded @ decoded.transpose(-1, -2), cell @ cell.transpose(-1, -2))
    torch.testing.assert_close(torch.linalg.det(decoded), torch.linalg.det(cell).abs())
    gradient = torch.autograd.grad(decoded.square().sum(), cell)[0]
    assert torch.isfinite(gradient).all()
    cubic = torch.eye(3, dtype=torch.float64)[None].requires_grad_()
    gradient = torch.autograd.grad(decode_cell(encode_cell(cubic)).sum(), cubic)[0]
    assert torch.isfinite(gradient).all()


def test_periodic_scaled_score_matches_log_density_derivative_at_boundary():
    delta = torch.tensor([[-.99, -.1, .99], [.001, .499, -.499]], dtype=torch.float64,
                         requires_grad=True)
    sigma = torch.tensor([[.12], [.02]], dtype=torch.float64)
    images = torch.arange(-3, 4, dtype=torch.float64)
    log_density = torch.logsumexp(-.5 * ((delta[..., None] + images) / sigma[..., None]).square(), -1)
    exact = torch.autograd.grad(log_density.sum(), delta)[0] * sigma
    torch.testing.assert_close(periodic_score(delta, sigma), exact)
    torch.testing.assert_close(periodic_score(delta + 1, sigma), exact, atol=1e-10, rtol=1e-10)


def test_denoising_heads_reach_backbone_and_sample_preserves_composition():
    torch.manual_seed(3)
    model = PeriodicDenoiser(make_backbone("cgcnn", implementation="legacy", width=8, layers=1, cutoff=2.,
                                          context_dim=CONTEXT_DIM)).double()
    batch = tiny_batch()
    noisy, time, targets = corrupt(batch, generator=torch.Generator().manual_seed(8))
    prediction = model(noisy, time)
    loss = sum((prediction[key] - targets[key]).square().mean() for key in targets)
    gradients = torch.autograd.grad(loss, list(model.backbone.parameters()), allow_unused=True)
    active = [gradient for gradient in gradients if gradient is not None]
    assert active and all(torch.isfinite(gradient).all() for gradient in active)
    assert sum(float(gradient.norm()) for gradient in active) > 0
    generated = model.eval().sample(batch, steps=2, inner_steps=1)
    torch.testing.assert_close(generated.numbers, batch.numbers)
    assert torch.linalg.det(generated.cell).min() > 0
    frac = fractional_coordinates(generated)
    assert bool(((frac >= -1e-12) & (frac < 1 + 1e-12)).all())
    assert all(not targets for targets in generated.targets)
