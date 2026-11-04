"""Numerical acceptance of the acceptance routine; run through Slurm."""
from dataclasses import replace
import os

import pytest
import torch

from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.contracts import Structure
from universal_gnn.engine.training import build_model


class OffsetReadout(torch.nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward(self, *args, **kwargs):
        return self.base(*args, **kwargs) * 1000 + 2**24


def configured(task):
    torch.manual_seed(123)
    config = {'dtype': 'float32', 'device': os.environ.get('UGNN_PHYSICAL_DEVICE', 'cpu'),
              'backbone': {'name': 'gcn', 'width': 8, 'layers': 1},
              'graph': {'name': 'knn', 'k': 2}, 'dataset': {'path': 'unused'},
              'optimization': {'train_backbone': True, 'train_readout': True},
              'task': {'kind': 'supervised', 'property': 'dielectric'},
              'prediction': {'version': 1, 'readout': {'name': 'response', 'pooling': 'mean'}}}
    if task == 'forcefield':
        config['task'] = {'kind': 'forcefield', 'supervised_outputs': ['forces']}
        config['prediction']['readout'] = {'name': 'node_mlp', 'pooling': 'sum', 'hidden_features': [8]}
    elif task == 'equivariant':
        config['prediction']['readout']['feature_processing'] = {'name': 'equivariant', 'cutoff': 3.,
                                                               'profile': 'small_response', 'basis_version': 2}
    a = Structure(torch.tensor([1, 6, 8]), torch.tensor([[.1,.2,.3],[.8,.4,.5],[.3,.9,.6]]),
                  torch.eye(3)*5, torch.zeros(3, dtype=torch.bool), 'a')
    b = replace(a, positions=a.positions*1.2, identifier='b')
    return build_model(config).to(config['device']), [a, b], config


@pytest.mark.parametrize('task', ['forcefield', 'fixed_frame', 'equivariant'])
def test_derivative_geometry_and_mixed_gradients_on_live_model(task):
    model, structures, config = configured(task)
    result = validate_derivatives(model, structures, config)
    assert result['passed'], result
    assert all(value > 0 for value in result['mixed_parameter_gradient_norms'].values())
    if task == 'fixed_frame':
        assert not result['checks']['rotation_response_covariance']['required']
        assert result['checks']['rotation_fixed_frame_invariance']['passed']
    elif task == 'equivariant':
        assert result['checks']['rotation_response_covariance']['required']
        assert result['checks']['inversion_rank2_response']['passed']
    else:
        assert result['checks']['forces_finite_difference']['passed']
        assert result['checks']['train_batch_forces']['passed']


@pytest.mark.parametrize('large_energy_offset', [False, True])
def test_wrong_force_offset_is_rejected_by_independent_energy_difference(monkeypatch, large_energy_offset):
    model, structures, config = configured('forcefield')
    if large_energy_offset:
        model.energy_model.readout = OffsetReadout(model.energy_model.readout)
    original = model.forward
    def incorrect(*args, **kwargs):
        values = original(*args, **kwargs)
        return {**values, 'forces': values['forces'] + 1.}
    monkeypatch.setattr(model, 'forward', incorrect)
    result = validate_derivatives(model, structures, config)
    assert not result['passed']
    assert not result['checks']['forces_finite_difference']['passed']


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
def test_energy_difference_precision_preserves_live_state_and_detects_derivatives(dtype):
    model, structures, config = configured('forcefield')
    model.energy_model.readout = OffsetReadout(model.energy_model.readout)
    model.to(dtype=dtype).eval()
    state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    result = validate_derivatives(model, structures, config)
    assert result['passed'], result
    assert result['finite_difference']['analytic_dtype'] == str(dtype)
    assert result['finite_difference']['energy_reference_dtype'] == 'torch.float64'
    assert max(abs(value) for value in result['finite_difference']['forces_analytic']) > .002
    assert next(model.parameters()).dtype == dtype
    assert state.keys() == model.state_dict().keys()
    assert all(torch.equal(value, model.state_dict()[key]) for key, value in state.items())


def test_original_assessment_helper_accepts_float64_geometry_and_zero_reference(monkeypatch):
    import importlib
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    assess = importlib.import_module('validate_other_forcefields').assess_gradients
    model, structures, _ = configured('forcefield')
    data = [replace(item, positions=item.positions.double(), cell=item.cell.double()) for item in structures]
    result = assess(model.cpu().double(), data)
    assert result['forces_finite_difference_passed']
    assert result['stress_finite_difference_passed']
