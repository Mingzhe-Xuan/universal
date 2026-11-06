"""No-model original-label re-score of the author's complete test1000 cohort."""

import hashlib
import json
from pathlib import Path

from universal_gnn.engine.evaluation.metrics import RegressionMetrics
from ...execution.gates import canonical_digest, file_sha
from ...prediction_assessment.contracts import compare, finite_shape, rounded, source_context, unchanged_source
from ...preflight import write_json
from ..source import COUNTS


def cohort_indices(manifest):
    indices = manifest.get("evaluation_cohorts", {}).get("official_test_01")
    if (manifest.get("counts") != COUNTS or len(manifest.get("records", [])) != 100000
            or any(len(manifest.get("partitions", {}).get(name, [])) != count for name, count in COUNTS.items())
            or not isinstance(indices, list) or len(indices) != 1000
            or any(type(i) is not int or not 0 <= i < 100000 for i in indices)
            or len(set(indices)) != 1000 or not set(indices) <= set(manifest["partitions"]["test"])
            or set(indices) & (set(manifest["partitions"]["train"]) | set(manifest["partitions"]["validation"]))):
        raise ValueError("Require the original1000 author test indices inside the complete99000 heldout")
    return indices


def rescore_author_cohort(training_report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    context = source_context(training_report)
    if context["task"] != "forcefield" or context["config"]["dtype"] != "float32":
        raise ValueError("Molecular author cohort retains the original float32 E+F protocol")
    indices = cohort_indices(context["manifest"])
    ids = [context["ids"][i] for i in indices]
    if len(set(ids)) != len(ids):
        raise ValueError("Original author cohort IDs must be unique")
    wanted, selected, digest = set(ids), {}, hashlib.sha256()
    path = Path(context["trained"]["heldout"]["predictions"])
    count = 0
    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            row = json.loads(raw)
            if count >= len(context["test_ids"]) or row.get("id") != context["test_ids"][count]:
                raise ValueError("Author metrics require the complete source-ordered99000 prediction stream")
            if row["id"] in wanted:
                selected[row["id"]] = row
            count += 1
    if count != len(context["test_ids"]) or set(selected) != wanted:
        raise ValueError("Incomplete99000 output or1000 author cohort")
    metrics = {name: RegressionMetrics() for name in ["total_energy", "forces", "energy_per_atom"]}
    atom_counts = {context["ids"][i]: context["natoms"][i] for i in indices}
    with (output / "predictions.jsonl").open("x", encoding="utf8", newline="\n") as stream:
        for identifier in ids:
            row = selected[identifier];natoms = atom_counts[identifier]
            if (type(row.get("natoms")) is not int or row["natoms"] != natoms
                    or set(row["predictions"]) != {"total_energy", "forces"}
                    or set(row["targets"]) != {"total_energy", "forces"}):
                raise ValueError("Author cohort E/F outputs or original atom counts differ")
            for name, shape in [("total_energy", (1, 1)), ("forces", (natoms, 3))]:
                finite_shape(row["predictions"][name], shape)
                finite_shape(row["targets"][name], shape)
                compare(row["targets"][name], context["labels"][identifier][name], "author_raw_target", rtol=0, atol=0)
                metrics[name].update(row["predictions"][name], context["labels"][identifier][name])
            metrics["energy_per_atom"].update(rounded([[row["predictions"]["total_energy"][0][0] / natoms]], "float32"),
                rounded([[context["labels"][identifier]["total_energy"][0][0] / natoms]], "float32"))
            stream.write(json.dumps(row, allow_nan=False) + "\n")
    unchanged_source(context, training_report)
    if file_sha(path) != digest.hexdigest():
        raise ValueError("Full heldout predictions changed during author cohort assessment")
    results = {name: accumulator.result() for name, accumulator in metrics.items()}
    results["energy_per_atom"]["unit"] = "eV/atom"
    result = dict(status="passed", kind="molecular_author_test01_saved_label_assessment", cohort="official_test_01",
        structures=len(ids), complete_heldout_structures=count, metrics=results, ordered_ids=ids,
        author_indices_sha256=canonical_digest(indices), full_prediction_sha256=digest.hexdigest(),
        prediction_sha256=file_sha(output / "predictions.jsonl"),
        source_sha256=context["config"]["dataset"]["sha256"],
        split_manifest_sha256=context["config"]["dataset"]["split_manifest_sha256"],
        training_report_sha256=context["training_report_sha256"], dtype="float32", formal_training_runs=0,
        model_execution_performed=False, interpretation="Original author1000 test order, full source E/F labels, same validation-best predictions. Correlated ethanol trajectory; no independent-trajectory/new-molecule or stress accuracy claim.")
    write_json(output / "report.json", result)
    return result
