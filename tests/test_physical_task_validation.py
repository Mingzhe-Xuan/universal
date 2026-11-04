"""Numerical acceptance of the acceptance routine; run through Slurm."""
from dataclasses import replace
import os

import pytest
import torch

from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.contracts import Structure
from universal_gnn.engine.training import build_model


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


def test_wrong_force_offset_is_rejected_by_independent_energy_difference(monkeypatch):
    model, structures, config = configured('forcefield')
    original = model.forward
    def incorrect(*args, **kwargs):
        values = original(*args, **kwargs)
        return {**values, 'forces': values['forces'] + 1.}
    monkeypatch.setattr(model, 'forward', incorrect)
    result = validate_derivatives(model, structures, config)
    assert not result['passed']
    assert not result['checks']['forces_finite_difference']['passed']
