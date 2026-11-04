"""Full held-out denoising scores, distinct from sampled-structure quality."""

import json
from pathlib import Path


def score_denoising_test(holdout, model, config, output):
    import torch
    from universal_gnn.engine.evaluation.heldout import file_sha256
    from universal_gnn.engine.evaluation.metrics import RegressionMetrics
    from universal_gnn.engine.generation import denoising_parts, generation_batches
    from universal_gnn.engine.metrics import LossTotals
    from universal_gnn.engine.training import execution_record, version_record

    if holdout.best_sha256 is None or file_sha256(holdout.best_checkpoint) != holdout.best_sha256:
        raise ValueError("Validation-best checkpoint changed before generation test scoring")
    saved = torch.load(holdout.best_checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(saved["state_dict"], strict=True)
    model.eval()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    totals, metrics, count = LossTotals(), {}, 0
    with (output / "predictions.jsonl").open("x", encoding="utf-8") as stream, torch.no_grad():
        for clean, noisy, time, targets in generation_batches(holdout.test, config, phase="test"):
            prediction = model(noisy, time)
            totals.add(denoising_parts(prediction, targets))
            for i, identifier in enumerate(clean.identifiers):
                record = {"id": identifier, "noise_phase": "test", "predictions": {}, "targets": {}}
                for name, values in prediction.items():
                    start, end = (int(clean.ptr[i]), int(clean.ptr[i + 1])) if name == "fractional_score" else (i, i + 1)
                    predicted = values[start:end].cpu().tolist()
                    target = targets[name][start:end].cpu().tolist()
                    metrics.setdefault(name, RegressionMetrics()).update(predicted, target)
                    record["predictions"][name], record["targets"][name] = predicted, target
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                count += 1
        if count != len(holdout.test):
            raise RuntimeError("Denoising test did not cover its entire partition")
        result = {"partition": "test", "structures": count, "normalized_denoising_loss": totals.loss(config),
                  "metrics": {name: values.result() for name, values in metrics.items()},
                  "predictions": str(output / "predictions.jsonl"), "selection": holdout.snapshot(),
                  "validation_structures": len(holdout.validation), "source_structures": holdout.manifest["source_count"],
                  "declared_train_structures": holdout.manifest["counts"]["train"],
                  "source_sha256": holdout.manifest["source_sha256"],
                  "checkpoint_role": "validation_best", "execution": execution_record(model), "versions": version_record(),
                  "interpretation": "held-out denoising only; no sampled-structure quality or stability claim"}
        (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result
