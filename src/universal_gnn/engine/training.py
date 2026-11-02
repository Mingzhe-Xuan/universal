from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

import torch

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.contracts import StructureBatch
from universal_gnn.data.structures import bind_targets, load_structures
from universal_gnn.properties import property_spec
from universal_gnn.tasks import ForceFieldModel, SupervisedModel


def build_model(config):
    backbone_config = dict(config["backbone"])
    name = backbone_config.pop("name")
    backbone = make_backbone(name, **backbone_config)
    task = config["task"]
    if task["kind"] == "forcefield":
        return ForceFieldModel(backbone)
    if task["kind"] == "supervised":
        spec = property_spec(task["property"], channels=task.get("channels"), unit=task.get("unit"))
        return SupervisedModel(backbone, spec, route=task.get("route"))
    raise ValueError(f"Task kind not implemented: {task['kind']}")


def dataset(config, limit=10):
    structures = load_structures(config["dataset"]["path"])
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
    classification = config["task"].get("property") == "classification"
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


def run_training(config: dict, output: str | Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(config.get("seed", 123))
    device = config.get("device", "cpu")
    model = build_model(config).to(device=device, dtype=torch.float64)
    structures = dataset(config, config.get("structures", 10))
    batch = StructureBatch.from_structures(structures).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", 1e-3))
    model.eval()
    initial_predictions = predict(model, batch, config)
    initial_loss, scales = loss_for(initial_predictions, batch, config)
    initial_loss = float(initial_loss.detach())
    starting = {key: value.detach().clone() for key, value in model.named_parameters()}
    history = []
    gradient_norms = []
    backbone_gradient_norms = []
    model.train()
    for _ in range(config.get("epochs", 10)):
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
    model.eval()
    predictions = predict(model, batch, config)
    final_loss = float(loss_for(predictions, batch, config, scales)[0].detach())
    delta = math.sqrt(sum(float((value.detach() - starting[key]).square().sum())
                          for key, value in model.named_parameters()))
    checkpoint = output / "checkpoint.pt"
    torch.save({"config": config, "state_dict": model.state_dict(), "versions": version_record(),
                "scales": scales}, checkpoint)
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
    report = {"config": config, "versions": version_record(), "structures": records,
              "initial_loss": initial_loss, "final_loss": final_loss, "history": history,
              "gradient_norms": gradient_norms, "backbone_gradient_norms": backbone_gradient_norms,
              "parameter_delta_norm": delta, "checkpoint_reload": True,
              "predictions": {name: value.detach().cpu().tolist() for name, value in predictions.items()},
              "interpretation": "execution/overfit check on training structures, not generalization",
              "passed": bool(history and delta > 0 and max(backbone_gradient_norms, default=0) > 0
                             and math.isfinite(final_loss) and final_loss < initial_loss)}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError(f"Training acceptance failed; inspect {output / 'report.json'}")
    return report


def load_checkpoint(path: str | Path, *, device="cpu"):
    saved = torch.load(path, map_location=device, weights_only=True)
    model = build_model(saved["config"]).to(device=device, dtype=torch.float64)
    model.load_state_dict(saved["state_dict"], strict=True)
    return model.eval()
