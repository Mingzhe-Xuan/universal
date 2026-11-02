from __future__ import annotations

import hashlib
import copy
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess

import torch

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.contracts import StructureBatch
from universal_gnn.data.structures import bind_targets, load_structures
from universal_gnn.properties import property_spec
from universal_gnn.tasks import ForceFieldModel, SupervisedModel


def build_model(config):
    from universal_gnn.contracts.schema import validate_config

    validate_config(config)
    backbone_config = dict(config["backbone"])
    name = backbone_config.pop("name")
    if "graph" in config:
        backbone_config["graph_config"] = config["graph"]
    task = config["task"]
    if task["kind"] == "generation":
        from universal_gnn.tasks.generation import CONTEXT_DIM, PeriodicDenoiser

        if backbone_config.get("context_dim", CONTEXT_DIM) != CONTEXT_DIM:
            raise ValueError(f"Generation requires context_dim={CONTEXT_DIM}")
        backbone_config["context_dim"] = CONTEXT_DIM
        return PeriodicDenoiser(make_backbone(name, **backbone_config))
    backbone = make_backbone(name, **backbone_config)
    if task["kind"] == "forcefield":
        return ForceFieldModel(backbone)
    if task["kind"] == "supervised":
        spec = property_spec(task["property"], channels=task.get("channels"), unit=task.get("unit"),
                             definition=task.get("spec"))
        return SupervisedModel(backbone, spec, route=task.get("route"),
                               adapter_version=task.get("adapter_version", 2))
    raise ValueError(f"Task kind not implemented: {task['kind']}")


def dataset(config, limit=10):
    structures = load_structures(config["dataset"]["path"], options=config["dataset"].get("options"))
    if "bindings" in config["dataset"]:
        structures = bind_targets(structures, config["dataset"]["bindings"])
    if len(structures) < limit:
        raise ValueError(f"Acceptance requires {limit} structures, found {len(structures)}")
    return structures[:limit]


def label(batch, name, prediction, *, classification=False):
    values = []
    for identifier, targets in zip(batch.identifiers, batch.targets):
        if name not in targets:
            raise ValueError(f"{identifier}: missing bound label {name}")
        value = torch.as_tensor(targets[name], device=prediction.device)
        values.append(value.flatten() if classification else value.reshape(-1))
    joined = torch.cat(values).to(dtype=torch.long if classification else prediction.dtype)
    expected_shape = (len(prediction),) if classification else prediction.shape
    return joined.reshape(expected_shape)


def predict(model, batch, config, *, training=False):
    if config["task"]["kind"] == "forcefield":
        return model(batch, create_graph=training)
    return {config["task"]["property"]: model(batch, create_graph=training)}


def loss_for(predictions, batch, config, scales=None):
    losses, used_scales = [], {}
    task = config["task"]
    classification = (task["kind"] == "supervised" and
                      property_spec(task["property"], definition=task.get("spec")).kind == "classification")
    for name, prediction in predictions.items():
        target = label(batch, name, prediction, classification=classification)
        if classification:
            losses.append(torch.nn.functional.cross_entropy(prediction, target))
            used_scales[name] = 1.
            continue
        mask = torch.isfinite(target)
        if not bool(mask.any()):
            raise ValueError(f"No finite labels for {name}")
        scale = (scales[name] if scales is not None else max(
            float(target[mask].std(unbiased=False)), float(target[mask].abs().mean()) * .1, 1e-2))
        used_scales[name] = scale
        weight = config["task"].get("loss_weights", {}).get(name, 1.)
        losses.append(weight * ((prediction[mask] - target[mask]) / scale).square().mean())
    return torch.stack(losses).sum(), used_scales


def version_record():
    names = ["torch", "e3nn", "mace-torch", "nequip", "numpy", "ase"]
    record = {}
    for name in names:
        try:
            record[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            record[name] = None
    return record


def execution_record(model):
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[3], check=False)
    return {"git_commit": result.stdout.strip() if result.returncode == 0 else None,
            "slurm": {key: os.environ.get(key) for key in
                      ["SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID", "SLURM_ARRAY_TASK_ID", "SLURMD_NODENAME"]},
            "backbone_class": type(model.backbone).__name__,
            "gnn_class": type(model.backbone.gnn).__name__ if hasattr(model.backbone, "gnn") else None,
            "native_irreps": model.backbone.irreps,
            "backend_version": getattr(model.backbone, "backend_version", None),
            "graph_builder": type(model.backbone.graph_builder).__name__ if hasattr(model.backbone, "graph_builder") else None,
            "extensions": getattr(model.backbone, "extension_provenance", {}),
            "geometry_basis_version": getattr(getattr(model, "adapter", None), "basis_version", None)}


