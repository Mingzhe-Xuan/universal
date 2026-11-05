"""Live rank3/4 response checks and independent failure oracles; run in Slurm."""
from itertools import product
import math
import json
import os
from pathlib import Path

import pytest
import torch

from universal_gnn.benchmarks.validation.cartesian import rotation_subscripts
from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.engine.training import build_model
from test_physical_task_validation import configured


def high_rank(task, kind):
    _, structures, config = configured("equivariant" if kind == "equivariant" else "fixed_frame")
    config["task"]["property"] = task
    torch.manual_seed(123)
    return build_model(config).to(config["device"]), structures, config


@pytest.mark.parametrize("task,rank", [("piezoelectric", 3), ("elastic", 4)])
@pytest.mark.parametrize("kind", ["fixed_frame", "equivariant"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_live_response_derivative_geometry_and_mixed_gradients(task, rank, kind, dtype):
    model, structures, config = high_rank(task, kind)
    model.to(dtype=dtype)
    result = validate_derivatives(model, structures, config)
    assert result["passed"], result
    response = result["response"]
    assert response["rank"] == rank and response["shape"] == [3] * rank
    assert response["inversion_parity"] == (-1)**rank and response["no_symmetry_projection"]
    assert torch.as_tensor(response["analytic"]).shape == (1, *([3] * rank))
    assert all(math.isfinite(value) and value > 0 for value in result["mixed_parameter_gradient_norms"].values())
    checks = result["checks"]
    assert checks["response_auxiliary_finite_difference"]["passed"]
    assert checks["translation_response"]["passed"] and checks["eval_batch_response"]["passed"]
    if kind == "equivariant":
        assert checks["rotation_response_covariance"]["required"]
        assert checks["rotation_response_covariance"]["passed"]
        assert checks["inversion_rank" + str(rank) + "_response"]["passed"]
    else:
        assert not checks["rotation_response_covariance"]["required"]
        assert checks["rotation_fixed_frame_invariance"]["passed"]
        assert "inversion_rank" + str(rank) + "_response" not in checks
    if os.environ.get("UGNN_RESPONSE_REPORTS"):
        path = Path(os.environ["UGNN_RESPONSE_REPORTS"]) / (task + "-" + kind + "-" + str(dtype) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf8") as stream:
            json.dump(dict(config=config, result=result, scope="Small live model numerical validator acceptance; no official full-data preparation or training"), stream, indent=2, allow_nan=False)


@pytest.mark.parametrize("rank", [2, 3, 4])
def test_rotation_matches_explicit_component_oracle_without_symmetrizing(rank):
    # A deliberately nonsymmetric source checks every slot independently.
    source = (torch.arange(2 * 3**rank, dtype=torch.float64).reshape(2, *([3] * rank))**1.3 + .37) / 100
    x = torch.tensor([[.8, -.6, 0.], [.6, .8, 0.], [0., 0., 1.]], dtype=torch.float64)
    y = torch.tensor([[1., 0., 0.], [0., 12/13, -5/13], [0., 5/13, 12/13]], dtype=torch.float64)
    rotation = x @ y
    actual = torch.einsum(rotation_subscripts(rank), *((rotation,) * rank), source)
    expected = torch.zeros_like(source)
    for batch in range(2):
        for out_axes in product(range(3), repeat=rank):
            total = 0.
            for in_axes in product(range(3), repeat=rank):
                weight = math.prod(float(rotation[i, j]) for i, j in zip(out_axes, in_axes))
                total += weight * float(source[(batch, *in_axes)])
            expected[(batch, *out_axes)] = total
    assert torch.allclose(actual, expected, rtol=1e-12, atol=1e-12)
    restored = torch.einsum(rotation_subscripts(rank), *((rotation.T,) * rank), actual)
    assert torch.allclose(restored, source, rtol=1e-12, atol=1e-12)
    assert not torch.allclose(source, source.transpose(-1, -2))


@pytest.mark.parametrize("task", ["piezoelectric", "elastic"])
def test_false_equivariance_claim_is_rejected_even_when_auxiliary_derivative_is_correct(task):
    model, structures, config = high_rank(task, "fixed_frame")
    model.readout.descriptor["transformation_guarantee"] = "O3_cartesian"
    result = validate_derivatives(model, structures, config)
    assert result["checks"]["response_auxiliary_finite_difference"]["passed"]
    assert result["checks"]["rotation_response_covariance"]["required"]
    assert not result["checks"]["rotation_response_covariance"]["passed"]
    assert not result["passed"]


def test_wrong_odd_rank_inversion_is_independently_rejected(monkeypatch):
    model, structures, config = high_rank("piezoelectric", "equivariant")
    original = model.forward
    def wrong_inversion(batch, **kwargs):
        value = original(batch, **kwargs)
        return -value if float(batch.positions.sum()) < 0 else value
    monkeypatch.setattr(model, "forward", wrong_inversion)
    result = validate_derivatives(model, structures, config)
    assert result["checks"]["response_auxiliary_finite_difference"]["passed"]
    assert not result["checks"]["inversion_rank3_response"]["passed"]
    assert not result["passed"]


@pytest.mark.parametrize("task", ["piezoelectric", "elastic"])
def test_wrong_saved_derivative_is_rejected(task, monkeypatch):
    model, structures, config = high_rank(task, "equivariant")
    original = model.forward
    monkeypatch.setattr(model, "forward", lambda *args, **kwargs: original(*args, **kwargs) + .1)
    result = validate_derivatives(model, structures, config)
    assert not result["checks"]["response_auxiliary_finite_difference"]["passed"]
    assert not result["passed"]


def test_shape_broadcasting_cannot_hide_wrong_response_format(monkeypatch):
    model, structures, config = high_rank("piezoelectric", "equivariant")
    original = model.forward
    monkeypatch.setattr(model, "forward", lambda *args, **kwargs: original(*args, **kwargs).flatten(1))
    with pytest.raises(ValueError, match="shape differs"):
        validate_derivatives(model, structures, config)
