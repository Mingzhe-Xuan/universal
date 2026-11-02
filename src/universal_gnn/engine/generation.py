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


def run_generation_training(config, output):
    from universal_gnn.engine.training import (build_model, dataset, execution_record,
                                               load_checkpoint, version_record)

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    seed = config.get("seed", 123)
    torch.manual_seed(seed)
    device = config.get("device", "cpu")
    clean = StructureBatch.from_structures(dataset(config, config.get("structures", 10))).to(device)
    generator = torch.Generator(device=device).manual_seed(seed + 1)
    noisy, time, targets = corrupt(clean, generator=generator)
    model = build_model(config).to(device=device, dtype=torch.float64)
    execution = execution_record(model)
    starting = {name: value.detach().clone() for name, value in model.named_parameters()}
    optimizer = torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", 1e-3))
    with torch.no_grad():
        initial = float(score_loss(model.eval()(noisy, time), targets))
    history, gradient_norms = [], []
    model.train()
    for _ in range(config.get("epochs", 10)):
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
    model.eval()
    with torch.no_grad():
        prediction = model(noisy, time)
        final = float(score_loss(prediction, targets))
    delta = math.sqrt(sum(float((p.detach() - starting[name]).square().sum())
                          for name, p in model.named_parameters()))
    checkpoint = output / "checkpoint.pt"
    torch.save({"format_version": 2, "config": config, "state_dict": model.state_dict(),
                "versions": version_record()}, checkpoint)
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
              "passed": bool(history and final < initial and delta > 0 and valid and
                             max(gradient_norms, default=0) > 0)}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError(f"Generation execution acceptance failed: {output / 'report.json'}")
    return report
