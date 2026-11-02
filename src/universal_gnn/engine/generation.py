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


def run_generation_training(config, output, *, resume=None, checkpoint_path=None, event_callback=None):
    import copy

    from universal_gnn.engine.runtime import (check_model_config, checkpoint_config, data_fingerprint,
                                               restore_optimizer, save_training_checkpoint)
    from universal_gnn.engine.training import (build_model, dataset, execution_record,
                                               load_checkpoint, version_record)

    config = copy.deepcopy(config)
    saved = torch.load(resume, map_location="cpu", weights_only=True) if resume else None
    if saved is not None:
        if saved.get("format_version", 1) == 1:
            config["task"].setdefault("adapter_version", 1)
        check_model_config(checkpoint_config(saved), config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    seed = config.get("seed", 123)
    torch.manual_seed(seed)
    device = config.get("device", "cpu")
    structures = dataset(config, config.get("structures", 10))
    fingerprint = data_fingerprint(structures)
    clean = StructureBatch.from_structures(structures).to(device)
    generator = torch.Generator(device=device).manual_seed(seed + 1)
    noisy, time, targets = corrupt(clean, generator=generator)
    model = build_model(config).to(device=device, dtype=torch.float64)
    if saved is not None:
        from universal_gnn.engine.runtime import verify_extensions

        verify_extensions(saved, model)
        model.load_state_dict(saved["state_dict"], strict=True)
    execution = execution_record(model)
    starting = {name: value.detach().clone() for name, value in model.named_parameters()}
    optimizer = torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", 1e-3))
    state = restore_optimizer(saved, optimizer, config, fingerprint) if saved is not None else None
    completed = state["completed_epochs"] if state is not None else 0
    epochs = config.get("epochs", 10)
    if epochs <= completed:
        raise ValueError(f"epochs is the total target; set it greater than the {completed} completed epochs")
    checkpoint = Path(checkpoint_path) if checkpoint_path is not None else output / "checkpoint.pt"
    versions = version_record()
    with torch.no_grad():
        segment_initial = float(score_loss(model.eval()(noisy, time), targets))
    initial = state["initial_loss"] if state is not None else segment_initial
    history = list(state["history"]) if state is not None else []
    gradient_norms = list(state["backbone_gradient_norms"]) if state is not None else []

    def save_progress(epoch):
        save_training_checkpoint(checkpoint, model, optimizer, config, versions,
                                 {"completed_epochs": epoch, "data_fingerprint": fingerprint,
                                  "initial_loss": initial, "history": history,
                                  "backbone_gradient_norms": gradient_norms})

    model.train()
    for epoch in range(completed, epochs):
        optimizer.zero_grad(set_to_none=True)
        loss = score_loss(model(noisy, time), targets)
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("Nonfinite denoising loss")
        loss.backward()
        active = [p.grad for p in model.parameters() if p.grad is not None]
        if not active or not all(bool(torch.isfinite(g).all()) for g in active):
            raise FloatingPointError("Missing/nonfinite denoising gradients")
        gradients = [p.grad for p in model.backbone.parameters() if p.grad is not None]
        gradient_norms.append(math.sqrt(sum(float(g.square().sum()) for g in gradients)))
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.get("clip_grad_norm", 10.))
        optimizer.step()
        history.append(float(loss.detach()))
        interval = config.get("checkpoint_every", 0)
        if interval and (epoch + 1) % interval == 0:
            save_progress(epoch + 1)
        if event_callback is not None:
            event_callback("epoch", epoch=epoch + 1, loss=history[-1])
    model.eval()
    with torch.no_grad():
        prediction = model(noisy, time)
        final = float(score_loss(prediction, targets))
    delta = math.sqrt(sum(float((p.detach() - starting[name]).square().sum())
                          for name, p in model.named_parameters()))
    save_progress(epochs)
    reloaded = load_checkpoint(checkpoint, device=device)
    with torch.no_grad():
        again = reloaded(noisy, time)
        for key in prediction:
            torch.testing.assert_close(prediction[key], again[key], rtol=1e-8, atol=1e-9)
    sampling = config["task"].get("sampling", {})
    generated = reloaded.sample(clean, **sampling)
    torch.testing.assert_close(generated.numbers, clean.numbers)
    fractional = fractional_coordinates(generated)
    valid = bool(torch.isfinite(generated.positions).all() and
                 (torch.linalg.det(generated.cell) > 0).all() and
                 ((fractional >= -1e-10) & (fractional < 1 + 1e-10)).all())
    report = {"config": config, "versions": version_record(), "execution": execution,
              "initial_loss": initial,
              "checkpoint": str(checkpoint), "completed_epochs": epochs, "segment_initial_loss": segment_initial,
              "resume": {"path": str(resume) if resume else None,
                         "kind": "full" if state is not None else "weights_only" if saved is not None else "none",
                         "completed_epochs_before": completed},
              "final_loss": final, "history": history, "backbone_gradient_norms": gradient_norms,
              "parameter_delta_norm": delta, "checkpoint_reload": True,
              "structures": [{"id": identifier, "provenance": metadata,
                              "role": "fixed_corruption_train_and_reloaded_inference"}
                             for identifier, metadata in zip(clean.identifiers, clean.metadata)],
              "corruption_sha256": hashlib.sha256(noisy.positions.cpu().numpy().tobytes() +
                                                   noisy.cell.cpu().numpy().tobytes()).hexdigest(),
              "predictions": {key: value.cpu().tolist() for key, value in again.items()},
              "generation": generated_record(generated),
              "interpretation": "fixed-corruption overfit and sampling execution; no quality/generalization claim",
              "passed": bool(history[completed:] and final < initial and delta > 0 and valid and
                             max(gradient_norms[completed:], default=0) > 0)}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError(f"Generation execution acceptance failed: {output / 'report.json'}")
    return report
