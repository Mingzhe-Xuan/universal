"""Assess fixed validation thresholds on one complete saved CPU prediction stream."""

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

from ..execution.gates import file_sha
from ..prediction_assessment.contracts import source_context, unchanged_source
from ..prediction_assessment.rescoring import class_observation
from ..prediction_assessment.streaming import verify_inference_stream
from ...engine.evaluation.metrics import BinaryClassificationMetrics
from .selection import select_threshold, threshold_prediction


def _partition_scores(predictions, labels, dtype, digest):
    actual = hashlib.sha256()
    with Path(predictions).open("rb") as stream:
        for raw in stream:
            actual.update(raw)
            row = json.loads(raw)
            if row.get("type") == "prediction" and row["id"] in labels:
                score, argmax = class_observation(row["predictions"]["classification"], dtype)
                yield row["id"], score, labels[row["id"]], argmax
    if actual.hexdigest() != digest:
        raise ValueError("Prediction stream changed during partition scoring")


def assess_threshold(training_report, predictions, output, *, prediction_sha256, prediction_bytes):
    """No model load/forward; keep original metrics and all inputs unchanged."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite a classification assessment")
    context = source_context(training_report)
    if context["task"] != "classification":
        raise ValueError("Require a complete binary classification training report")
    trained, config, manifest = context["trained"], context["config"], context["manifest"]
    best = trained["best_checkpoint"]
    best_sha = trained["heldout"]["selection"]["best_sha256"]
    if file_sha(best) != best_sha:
        raise ValueError("Validation-best checkpoint differs")
    stream_evidence = verify_inference_stream(training_report, predictions,
        expected_sha256=prediction_sha256, expected_bytes=prediction_bytes)
    validation_ids = {context["ids"][i] for i in manifest["partitions"]["validation"]}
    validation_labels = {}
    binding = config["dataset"]["bindings"]["classification"]["key"]
    with Path(config["dataset"]["path"]).open("rb") as stream:
        for raw in stream:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row["id"] in validation_ids:
                value = row["targets"][binding]
                if type(value) is not int or value not in (0, 1):
                    raise ValueError("Validation source labels must be integer0/1")
                validation_labels[row["id"]] = value
    if set(validation_labels) != validation_ids or validation_ids & set(context["test_ids"]):
        raise ValueError("Validation/test membership differs from the frozen split")
    output.mkdir(parents=True, exist_ok=False)
    selection = select_threshold(
        ((identifier, score, target) for identifier, score, target, _ in
         _partition_scores(predictions, validation_labels, config["dtype"], prediction_sha256)),
        output / "validation-scores.sqlite")
    if selection["structures"] != len(validation_ids):
        raise ValueError("Incomplete validation prediction population")
    selection_path = output / "selection.json"
    selection_path.write_text(json.dumps(selection, indent=2, allow_nan=False), encoding="utf8")
    selection_sha = file_sha(selection_path)
    test_labels = {key: value["classification"][0] for key, value in context["labels"].items()}
    with ExitStack() as stack:
        chosen = stack.enter_context(BinaryClassificationMetrics(output / "selected-test-scores.sqlite"))
        original = stack.enter_context(BinaryClassificationMetrics(output / "argmax-test-scores.sqlite"))
        for _, score, target, argmax in _partition_scores(predictions, test_labels, config["dtype"], prediction_sha256):
            chosen.update(score, target, predicted_class=threshold_prediction(score, selection["rule"]))
            original.update(score, target, predicted_class=argmax)
        selected_metrics, argmax_metrics = chosen.result(), original.result()
    if selected_metrics["structures"] != len(context["test_ids"]):
        raise ValueError("Incomplete test prediction population")
    if selected_metrics["roc_auc"] != argmax_metrics["roc_auc"]:
        raise ValueError("A decision threshold must not change score-based AUROC")
    unchanged_source(context, training_report)
    if (file_sha(predictions) != prediction_sha256 or Path(predictions).stat().st_size != prediction_bytes or
            file_sha(best) != best_sha or file_sha(selection_path) != selection_sha):
        raise ValueError("Frozen predictions/checkpoint/selection changed")
    paths = [training_report, predictions, best, config["dataset"]["path"], config["dataset"]["split_manifest"]]
    result = dict(status="passed", kind="validation_selected_binary_threshold_assessment",
        prediction_source="same_complete_cpu_inference_stream_for_validation_and_test",
        formal_training_runs=0, model_execution_performed=False,
        validation_structures=len(validation_ids), test_structures=len(context["test_ids"]),
        source_structures=len(context["ids"]), selection=selection, selection_sha256=selection_sha,
        metrics=selected_metrics, same_stream_argmax_metrics=argmax_metrics,
        unchanged_original_heldout_metrics=trained["heldout"]["metrics"]["classification"],
        best_checkpoint_sha256=best_sha, dtype=config["dtype"], stream_evidence=stream_evidence,
        input_sha256={str(path): file_sha(path) for path in paths},
        interpretation="Validation-only threshold; fixed application to test. Original training argmax metrics retained. Both supplemental score sets use the same full CPU stream; no cross-device equality or new scientific acceptance inferred.")
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    return result
