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
from universal_gnn.tasks.supervision import supervised_outputs, supervised_predictions


def build_model(config, *, official_artifact=None):
    from universal_gnn.contracts.schema import validate_config

    validate_config(config)
    backbone_config = dict(config["backbone"])
    name = backbone_config.pop("name")
    declared_dim = backbone_config.pop("feature_dim", None)
    if official_artifact is not None:
        backbone_config["_artifact"] = official_artifact
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
    from universal_gnn.readouts.configuration import normalize_prediction
    from universal_gnn.engine.optimization import configure_optimization

    prediction = normalize_prediction(config, cutoff=getattr(backbone, "cutoff", None))
    if prediction is None and declared_dim is not None:
        from universal_gnn.contracts.components import resolve_feature_spec

        resolve_feature_spec(backbone, declared_dim)
    if task["kind"] == "forcefield":
        model = ForceFieldModel(backbone, prediction=prediction, feature_dim=declared_dim)
    elif task["kind"] == "supervised":
        spec = property_spec(task["property"], channels=task.get("channels"), unit=task.get("unit"),
                             definition=task.get("spec"))
        if prediction is not None and prediction["head_mode"] == "native":
            from universal_gnn.tasks.native import NativeTaskModel

            model = NativeTaskModel(backbone,spec,prediction=prediction,feature_dim=declared_dim)
        else:
            model = SupervisedModel(backbone, spec, route=task.get("route"),
                                    adapter_version=task.get("adapter_version", 2), prediction=prediction, feature_dim=declared_dim)
    else:
        raise ValueError(f"Task kind not implemented: {task['kind']}")
    configure_optimization(model, config)
    return model


def dataset(config, limit=None):
    from universal_gnn.data.indexed import SelectedStructures, open_structures
    from universal_gnn.engine.batching import model_dtype

    settings = config["dataset"]
    structures = open_structures(settings["path"], dtype=model_dtype(config), options=settings.get("options"))
    limit = config.get("structures") if limit is None else limit
    if limit == "all":
        limit = None
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
        raise ValueError("structures must be a positive integer, null or all")
    if limit is not None and len(structures) < limit:
        raise ValueError(f"Requested {limit} structures, found {len(structures)}")
    indices = range(len(structures))
    selection = settings.get("selection", "first")
    if selection not in {"first", "random"}:
        raise ValueError("dataset.selection must be first or random")
    if limit is not None:
        if selection == "random":
            generator = torch.Generator().manual_seed(settings.get("selection_seed", config.get("seed", 123)))
            indices = torch.randperm(len(structures), generator=generator)[:limit].tolist()
        else:
            indices = range(limit)
    if not len(indices):
        raise ValueError("Dataset must not be empty")
    bindings = settings.get("bindings")
    if config.get("task", {}).get("kind") == "forcefield" and bindings is not None:
        selected = supervised_outputs(config)
        bindings = {name: value for name, value in bindings.items() if name in selected}
    return SelectedStructures(structures, indices, bindings)


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
    for name, prediction in supervised_predictions(predictions, config).items():
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
    names = ["torch", "e3nn", "mace-torch", "nequip", "numpy", "ase", "alignn", "cgcnn",
             "matgl", "dgl", "jarvis-tools", "pymatgen", "torch-geometric", "torch-scatter", "torch-cluster"]
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
            "official": getattr(model.backbone, "load_report", None),
            "graph_builder": type(model.backbone.graph_builder).__name__ if hasattr(model.backbone, "graph_builder") else None,
            "extensions": getattr(model.backbone, "extension_provenance", {}),
            "geometry_basis_version": getattr(getattr(model, "adapter", None), "basis_version", None)}


