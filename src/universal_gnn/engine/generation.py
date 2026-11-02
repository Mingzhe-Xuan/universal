"""Small-data execution acceptance for periodic diffusion, without external labels."""

import hashlib
import json
import math
from pathlib import Path

import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.data.geometry import radius_graph
from universal_gnn.tasks.generation import corrupt, fractional_coordinates


def score_loss(prediction, targets):
    return sum((prediction[key] - target).square().mean() for key, target in targets.items())


def generated_record(batch):
    records = []
    for i, identifier in enumerate(batch.identifiers):
        start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
        records.append({"template_id": identifier, "numbers": batch.numbers[start:end].tolist(),
                        "positions": batch.positions[start:end].tolist(), "cell": batch.cell[i].tolist(),
                        "pbc": batch.pbc[i].tolist()})
    graph = radius_graph(batch, 2.)
    minimum = []
    for i in range(batch.num_graphs):
        distances = graph.distances[graph.edge_batch == i]
        minimum.append(float(distances.min()) if len(distances) else None)
    return {"structures": records, "volumes": torch.linalg.det(batch.cell).tolist(),
            "minimum_distance_below_2_angstrom": minimum}


def generation_batches(structures, config, *, epoch=None):
    from dataclasses import replace
    from universal_gnn.engine.batching import batch_indices, model_dtype

    for indices in batch_indices(structures, config, epoch=epoch):
        originals, corrupted, times = [], [], []
        targets = {"fractional_score": [], "cell_score": []}
        for index in indices:
            structure = structures[index]
            single = StructureBatch.from_structures([structure]).to(
                config.get("device", "cpu"), model_dtype(config))
            generator = torch.Generator(device=single.positions.device).manual_seed(config.get("seed", 123) + 1 + index)
            noisy, time, local_targets = corrupt(single, generator=generator)
            originals.append(structure)
            corrupted.append(replace(structure, positions=noisy.positions, cell=noisy.cell[0], graph=None))
            times.append(time)
            for key, value in local_targets.items():
                targets[key].append(value)
        clean = StructureBatch.from_structures(originals).to(config.get("device", "cpu"), model_dtype(config))
        yield clean, StructureBatch.from_structures(corrupted), torch.cat(times), {
            key: torch.cat(values) for key, values in targets.items()}


