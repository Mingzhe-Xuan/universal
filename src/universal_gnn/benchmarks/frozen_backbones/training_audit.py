"""Whole-training state evidence around the unchanged optimizer and engine."""

import math
import os
from pathlib import Path
import re

from ..execution.gates import file_sha, read_json
from ..preflight import write_json
from .contracts import checked_audit
from .worker import audit_optimizers, state_sha

PROTOCOL = "frozen_full_training_v1"


def training_sources():
    repository = Path(__file__).resolve().parents[4]
    names = ["benchmarks/frozen_backbones/" + name for name in
             ("training_audit.py", "worker.py", "execution.py", "contracts.py", "readiness.py")]
    names += ["engine/" + name for name in ("training.py", "optimization.py", "runtime.py")]
    names += ["benchmarks/execution/runner.py", "benchmarks/prediction_assessment/runtime.py"]
    return {"src/universal_gnn/" + name: file_sha(repository / "src/universal_gnn" / name) for name in names}


def checkpoint_state(path, expected_config):
    """Load actual checkpoint tensors on CPU, without a forward or an optimizer step."""
    import torch
    from universal_gnn.engine.optimization import components, component_audit, parameter_groups
    from universal_gnn.engine.training import load_checkpoint

    path = Path(path)
    digest = file_sha(path)
    saved = torch.load(path, map_location="cpu", weights_only=True)
    if saved["config"] != expected_config:
        raise ValueError("Frozen checkpoint differs from the actual resolved training recipe")
    model = load_checkpoint(path, device="cpu")
    modules = components(model)
    policy = saved.get("components", {})
    if (policy.get("policy") != model._component_policy or
            policy.get("optimizer_groups") != parameter_groups(model) or
            any(row["name"] == "backbone" for row in parameter_groups(model))):
        raise ValueError("Frozen checkpoint optimization policy/groups changed")
    metadata = component_audit(model)
    if (metadata["backbone"]["trainable_parameters"] != 0 or
            metadata["backbone"]["module_modes"]["train"] != 0 or
            metadata["readout"]["trainable_parameters"] <= 0):
        raise ValueError("Reloaded checkpoint lost the frozen body or trainable readout")
    result = dict(path=str(path), sha256=digest,
        backbone_state_sha256=state_sha(modules["backbone"]),
        readout_parameters_sha256=state_sha(modules["readout"], parameters_only=True),
        components=metadata, optimizer_groups=policy["optimizer_groups"], policy=policy["policy"])
    if file_sha(path) != digest:
        raise ValueError("Checkpoint changed while its actual frozen tensors were checked")
    return result


def audited_training(config, output, *, event_callback=None):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen full training and checkpoint audit require Slurm")
    from universal_gnn.engine.training import run_training

    observed = {}
    # The nested observer retains its original capacity-delegate source field;
    # this parent separately binds the actual unchanged full training engine.
    with audit_optimizers(observed):
        trained = run_training(config, output, event_callback=event_callback)
    audit = dict(protocol=PROTOCOL, source_sha256=training_sources(),
        actual_training_delegate="src/universal_gnn/engine/training.py", optimizer=observed["frozen_audit"],
        checkpoints={role: checkpoint_state(trained[name], trained["config"])
                     for role, name in (("best", "best_checkpoint"), ("last", "checkpoint"))})
    path = Path(output) / "frozen-training-audit.json"
    write_json(path, audit)
    trained["frozen_training_audit"] = dict(path=str(path), sha256=file_sha(path), protocol=PROTOCOL)
    write_json(Path(output) / "report.json", trained)
    return trained


def check_training_audit(trained, gate):
    """Tensor-free replay for both execution and the independent no-model stage."""
    entry = trained.get("frozen_training_audit", {})
    path = Path(entry.get("path", ""))
    if (entry.get("protocol") != PROTOCOL or path != Path(gate["case"]["run_directory"]) / "frozen-training-audit.json" or
            not path.is_file() or file_sha(path) != entry.get("sha256")):
        raise ValueError("Missing original whole-training frozen state audit")
    audit = read_json(path)
    if (audit.get("protocol") != PROTOCOL or audit.get("source_sha256") != training_sources() or
            audit.get("actual_training_delegate") != "src/universal_gnn/engine/training.py"):
        raise ValueError("Frozen training instrumentation/actual delegate source changed")
    body = audit.get("optimizer", {})
    epochs = trained["completed_epochs"]
    steps = epochs * math.ceil(gate["counts"]["train"] / gate["config"]["batch_size"])
    sources = audit["source_sha256"]
    checked_audit(body, steps,
        instrumentation_sha256=sources["src/universal_gnn/benchmarks/frozen_backbones/worker.py"],
        delegate_sha256=file_sha(Path(__file__).parents[1] / "probe_worker.py"))
    expected = gate["frozen_audit"]["backbone_state_before_sha256"]
    if body["backbone_state_before_sha256"] != expected:
        raise ValueError("Full training did not start from the independently verified original public body")
    checkpoints = audit.get("checkpoints", {})
    if set(checkpoints) != {"best", "last"}:
        raise ValueError("Both actual validation-best and last checkpoint must retain the original body")
    for role, key in (("best", "best_checkpoint"), ("last", "checkpoint")):
        row = checkpoints[role]
        metadata, policy = row.get("components", {}), row.get("policy", {})
        if (row.get("path") != trained[key] or row.get("sha256") != file_sha(trained[key]) or
                row.get("backbone_state_sha256") != expected or
                not isinstance(row.get("readout_parameters_sha256"), str) or
                not re.fullmatch(r"[0-9a-f]{64}", row["readout_parameters_sha256"]) or
                row.get("readout_parameters_sha256") == body["readout_parameters_before_sha256"] or
                policy != trained["config"]["optimization"] or policy.get("train_backbone") is not False or
                policy.get("train_readout") is not True or
                not row.get("optimizer_groups") or
                "readout" not in [group["name"] for group in row["optimizer_groups"]] or
                "backbone" in [group["name"] for group in row["optimizer_groups"]] or
                metadata.get("backbone", {}).get("trainable_parameters") != 0 or
                metadata.get("backbone", {}).get("mode") != "eval" or
                metadata.get("backbone", {}).get("module_modes", {}).get("train") != 0 or
                metadata.get("readout", {}).get("trainable_parameters", 0) <= 0):
            raise ValueError("Actual checkpoint body/head/optimizer/mode evidence changed")
    if checkpoints["last"]["readout_parameters_sha256"] != body["readout_parameters_after_sha256"]:
        raise ValueError("Last checkpoint does not contain the final actually updated readout")
    return dict(protocol=PROTOCOL, audit_sha256=entry["sha256"], optimizer_steps=steps,
        backbone_state_sha256=expected, backbone_gradients_absent=True,
        readout_parameters_changed=True, checkpoint_sha256={role: row["sha256"] for role, row in checkpoints.items()})
