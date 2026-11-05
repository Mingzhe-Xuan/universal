"""Live small-model frozen response/state oracles; run exclusively through Slurm."""
import copy
import json
import os
from pathlib import Path

import pytest
import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.engine.optimization import components, FrozenStateGuard, make_optimizer
from universal_gnn.engine.training import build_model
from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from test_physical_task_validation import configured


@pytest.mark.parametrize("kind", ["forcefield", "fixed_frame", "equivariant"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_frozen_backbone_keeps_input_derivatives_and_exact_state(kind, dtype):
    reference, structures, config = configured(kind)
    config = copy.deepcopy(config)
    config["optimization"]["train_backbone"] = False
    torch.manual_seed(123)
    model = build_model(config).to(device=config["device"], dtype=dtype)
    reference.to(device=config["device"], dtype=dtype).eval()
    model.eval()
    batch = StructureBatch.from_structures(structures).to(config["device"], dtype)
    expected, observed = reference(batch, create_graph=True), model(batch, create_graph=True)
    if kind == "forcefield":
        for name in ("total_energy", "forces", "stress"):
            torch.testing.assert_close(observed[name], expected[name], rtol=0, atol=0)
    else: torch.testing.assert_close(observed, expected, rtol=0, atol=0)
    guard = FrozenStateGuard(model)
    locked = {name: value.detach().clone() for name, value in components(model)["backbone"].state_dict().items()}
    readout_before = {name: value.detach().clone() for name, value in components(model)["readout"].state_dict().items()}
    optimizer = make_optimizer(model, config)
    assert [group["name"] for group in optimizer.param_groups] == ["readout"]
    owned = {id(parameter) for group in optimizer.param_groups for parameter in group["params"]}
    assert not owned.intersection(id(p) for p in components(model)["backbone"].parameters())
    model.train()
    assert all(not child.training for child in components(model)["backbone"].modules())
    optimizer.zero_grad()
    value = model(batch, create_graph=True)
    loss = value["forces"].square().sum() + value["stress"].square().sum() if kind == "forcefield" else value.square().sum()
    loss.backward()
    assert all(parameter.grad is None for parameter in components(model)["backbone"].parameters())
    active = [parameter.grad for parameter in components(model)["readout"].parameters() if parameter.grad is not None]
    assert active and all(torch.isfinite(gradient).all() for gradient in active)
    assert sum(float(gradient.detach().double().square().sum()) for gradient in active) > 1e-20
    optimizer.step()
    guard.verify()
    assert all(torch.equal(value, components(model)["backbone"].state_dict()[name]) for name, value in locked.items())
    assert any(not torch.equal(value, components(model)["readout"].state_dict()[name]) for name, value in readout_before.items())
    physics = validate_derivatives(model, structures, config)
    assert physics["passed"], physics
    assert physics["mixed_parameter_gradient_norms"]["backbone"] == 0.
    assert physics["mixed_parameter_gradient_norms"]["readout"] > 1e-10
    guard.verify()
    if os.environ.get("UGNN_FROZEN_RESPONSE_REPORTS"):
        path = Path(os.environ["UGNN_FROZEN_RESPONSE_REPORTS"]) / (kind + "-" + str(dtype) + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf8") as stream:
            json.dump(dict(config=config, dtype=str(dtype), kind=kind, physics=physics,
                initial_forward_exact=True, frozen_parameters_and_buffers_exact=True, frozen_modules_eval=True,
                backbone_optimizer_owned_parameters=0, backbone_gradients_absent=True, readout_parameters_changed=True,
                formal_training_runs=0, scope="Small live frozen response/state numerical oracle, not original official full-data readiness or training"),
                stream, indent=2, allow_nan=False)