def run_generation_training(config, output, *, resume=None, checkpoint_path=None, event_callback=None):
    import copy

    from universal_gnn.engine.runtime import (check_model_config, checkpoint_config, data_fingerprint,
                                               restore_optimizer, save_training_checkpoint)
    from universal_gnn.engine.training import (build_model, dataset, execution_record,
                                               load_checkpoint, version_record)
    from universal_gnn.engine.batching import model_dtype, validate_batching
    from universal_gnn.engine.metrics import LossTotals, weighted_loss

    config = copy.deepcopy(config)
    saved = torch.load(resume, map_location="cpu", weights_only=True) if resume else None
    config.setdefault("dtype", saved["config"].get("dtype", "float64") if saved is not None else "float32")
    config.setdefault("generation_corruption", "per_structure_v1")
    validate_batching(config)
    if saved is not None:
        expected = checkpoint_config(saved)
        if expected["backbone"].get("implementation") == "legacy":
            config["backbone"].setdefault("implementation", "legacy")
        if saved.get("format_version", 1) == 1:
            config["task"].setdefault("adapter_version", 1)
        check_model_config(checkpoint_config(saved), config)
        if "training_state" in saved and "generation_corruption" not in saved["config"]:
            raise ValueError("Legacy fixed-batch generation requires a weights-only warm start; corruption convention changed")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(config.get("seed", 123))
    device = config.get("device", "cpu")
    structures = dataset(config)
    fingerprint = data_fingerprint(structures)
    model = build_model(config, official_artifact=saved.get("official_backbone") if saved else None).to(
        device=device, dtype=model_dtype(config))
    if saved is not None:
        from universal_gnn.engine.runtime import verify_extensions

        verify_extensions(saved, model)
        model.load_state_dict(saved["state_dict"], strict=True)
    execution = execution_record(model)
    starting = {name: value.detach().cpu().clone() for name, value in model.named_parameters()}
    optimizer = torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", 1e-3))
    state = restore_optimizer(saved, optimizer, config, fingerprint) if saved is not None else None
    completed = state["completed_epochs"] if state is not None else 0
    epochs = config.get("epochs", 10)
    if epochs <= completed:
        raise ValueError(f"epochs is the total target; set it greater than the {completed} completed epochs")
    checkpoint = Path(checkpoint_path) if checkpoint_path is not None else output / "checkpoint.pt"
    versions = version_record()

    def parts(prediction, targets):
        return {key: ((prediction[key] - target).square().sum(), target.numel()) for key, target in targets.items()}

    def evaluate(current):
        totals = LossTotals()
        current.eval()
        with torch.no_grad():
            for clean, noisy, time, targets in generation_batches(structures, config):
                totals.add(parts(current(noisy, time), targets))
        return totals.loss(config)

    segment_initial = evaluate(model)
    initial = state["initial_loss"] if state is not None else segment_initial
    history = list(state["history"]) if state is not None else []
    gradient_norms = list(state["backbone_gradient_norms"]) if state is not None else []

    def save_progress(epoch):
        save_training_checkpoint(checkpoint, model, optimizer, config, versions,
                                 {"completed_epochs": epoch, "data_fingerprint": fingerprint,
                                  "initial_loss": initial, "history": history,
                                  "backbone_gradient_norms": gradient_norms})

    for epoch in range(completed, epochs):
        model.train()
        totals, squared, steps = LossTotals(), 0., 0
        for clean, noisy, time, targets in generation_batches(structures, config, epoch=epoch):
            optimizer.zero_grad(set_to_none=True)
            values = parts(model(noisy, time), targets)
            loss = weighted_loss(values, config)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("Nonfinite denoising loss")
            loss.backward()
            active = [p.grad for p in model.parameters() if p.grad is not None]
            if not active or not all(bool(torch.isfinite(g).all()) for g in active):
                raise FloatingPointError("Missing/nonfinite denoising gradients")
            squared += sum(float(p.grad.detach().square().sum()) for p in model.backbone.parameters() if p.grad is not None)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("clip_grad_norm", 10.))
            optimizer.step()
            totals.add(values)
            steps += 1
        gradient_norms.append(math.sqrt(squared))
        history.append(totals.loss(config))
        interval = config.get("checkpoint_every", 0)
        if interval and (epoch + 1) % interval == 0:
            save_progress(epoch + 1)
        if event_callback is not None:
            event_callback("epoch", epoch=epoch + 1, loss=history[-1], minibatches=steps, structures=len(structures))
    model.eval()
    final = evaluate(model)
    delta = math.sqrt(sum(float((p.detach().cpu() - starting[name]).square().sum())
                          for name, p in model.named_parameters()))
    save_progress(epochs)
    reloaded = load_checkpoint(checkpoint, device=device)
    collected, generated_values, valid = {}, {}, True
    digest = hashlib.sha256()
    collect = config.get("report_predictions", len(structures) <= 1000)
    with torch.no_grad():
        for clean, noisy, time, targets in generation_batches(structures, config):
            prediction, again = model(noisy, time), reloaded(noisy, time)
            for key in prediction:
                tolerance = (1e-5, 1e-6) if model_dtype(config) == torch.float32 else (1e-8, 1e-9)
                torch.testing.assert_close(prediction[key], again[key], rtol=tolerance[0], atol=tolerance[1])
                if collect:
                    collected.setdefault(key, []).extend(again[key].cpu().tolist())
            digest.update(noisy.positions.cpu().numpy().tobytes() + noisy.cell.cpu().numpy().tobytes())
            if config.get("validate_sampling", True):
                generated = reloaded.sample(clean, **config["task"].get("sampling", {}))
                torch.testing.assert_close(generated.numbers, clean.numbers)
                fractional = fractional_coordinates(generated)
                tolerance = 1e-6 if model_dtype(config) == torch.float32 else 1e-10
                valid = valid and bool(torch.isfinite(generated.positions).all() and
                         (torch.linalg.det(generated.cell) > 0).all() and
                         ((fractional >= -tolerance) & (fractional < 1 + tolerance)).all())
                if collect:
                    for key, value in generated_record(generated).items():
                        generated_values.setdefault(key, []).extend(value)
    report = {"config": config, "versions": version_record(), "execution": execution,
              "initial_loss": initial, "selected_structures": len(structures), "available_structures": len(structures.source),
              "checkpoint": str(checkpoint), "completed_epochs": epochs, "segment_initial_loss": segment_initial,
              "resume": {"path": str(resume) if resume else None,
                         "kind": "full" if state is not None else "weights_only" if saved is not None else "none",
                         "completed_epochs_before": completed},
              "final_loss": final, "history": history, "backbone_gradient_norms": gradient_norms,
              "parameter_delta_norm": delta, "checkpoint_reload": True,
              "structures": [{"id": structure.identifier, "provenance": structure.metadata,
                              "role": "fixed_corruption_train_and_reloaded_inference"}
                             for structure in structures[:config.get("report_structure_limit", 1000)]],
              "structure_records_truncated": len(structures) > config.get("report_structure_limit", 1000),
              "data_fingerprint": fingerprint, "corruption_sha256": digest.hexdigest(),
              "predictions": collected, "predictions_included": bool(collect), "generation": generated_values,
              "interpretation": "per-structure fixed corruption; no quality/generalization claim",
              "passed": bool(history[completed:] and delta > 0 and valid and math.isfinite(final))}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError(f"Generation execution failed: {output / 'report.json'}")
    return report
