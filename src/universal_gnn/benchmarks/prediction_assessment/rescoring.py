"""Re-score saved test outputs against original dtype-bound source labels."""

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

from universal_gnn.engine.evaluation.metrics import BinaryClassificationMetrics, RegressionMetrics
from ..assessment.grouped import GroupedRegressionMetrics
from ..execution.gates import canonical_digest, file_sha
from ..preflight import write_json
from .contracts import SHAPES, compare, finite_shape, rounded, source_context, target_names, unchanged_source


def class_observation(logits, dtype):
    """Original score_partition computes softmax after detaching logits to CPU."""
    import torch
    values = torch.tensor(logits, device="cpu", dtype=getattr(torch, dtype))
    return float(torch.softmax(values, dim=-1)[0, 1]), int(values.argmax(-1)[0])


def rescore_saved(training_report, output, *, allow_legacy_classification=False):
    """No GNN load/forward. A full configured diagnostic split remains non-formal."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite a saved-label assessment")
    context = source_context(training_report)
    trained, config, task = (context[k] for k in ("trained", "config", "task"))
    names, held = target_names(task), trained["heldout"]
    output.mkdir(parents=True, exist_ok=False)
    tensor_groups = GroupedRegressionMetrics((3, 3)) if task == "dielectric" else None
    metrics = {}
    digest, count = hashlib.sha256(), 0
    atom_counts = dict(zip(context["ids"], context["natoms"]))
    with ExitStack() as stack:
        for name in names:
            metrics[name] = (stack.enter_context(BinaryClassificationMetrics(output / "scores.sqlite"))
                             if task == "classification" else RegressionMetrics())
        if task == "forcefield":
            metrics["energy_per_atom"] = RegressionMetrics()
        stream = stack.enter_context(Path(held["predictions"]).open("rb"))
        for raw in stream:
            digest.update(raw)
            row = json.loads(raw)
            if count >= len(context["test_ids"]) or row.get("id") != context["test_ids"][count]:
                raise ValueError("Saved test predictions omit/duplicate/reorder the frozen test IDs")
            identifier = row["id"]
            if set(row["predictions"]) != set(names) or set(row["targets"]) != set(names):
                raise ValueError("Saved test output names differ from the primary task")
            natoms = atom_counts[identifier]
            if row.get("natoms") != natoms or type(row.get("natoms")) is not int:
                raise ValueError("Saved atom count differs from the raw source")
            for name in names:
                shape = (natoms, 3) if name == "forces" else SHAPES[name]
                finite_shape(row["predictions"][name], shape)
                finite_shape(row["targets"][name], (1,) if name == "classification" else shape)
                compare(row["targets"][name], context["labels"][identifier][name], "raw_target", rtol=0, atol=0)
                if name == "classification":
                    probability, predicted_class = class_observation(row["predictions"][name], config["dtype"])
                    metrics[name].update(probability, row["targets"][name][0], predicted_class=predicted_class)
                else:
                    metrics[name].update(row["predictions"][name], context["labels"][identifier][name])
                if name == "total_energy":
                    prediction = rounded([[row["predictions"][name][0][0] / natoms]], config["dtype"])
                    target = rounded([[context["labels"][identifier][name][0][0] / natoms]], config["dtype"])
                    metrics["energy_per_atom"].update(prediction, target)
                if tensor_groups is not None:
                    tensor_groups.update(row["predictions"][name][0], context["labels"][identifier][name][0])
            count += 1
        if count != len(context["test_ids"]):
            raise ValueError("Saved test predictions omit declared test IDs")
        rescored = {name: accumulator.result() for name, accumulator in metrics.items()}
    if "energy_per_atom" in rescored:
        rescored["energy_per_atom"]["unit"] = "eV/atom"
    if set(rescored) != set(held["metrics"]):
        raise ValueError("Heldout metric output names differ")
    additional = []
    for name, actual in rescored.items():
        tolerance = dict(rtol=1e-5, atol=1e-6) if name == "energy_per_atom" else {}
        reference = held["metrics"][name]
        legacy_fields = {"balanced_accuracy", "balanced_accuracy_policy"}
        if (name == "classification" and allow_legacy_classification and
                set(reference) == set(actual) - legacy_fields):
            compare({key: actual[key] for key in reference}, reference, name, **tolerance)
            additional = sorted(legacy_fields)
        else:
            compare(actual, reference, name, **tolerance)
    unchanged_source(context, training_report)
    if file_sha(held["predictions"]) != digest.hexdigest():
        raise ValueError("Saved predictions changed during assessment")
    result = dict(status="passed", kind="saved_predictive_raw_label_assessment", task=task,
                  structures=count, source_structures=len(context["ids"]), metrics=rescored,
                  source_sha256=config["dataset"]["sha256"],
                  split_manifest_sha256=config["dataset"]["split_manifest_sha256"],
                  training_report_sha256=context["training_report_sha256"], config_sha256=canonical_digest(config),
                  prediction_sha256=digest.hexdigest(), best_checkpoint_sha256=held["selection"]["best_sha256"],
                  dtype=config["dtype"], formal_training_runs=0,
                  additional_legacy_classification_fields=additional,
                  per_atom_rescore_tolerance=dict(rtol=1e-5, atol=1e-6,
                      reason="CPU/GPU float32 division rounding; original raw E/F retain1e-12"),
                  scope="Complete configured saved test labels and physical-unit metrics; no model execution, normalized-loss re-score or formal-training claim")
    if tensor_groups is not None:
        result["tensor_groups"] = tensor_groups.result()
    write_json(output / "report.json", result)
    return result