def run_training(config: dict, output: str | Path, *, resume=None, checkpoint_path=None, event_callback=None) -> dict:
    if config["task"]["kind"] == "generation":
        from universal_gnn.engine.generation import run_generation_training

        return run_generation_training(config, output, resume=resume, checkpoint_path=checkpoint_path,
                                       event_callback=event_callback)
    from universal_gnn.engine.runtime import (check_model_config, checkpoint_config, data_fingerprint,
                                               restore_optimizer, save_training_checkpoint)

    config = copy.deepcopy(config)
    saved = torch.load(resume, map_location="cpu", weights_only=True) if resume else None
    if saved is not None:
        if saved.get("format_version", 1) == 1:
            config["task"].setdefault("adapter_version", 1)
        check_model_config(checkpoint_config(saved), config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(config.get("seed", 123))
    device = config.get("device", "cpu")
    model = build_model(config).to(device=device, dtype=torch.float64)
    if saved is not None:
        from universal_gnn.engine.runtime import verify_extensions

        verify_extensions(saved, model)
        model.load_state_dict(saved["state_dict"], strict=True)
    execution = execution_record(model)
    structures = dataset(config, config.get("structures", 10))
    batch = StructureBatch.from_structures(structures).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", 1e-3))
    fingerprint = data_fingerprint(structures)
    state = restore_optimizer(saved, optimizer, config, fingerprint) if saved is not None else None
    completed = state["completed_epochs"] if state is not None else 0
    epochs = config.get("epochs", 10)
    if epochs <= completed:
        raise ValueError(f"epochs is the total target; set it greater than the {completed} completed epochs")
    checkpoint = Path(checkpoint_path) if checkpoint_path is not None else output / "checkpoint.pt"
    versions = version_record()
    model.eval()
    initial_predictions = predict(model, batch, config)
    current_loss, scales = loss_for(initial_predictions, batch, config,
                                   saved.get("scales") if state is not None else None)
    segment_initial_loss = float(current_loss.detach())
    initial_loss = state["initial_loss"] if state is not None else segment_initial_loss
    starting = {key: value.detach().clone() for key, value in model.named_parameters()}
    history = list(state["history"]) if state is not None else []
    gradient_norms = list(state["gradient_norms"]) if state is not None else []
    backbone_gradient_norms = list(state["backbone_gradient_norms"]) if state is not None else []

    def save_progress(epoch):
        save_training_checkpoint(checkpoint, model, optimizer, config, versions,
                                 {"completed_epochs": epoch, "data_fingerprint": fingerprint,
                                  "initial_loss": initial_loss, "history": history,
                                  "gradient_norms": gradient_norms,
                                  "backbone_gradient_norms": backbone_gradient_norms}, scales=scales)

    model.train()
    for epoch in range(completed, epochs):
        optimizer.zero_grad(set_to_none=True)
        prediction = predict(model, batch, config, training=True)
        loss, _ = loss_for(prediction, batch, config, scales)
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("Nonfinite training loss")
        loss.backward()
        active = [p.grad for p in model.parameters() if p.grad is not None]
        if not active or not all(bool(torch.isfinite(g).all()) for g in active):
            raise FloatingPointError("Missing/nonfinite parameter gradients")
        gradient_norms.append(math.sqrt(sum(float(g.detach().square().sum()) for g in active)))
        backbone_grads = [p.grad for p in model.backbone.parameters() if p.grad is not None]
        backbone_gradient_norms.append(math.sqrt(sum(float(g.detach().square().sum()) for g in backbone_grads)))
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("clip_grad_norm", 10.))
        optimizer.step()
        history.append(float(loss.detach()))
        interval = config.get("checkpoint_every", 0)
        if interval and (epoch + 1) % interval == 0:
            save_progress(epoch + 1)
        if event_callback is not None:
            event_callback("epoch", epoch=epoch + 1, loss=history[-1])
    model.eval()
    predictions = predict(model, batch, config)
    final_loss = float(loss_for(predictions, batch, config, scales)[0].detach())
    delta = math.sqrt(sum(float((value.detach() - starting[key]).square().sum())
                          for key, value in model.named_parameters()))
    save_progress(epochs)
    reloaded = load_checkpoint(checkpoint, device=device)
    again = predict(reloaded, batch, config)
    for name in predictions:
        torch.testing.assert_close(again[name], predictions[name], rtol=1e-8, atol=1e-9)
        if not bool(torch.isfinite(predictions[name]).all()):
            raise FloatingPointError(f"Nonfinite predictions: {name}")
    records = []
    for structure in structures:
        raw = json.dumps({"z": structure.numbers.tolist(), "r": structure.positions.tolist(),
                          "cell": structure.cell.tolist()}, sort_keys=True).encode()
        records.append({"id": structure.identifier, "geometry_sha256": hashlib.sha256(raw).hexdigest(),
                        "provenance": structure.metadata, "role": "train_and_reloaded_inference"})
    report = {"config": config, "versions": version_record(), "execution": execution,
              "structures": records,
              "checkpoint": str(checkpoint), "completed_epochs": epochs,
              "segment_initial_loss": segment_initial_loss,
              "resume": {"path": str(resume) if resume else None,
                         "kind": "full" if state is not None else "weights_only" if saved is not None else "none",
                         "completed_epochs_before": completed},
              "initial_loss": initial_loss, "final_loss": final_loss, "history": history,
              "gradient_norms": gradient_norms, "backbone_gradient_norms": backbone_gradient_norms,
              "parameter_delta_norm": delta, "checkpoint_reload": True,
              "predictions": {name: value.detach().cpu().tolist() for name, value in predictions.items()},
              "interpretation": "execution/overfit check on training structures, not generalization",
              "passed": bool(history[completed:] and delta > 0 and max(backbone_gradient_norms[completed:], default=0) > 0
                             and math.isfinite(final_loss) and final_loss < initial_loss)}
    from universal_gnn.engine.derived import derived_outputs

    report["derived"] = derived_outputs(again, config["task"])
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError(f"Training acceptance failed; inspect {output / 'report.json'}")
    return report


def load_checkpoint(path: str | Path, *, device="cpu"):
    from universal_gnn.engine.runtime import checkpoint_config, verify_extensions

    saved = torch.load(path, map_location=device, weights_only=True)
    config = checkpoint_config(saved)
    model = build_model(config).to(device=device, dtype=torch.float64)
    verify_extensions(saved, model)
    model.load_state_dict(saved["state_dict"], strict=True)
    return model.eval()