def run_training(config: dict, output: str | Path, *, resume=None, checkpoint_path=None, event_callback=None,
                 warm_start=None, warm_start_components=("backbone",)) -> dict:
    from universal_gnn.contracts.schema import validate_config

    validate_config(config)
    if resume is not None and warm_start is not None:
        raise ValueError("resume and warm_start are mutually exclusive")
    if config["task"]["kind"] == "generation":
        if warm_start is not None:
            raise ValueError("Explicit component warm-start is not supported for generation")
        from universal_gnn.engine.generation import run_generation_training

        return run_generation_training(config, output, resume=resume, checkpoint_path=checkpoint_path,
                                       event_callback=event_callback)
    from universal_gnn.engine.runtime import (check_model_config, checkpoint_config, data_fingerprint,
                                               restore_optimizer, save_training_checkpoint)
    from universal_gnn.engine.batching import batches, model_dtype, validate_batching
    from universal_gnn.engine.metrics import dataset_scales, loss_parts, weighted_loss, LossTotals
    from universal_gnn.engine.optimization import (make_optimizer, resolved_model_config, component_audit,
                                                  verify_component_checkpoint, FrozenStateGuard)

    config = copy.deepcopy(config)
    saved = torch.load(resume, map_location="cpu", weights_only=True) if resume else None
    warm_saved = torch.load(warm_start, map_location="cpu", weights_only=True) if warm_start else None
    config.setdefault("dtype", saved["config"].get("dtype", "float64") if saved is not None else "float32")
    validate_batching(config)
    if saved is not None:
        expected = checkpoint_config(saved)
        if expected["backbone"].get("implementation") == "legacy":
            config["backbone"].setdefault("implementation", "legacy")
        if saved.get("format_version", 1) == 1:
            config["task"].setdefault("adapter_version", 1)
        check_model_config(checkpoint_config(saved), config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(config.get("seed", 123))
    device = config.get("device", "cpu")
    artifact = saved.get("official_backbone") if saved else None
    if warm_saved and "backbone" in warm_start_components:
        source_config = checkpoint_config(warm_saved)
        if source_config["backbone"]["name"] != config["backbone"]["name"]:
            raise ValueError("warm-start backbone model name differs")
        if (not config["backbone"].get("checkpoint") or
                config["backbone"].get("checkpoint") == source_config["backbone"].get("checkpoint")):
            artifact = warm_saved.get("official_backbone")
    model = build_model(config, official_artifact=artifact).to(
        device=device, dtype=model_dtype(config))
    if saved is not None:
        from universal_gnn.engine.runtime import verify_extensions

        verify_extensions(saved, model)
        model.load_state_dict(saved["state_dict"], strict=True)
        verify_component_checkpoint(saved, model, training=True)
    initialization = None
    if warm_start is not None:
        from universal_gnn.engine.warm_start import initialize_components

        initialization = initialize_components(model, warm_start, warm_start_components)
    frozen_state = FrozenStateGuard(model)
    config = resolved_model_config(config, model)
    execution = execution_record(model)
    optimizer = make_optimizer(model, config)
    structures = dataset(config)
    config = resolved_model_config(config, model, structure_count=len(structures))
    if "prediction" in config or "optimization" in config:
        (output / "config.resolved.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        if event_callback is not None:
            event_callback("model_resolved", config=config, components=component_audit(model))
    fingerprint = data_fingerprint(structures)
    state = restore_optimizer(saved, optimizer, config, fingerprint) if saved is not None else None
    completed = state["completed_epochs"] if state is not None else 0
    epochs = config.get("epochs", 10)
    if epochs <= completed:
        raise ValueError(f"epochs is the total target; set it greater than the {completed} completed epochs")
    checkpoint = Path(checkpoint_path) if checkpoint_path is not None else output / "checkpoint.pt"
    versions = version_record()
    scales = saved["scales"] if state is not None else dataset_scales(structures, config)

    def evaluate(current, *, compare=None, collect=False):
        totals, collected = LossTotals(), {}
        current.eval()
        for batch in batches(structures, config):
            values = predict(current, batch, config)
            totals.add(loss_parts(values, batch, config, scales))
            if compare is not None:
                other = predict(compare, batch, config)
                for name in values:
                    tolerance = (1e-5, 1e-6) if model_dtype(config) == torch.float32 else (1e-8, 1e-9)
                    torch.testing.assert_close(values[name], other[name], rtol=tolerance[0], atol=tolerance[1])
            if collect:
                for name, value in values.items():
                    collected.setdefault(name, []).append(value.detach().cpu())
        return totals.loss(config), {name: torch.cat(values) for name, values in collected.items()}

    segment_initial_loss, _ = evaluate(model)
    frozen_state.verify()
    initial_loss = state["initial_loss"] if state is not None else segment_initial_loss
    starting = {key: value.detach().cpu().clone() for key, value in model.named_parameters()}
    history = list(state["history"]) if state is not None else []
    gradient_norms = list(state["gradient_norms"]) if state is not None else []
    backbone_gradient_norms = list(state["backbone_gradient_norms"]) if state is not None else []
    training_components = None

    def save_progress(epoch):
        save_training_checkpoint(checkpoint, model, optimizer, config, versions,
                                 {"completed_epochs": epoch, "data_fingerprint": fingerprint,
                                  "initial_loss": initial_loss, "history": history,
                                  "gradient_norms": gradient_norms,
                                  "backbone_gradient_norms": backbone_gradient_norms}, scales=scales)

    for epoch in range(completed, epochs):
        model.train()
        if training_components is None:
            training_components = component_audit(model)
        totals, gradient_squared, backbone_squared, steps = LossTotals(), 0., 0., 0
        for batch in batches(structures, config, epoch=epoch):
            optimizer.zero_grad(set_to_none=True)
            prediction = predict(model, batch, config, training=True)
            parts = loss_parts(prediction, batch, config, scales)
            if not any(count for _, count in parts.values()):
                continue
            loss = weighted_loss(parts, config)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("Nonfinite training loss")
            frozen_state.verify()
            loss.backward()
            active = [p.grad for p in model.parameters() if p.grad is not None]
            if not active or not all(bool(torch.isfinite(g).all()) for g in active):
                raise FloatingPointError("Missing/nonfinite parameter gradients")
            gradient_squared += sum(float(g.detach().square().sum()) for g in active)
            from universal_gnn.engine.optimization import components

            backbone_squared += sum(float(p.grad.detach().square().sum()) for p in components(model)["backbone"].parameters()
                                    if p.grad is not None)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("clip_grad_norm", 10.))
            optimizer.step()
            totals.add(parts)
            steps += 1
        if not steps:
            raise ValueError("Epoch has no labelled minibatches")
        history.append(totals.loss(config))
        gradient_norms.append(math.sqrt(gradient_squared))
        backbone_gradient_norms.append(math.sqrt(backbone_squared))
        interval = config.get("checkpoint_every", 0)
        if interval and (epoch + 1) % interval == 0:
            save_progress(epoch + 1)
        if event_callback is not None:
            event_callback("epoch", epoch=epoch + 1, loss=history[-1], minibatches=steps,
                           structures=len(structures))
    model.eval()
    final_loss, _ = evaluate(model)
    frozen_state.verify()
    delta = math.sqrt(sum(float((value.detach().cpu() - starting[key]).square().sum())
                          for key, value in model.named_parameters()))
    save_progress(epochs)
    reloaded = load_checkpoint(checkpoint, device=device)
    collect = config.get("report_predictions", len(structures) <= 1000)
    _, predictions = evaluate(reloaded, compare=model, collect=collect)
    records = []
    for structure in structures[:config.get("report_structure_limit", 1000)]:
        raw = json.dumps({"z": structure.numbers.tolist(), "r": structure.positions.tolist(),
                          "cell": structure.cell.tolist()}, sort_keys=True).encode()
        records.append({"id": structure.identifier, "geometry_sha256": hashlib.sha256(raw).hexdigest(),
                        "provenance": structure.metadata, "role": "train_and_reloaded_inference"})
    report = {"config": config, "versions": version_record(), "execution": execution,
              "components": component_audit(model), "components_during_training": training_components,
              "initialization": initialization,
              "checkpoint_capability_updates": getattr(model, "_checkpoint_capability_updates", []),
              "supervised_outputs": list(supervised_outputs(config)),
              "structures": records, "selected_structures": len(structures),
              "available_structures": len(structures.source), "data_fingerprint": fingerprint,
              "structure_records_truncated": len(records) != len(structures),
              "checkpoint": str(checkpoint), "completed_epochs": epochs,
              "segment_initial_loss": segment_initial_loss,
              "resume": {"path": str(resume) if resume else None,
                         "kind": "full" if state is not None else "weights_only" if saved is not None else "none",
                         "completed_epochs_before": completed},
              "initial_loss": initial_loss, "final_loss": final_loss, "history": history,
              "gradient_norms": gradient_norms, "backbone_gradient_norms": backbone_gradient_norms,
              "parameter_delta_norm": delta, "checkpoint_reload": True,
              "predictions_included": bool(collect),
              "predictions": {name: value.tolist() for name, value in predictions.items()},
              "interpretation": "training metrics; no held-out generalization claim",
              "passed": bool(history[completed:] and delta > 0 and math.isfinite(final_loss))}
    from universal_gnn.engine.derived import derived_outputs

    report["derived"] = derived_outputs(predictions, config["task"]) if collect else {}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError(f"Training failed; inspect {output / 'report.json'}")
    return report


def load_checkpoint(path: str | Path, *, device="cpu"):
    from universal_gnn.engine.runtime import checkpoint_config, verify_extensions

    saved = torch.load(path, map_location=device, weights_only=True)
    config = checkpoint_config(saved)
    from universal_gnn.engine.batching import model_dtype

    model = build_model(config, official_artifact=saved.get("official_backbone")).to(
        device=device, dtype=model_dtype(config, legacy=True))
    verify_extensions(saved, model)
    model.load_state_dict(saved["state_dict"], strict=True)
    if saved.get("components") is not None:
        from universal_gnn.engine.optimization import verify_component_checkpoint

        verify_component_checkpoint(saved, model)
    return model.eval()
