"""Live frozen optimizer instrumentation controls; CPU Slurm only."""

import copy
import json
import os
from pathlib import Path

import pytest
import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.engine import optimization
from universal_gnn.engine.training import build_model
from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.benchmarks.frozen_backbones.worker import audit_optimizers, state_sha
from universal_gnn.benchmarks.frozen_backbones.contracts import checked_audit
from universal_gnn.benchmarks.prediction_assessment.runtime import verify_physics
from test_physical_task_validation import configured


@pytest.mark.parametrize("kind", ["forcefield", "fixed_frame", "equivariant"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_audit_wraps_real_steps_preserving_body_and_input_derivatives(kind, dtype):
    assert os.environ.get("SLURM_JOB_ID"), "Numerical controls require Slurm"
    _, structures, config = configured(kind)
    config = copy.deepcopy(config);config["optimization"]["train_backbone"] = False
    torch.manual_seed(123)
    model = build_model(config).to(device="cpu", dtype=dtype)
    uninstrumented = copy.deepcopy(model)
    original_optimizer = optimization.make_optimizer
    modules = optimization.components(model)
    before = {name: value.detach().clone() for name, value in modules["backbone"].state_dict().items()}
    params_before = {name: value.detach().clone() for name, value in modules["readout"].named_parameters()}
    batch = StructureBatch.from_structures(structures).to(device="cpu", dtype=dtype)
    shadow_batch = StructureBatch.from_structures(structures).to(device="cpu", dtype=dtype)
    rng_before = torch.get_rng_state()
    result = {}
    with audit_optimizers(result):
        optimizer = optimization.make_optimizer(model, config)
        for _ in range(3):
            model.train();optimizer.zero_grad(set_to_none=True)
            value = model(batch, create_graph=True)
            loss = value["forces"].square().sum() + value["stress"].square().sum() if kind == "forcefield" else value.square().sum()
            loss.backward();optimizer.step()
    rng_after = torch.get_rng_state()
    shadow_optimizer = original_optimizer(uninstrumented, config)
    torch.set_rng_state(rng_before)
    for _ in range(3):
        uninstrumented.train();shadow_optimizer.zero_grad(set_to_none=True)
        value = uninstrumented(shadow_batch, create_graph=True)
        loss = value["forces"].square().sum() + value["stress"].square().sum() if kind == "forcefield" else value.square().sum()
        loss.backward();shadow_optimizer.step()
    assert torch.equal(torch.get_rng_state(), rng_after)
    assert all(torch.equal(value, uninstrumented.state_dict()[name]) for name, value in model.state_dict().items())
    assert all(torch.equal(value, modules["backbone"].state_dict()[name]) for name, value in before.items())
    assert any(not torch.equal(value, dict(modules["readout"].named_parameters())[name]) for name, value in params_before.items())
    assert all(not child.training for child in modules["backbone"].modules())
    assert all(not p.requires_grad and p.grad is None for p in modules["backbone"].parameters())
    audit = result["frozen_audit"]
    checked_audit(audit, 3, instrumentation_sha256=audit["instrumentation_source_sha256"], delegate_sha256=audit["delegate_source_sha256"])
    physics = validate_derivatives(model, structures, config)
    assert physics["passed"] and physics["mixed_parameter_gradient_norms"]["backbone"] == 0.
    assert physics["mixed_parameter_gradient_norms"]["readout"] > 1e-10
    if dtype == torch.float32:
        verify_physics(physics, "forcefield" if kind == "forcefield" else "dielectric",
                       dict(ids=list(batch.identifiers)), frozen_backbone=True)
    assert state_sha(modules["backbone"]) == audit["backbone_state_before_sha256"]
    if os.environ.get("UGNN_FROZEN_WORKER_REPORTS"):
        root = Path(os.environ["UGNN_FROZEN_WORKER_REPORTS"]);root.mkdir(parents=True, exist_ok=True)
        report = dict(status="passed", kind=kind, dtype=str(dtype), audit=audit, physics=physics,
                      identical_to_uninstrumented_steps=True, rng_state_exact=True,
                      actual_optimizer_steps=3, official_training_runs=0, scope="Small CPU instrumentation/control, not official CUDA capacity")
        (root / (kind + "-" + str(dtype) + ".json")).write_text(json.dumps(report, indent=2, allow_nan=False))


@pytest.mark.parametrize("mutation", ["buffer", "mode", "gradient", "ownership"])
def test_audit_refuses_frozen_state_mode_gradient_or_optimizer_mutation(mutation):
    assert os.environ.get("SLURM_JOB_ID"), "Numerical controls require Slurm"
    _, _, config = configured("forcefield")
    config = copy.deepcopy(config);config["optimization"]["train_backbone"] = False
    model = build_model(config).to(device="cpu", dtype=torch.float32)
    body = optimization.components(model)["backbone"]
    body.register_buffer("test_only_state", torch.tensor(0.))
    with pytest.raises(RuntimeError):
        with audit_optimizers({}):
            if mutation == "ownership":next(body.parameters()).requires_grad_(True)
            optimizer = optimization.make_optimizer(model, config)
            if mutation == "buffer":body.test_only_state.add_(1.)
            elif mutation == "mode":body.train()
            elif mutation == "gradient":next(body.parameters()).grad = torch.ones_like(next(body.parameters()))
            if mutation in {"mode", "gradient"}:optimizer.step()
