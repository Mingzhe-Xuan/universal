"""Checkpoint verification numerical regressions; run through Slurm."""
import copy

import pytest
import torch

from universal_gnn.engine.verification import checkpoint_verification


@pytest.fixture(autouse=True)
def restore_deterministic_policy():
    enabled = torch.are_deterministic_algorithms_enabled()
    warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    yield
    torch.use_deterministic_algorithms(enabled, warn_only=warn_only)


def module():
    model = torch.nn.Linear(3, 4).eval()
    model.register_buffer('running_value', torch.ones(1))
    return model


def test_exact_state_strict_scope_rng_and_default_restoration():
    torch.use_deterministic_algorithms(False)
    first = module()
    second = copy.deepcopy(first)
    random_state = torch.get_rng_state().clone()
    with checkpoint_verification(first, second) as receipt:
        assert torch.are_deterministic_algorithms_enabled()
        assert not torch.is_deterministic_algorithms_warn_only_enabled()
        assert receipt['state_exact'] and receipt['state_tensors'] == 3
        torch.testing.assert_close(first(torch.ones(2, 3)), second(torch.ones(2, 3)), rtol=0, atol=0)
    assert not torch.are_deterministic_algorithms_enabled()
    assert torch.equal(random_state, torch.get_rng_state())


@pytest.mark.parametrize('corrupt', ['parameter', 'buffer', 'dtype', 'keys'])
def test_state_corruption_rejected_before_prediction(corrupt):
    first = module()
    second = copy.deepcopy(first)
    if corrupt == 'parameter':
        with torch.no_grad():
            second.weight.add_(1.)
    elif corrupt == 'buffer':
        second.running_value.add_(1.)
    elif corrupt == 'dtype':
        second.double()
    else:
        del second.running_value
    with pytest.raises(ValueError, match='state'):
        with checkpoint_verification(first, second):
            pytest.fail('Corrupted state reached prediction')


def test_exception_restores_callers_strict_and_warn_only_policy():
    torch.use_deterministic_algorithms(True, warn_only=True)
    first = module()
    with pytest.raises(RuntimeError, match='comparison failed'):
        with checkpoint_verification(first, copy.deepcopy(first)):
            assert not torch.is_deterministic_algorithms_warn_only_enabled()
            raise RuntimeError('comparison failed')
    assert torch.are_deterministic_algorithms_enabled()
    assert torch.is_deterministic_algorithms_warn_only_enabled()


def test_actual_cuda_prediction_comparison_keeps_original_float32_tolerance():
    assert torch.cuda.is_available()
    first = module().cuda()
    second = copy.deepcopy(first)
    data = torch.linspace(-1., 1., 96, device='cuda').reshape(32, 3)
    with checkpoint_verification(first, second):
        prediction, again = first(data), second(data)
        assert torch.equal(prediction, again)
        torch.testing.assert_close(prediction, again, rtol=1e-5, atol=1e-6)
