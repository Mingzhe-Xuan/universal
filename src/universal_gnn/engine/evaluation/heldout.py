"""Opt-in validation selection and streamed test scoring for manifest partitions."""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil

from .selection import ValidationTracker


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_json(value):
    if isinstance(value, list):
        return [finite_json(item) for item in value]
    return None if isinstance(value, float) and not math.isfinite(value) else value


def candidate_path(path):
    path = Path(path)
    return path.with_name(path.stem + ".candidate" + path.suffix)


def verified_best(previous):
    path = Path(previous["best_checkpoint"])
    for candidate in (path, candidate_path(path)):
        if candidate.is_file() and file_sha256(candidate) == previous["best_sha256"]:
            return candidate
    raise ValueError("Resume requires the verified previous validation-best checkpoint")


class HoldoutEvaluation:
    def __init__(self, config, training, checkpoint, *, previous=None):
        from universal_gnn.data.indexed import SelectedStructures
        from universal_gnn.data.splits.loading import load_partition

        settings = config["dataset"]
        if settings.get("partition") != "train":
            raise ValueError("Training with hold-out evaluation requires dataset.partition=train")
        options = config.get("evaluation", {})
        if not isinstance(options, dict) or set(options) - {"patience", "min_delta"}:
            raise ValueError("evaluation accepts only patience and min_delta")
        source = training.source
        val_indices, manifest, digest = load_partition(source, settings, partition="validation")
        test_indices, _, _ = load_partition(source, settings, partition="test")
        self.validation = SelectedStructures(source, val_indices, training.bindings)
        self.test = SelectedStructures(source, test_indices, training.bindings)
        self.manifest = manifest
        self.tracker = ValidationTracker(digest, patience=options.get("patience"),
                                         min_delta=options.get("min_delta", 0.),
                                         state=previous["tracker"] if previous else None)
        checkpoint = Path(checkpoint)
        self.best_checkpoint = checkpoint.with_name(checkpoint.stem + ".best" + checkpoint.suffix).resolve()
        self.best_sha256 = None
        if previous:
            source_checkpoint = verified_best(previous)
            if source_checkpoint.resolve() != self.best_checkpoint:
                same_run_recovery = Path(previous["best_checkpoint"]).resolve() == self.best_checkpoint
                if self.best_checkpoint.exists() and not same_run_recovery:
                    raise FileExistsError(f"Refusing to overwrite {self.best_checkpoint}")
                self.best_checkpoint.parent.mkdir(parents=True, exist_ok=True)
                if same_run_recovery:
                    os.replace(source_checkpoint, self.best_checkpoint)
                else:
                    shutil.copyfile(source_checkpoint, self.best_checkpoint)
            self.best_sha256 = previous["best_sha256"]
        elif self.best_checkpoint.exists() or candidate_path(self.best_checkpoint).exists():
            raise FileExistsError(f"Refusing to overwrite existing best checkpoint: {self.best_checkpoint}")

    def update(self, epoch, validation_loss, model, optimizer, config, versions, scales):
        from universal_gnn.engine.runtime import save_training_checkpoint

        improved = self.tracker.update(epoch, validation_loss)
        if improved:
            candidate = candidate_path(self.best_checkpoint)
            save_training_checkpoint(candidate, model, optimizer, config, versions, None, scales=scales)
            self.best_sha256 = file_sha256(candidate)
        return improved

    def finalize_best(self):
        # Keep the old best until the atomic last checkpoint commits its new hash.
        # Either file can then satisfy recovery across a crash between the two renames.
        source = verified_best(self.snapshot())
        candidate = candidate_path(self.best_checkpoint)
        if source != self.best_checkpoint:
            os.replace(source, self.best_checkpoint)
        elif candidate.exists():
            candidate.unlink()

    def snapshot(self):
        return {"tracker": self.tracker.snapshot(), "best_checkpoint": str(self.best_checkpoint),
                "best_sha256": self.best_sha256}

    def score_test(self, model, config, scales, output):
        import torch
        from universal_gnn.engine.training import execution_record, version_record

        if self.best_sha256 is None or file_sha256(self.best_checkpoint) != self.best_sha256:
            raise ValueError("Validation-best artifact changed before test scoring")
        saved = torch.load(self.best_checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(saved["state_dict"], strict=True)
        model.eval()
        metadata = {"selection": self.snapshot(), "validation_structures": len(self.validation),
                    "test_structures": len(self.test), "source_structures": self.manifest["source_count"],
                    "declared_train_structures": len(self.manifest["partitions"]["train"]),
                    "source_sha256": self.manifest["source_sha256"],
                    "partition": "test", "checkpoint_role": "validation_best",
                    "execution": execution_record(model), "versions": version_record()}
        return score_partition(model, self.test, config, scales, output, metadata=metadata)


def make_holdout(config, training, checkpoint, *, state=None):
    if config["dataset"].get("split_manifest") is None:
        if "evaluation" in config or (state is not None and "evaluation" in state):
            raise ValueError("Held-out evaluation requires dataset.split_manifest")
        return None
    if state is not None and "evaluation" not in state:
        raise ValueError("Full resume lacks validation selection history; use a weights-only warm start")
    result = HoldoutEvaluation(config, training, checkpoint,
                               previous=state.get("evaluation") if state is not None else None)
    if state is not None and len(result.tracker.state["history"]) != state["completed_epochs"]:
        raise ValueError("Validation history does not match completed training epochs")
    return result


def score_partition(model, structures, config, scales, output, *, metadata=None):
    """One pass over held-out labels; preserve all predictions as JSONL on disk."""
    from contextlib import ExitStack
    import torch

    from universal_gnn.engine.batching import batches
    from universal_gnn.engine.metrics import is_classification, loss_parts, LossTotals
    from universal_gnn.engine.training import label, predict
    from universal_gnn.tasks.supervision import supervised_predictions
    from .metrics import BinaryClassificationMetrics, RegressionMetrics

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    classification = is_classification(config)
    totals, accumulators, count = LossTotals(), {}, 0
    with ExitStack() as stack:
        stream = stack.enter_context((output / "predictions.jsonl").open("x", encoding="utf-8"))
        for batch in batches(structures, config):
            predictions = predict(model, batch, config)
            totals.add(loss_parts(predictions, batch, config, scales))
            selected = supervised_predictions(predictions, config)
            targets = {name: label(batch, name, value, classification=classification)
                       for name, value in selected.items()}
            detached = {name: value.detach().cpu() for name, value in selected.items()}
            target_values = {name: value.detach().cpu() for name, value in targets.items()}
            for name in selected:
                if name not in accumulators:
                    if classification:
                        if selected[name].shape[-1] != 2:
                            raise ValueError("Held-out classification metrics currently require two classes")
                        accumulators[name] = stack.enter_context(BinaryClassificationMetrics(output / "scores.sqlite"))
                    else:
                        accumulators[name] = RegressionMetrics()
            for i, identifier in enumerate(batch.identifiers):
                record = {"id": identifier, "predictions": {}, "targets": {}}
                for name, value in detached.items():
                    atomic = name == "forces" or (config["task"]["kind"] == "supervised" and model.spec.scope == "node")
                    start, end = (int(batch.ptr[i]), int(batch.ptr[i + 1])) if atomic else (i, i + 1)
                    prediction, target = value[start:end], target_values[name][start:end]
                    if classification:
                        accumulators[name].update(float(torch.softmax(prediction, dim=-1)[0, 1]),
                                                  int(target[0]), predicted_class=int(prediction.argmax(-1)[0]))
                    else:
                        accumulators[name].update(prediction.tolist(), target.tolist())
                    record["predictions"][name] = prediction.tolist()
                    record["targets"][name] = finite_json(target.tolist())
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                count += 1
        if count != len(structures):
            raise RuntimeError("Held-out prediction count does not match its partition")
        result = {"structures": count, "normalized_loss": totals.loss(config),
                  "metrics": {name: accumulator.result() for name, accumulator in accumulators.items()},
                  "predictions": str(output / "predictions.jsonl"), "train_scales": copy.deepcopy(scales)}
        result.update(metadata or {})
        (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result
