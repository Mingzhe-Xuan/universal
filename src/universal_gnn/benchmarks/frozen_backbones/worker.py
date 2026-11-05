"""Instrument the unchanged disposable worker with exact frozen-state checks."""

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
from unittest.mock import patch

from .. import probe_worker
from ..execution.gates import file_sha

PROTOCOL = "frozen_optimizer_state_v1"
DELEGATE = probe_worker.execute


def check_request(request):
    config = request["config"]
    task = config.get("task", {})
    if (request.get("phase") != "train" or config.get("seed") != 123 or config.get("structures") != "all" or
            config.get("max_atoms") is not None or config.get("dtype") != "float32" or
            not str(config.get("device", "")).startswith("cuda") or
            config.get("optimization", {}).get("train_backbone") is not False or
            config.get("optimization", {}).get("train_readout") is not True or
            config.get("prediction", {}).get("head_mode") != "reset" or
            config.get("backbone", {}).get("initialization") != "pretrained" or
            config.get("backbone", {}).get("implementation") != "official" or
            config.get("backbone", {}).get("name") not in {"cgcnn", "alignn", "mace", "nequip"} or
            not (task.get("kind") == "forcefield" or task.get("kind") == "supervised" and task.get("property") == "dielectric")):
        raise ValueError("Require a full single123 official pretrained frozen response training probe")


def state_sha(module, *, parameters_only=False):
    """Hash all actual persistent tensors, including dtype, shape and buffers."""
    import torch

    digest = hashlib.sha256()
    values = dict(module.named_parameters()) if parameters_only else module.state_dict()
    for name, value in sorted(values.items()):
        digest.update(json.dumps([name, str(value.dtype), list(value.shape)], separators=(",", ":")).encode() + b"\n")
        digest.update(value.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


@contextmanager
def audit_optimizers(result):
    """Observe identical optimizer steps; never detach a model's input graph."""
    import torch
    from universal_gnn.engine import optimization

    original = optimization.make_optimizer
    captured = []

    def make(model, config):
        if captured:
            raise RuntimeError("One disposable frozen probe must construct exactly one optimizer")
        optimizer = original(model, config)
        modules = optimization.components(model)
        backbone, readout = modules["backbone"], modules["readout"]
        owned = [p for group in optimizer.param_groups for p in group["params"]]
        backbone_ids = {id(p) for p in backbone.parameters()}
        expected = {id(p) for p in model.parameters() if p.requires_grad}
        if (len(owned) != len({id(p) for p in owned}) or {id(p) for p in owned} != expected or
                backbone_ids.intersection(id(p) for p in owned) or any(p.requires_grad for p in backbone.parameters()) or
                not any(p.requires_grad for p in readout.parameters())):
            raise RuntimeError("Frozen backbone/optimizer ownership differs from the declared policy")
        guard = optimization.FrozenStateGuard(model)
        guard.verify()
        audit = dict(protocol=PROTOCOL, optimizer_steps=0, guard_checks=1,
            backbone_optimizer_parameters=0, backbone_requires_grad_parameters=0,
            backbone_gradients_absent=True, frozen_modules_eval=True,
            backbone_state_before_sha256=state_sha(backbone), readout_state_before_sha256=state_sha(readout),
            readout_parameters_before_sha256=state_sha(readout, parameters_only=True),
            minimum_readout_gradient_norm=None, maximum_readout_gradient_norm=None,
            optimizer_groups=[group.get("name") for group in optimizer.param_groups],
            changed_optimizer_arithmetic=False, changed_rng=False,
            instrumentation_source_sha256=file_sha(Path(__file__)), delegate_source_sha256=file_sha(Path(probe_worker.__file__)))
        result["frozen_audit"] = audit
        original_step = optimizer.step

        def step(*args, **kwargs):
            guard.verify();audit["guard_checks"] += 1
            if any(p.requires_grad or p.grad is not None for p in backbone.parameters()):
                raise RuntimeError("Frozen backbone acquired trainability or gradients")
            gradients = [p.grad for p in readout.parameters() if p.grad is not None]
            norm = math.sqrt(sum(float(g.detach().double().square().sum()) for g in gradients))
            if not gradients or not all(bool(torch.isfinite(g).all()) for g in gradients) or not math.isfinite(norm) or norm <= 0:
                raise FloatingPointError("Missing finite positive frozen-probe readout gradients")
            value = original_step(*args, **kwargs)
            guard.verify();audit["guard_checks"] += 1
            audit["optimizer_steps"] += 1
            audit["minimum_readout_gradient_norm"] = min(norm, audit["minimum_readout_gradient_norm"] or norm)
            audit["maximum_readout_gradient_norm"] = max(norm, audit["maximum_readout_gradient_norm"] or norm)
            return value

        optimizer.step = step
        captured.append((guard, backbone, readout, audit))
        return optimizer

    with patch.object(optimization, "make_optimizer", make):
        yield
    if len(captured) != 1:
        raise RuntimeError("Frozen probe did not construct its declared optimizer")
    guard, backbone, readout, audit = captured[0]
    guard.verify();audit["guard_checks"] += 1
    audit.update(backbone_state_after_sha256=state_sha(backbone), readout_state_after_sha256=state_sha(readout),
                 readout_parameters_after_sha256=state_sha(readout, parameters_only=True))
    if (audit["optimizer_steps"] < 1 or audit["backbone_state_after_sha256"] != audit["backbone_state_before_sha256"] or
            audit["readout_parameters_after_sha256"] == audit["readout_parameters_before_sha256"]):
        raise RuntimeError("Frozen probe changed backbone state or failed to update its readout")
    audit["state_exact_after_every_step"] = True
    audit["readout_parameters_changed"] = True


def execute(request, result, result_path):
    check_request(request)
    with audit_optimizers(result):
        DELEGATE(request, result, result_path)


def main():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen capacity workers require Slurm")
    with patch.object(probe_worker, "execute", execute):
        probe_worker.main()


if __name__ == "__main__":
    main()
