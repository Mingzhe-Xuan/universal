"""Independent scalar re-score of every saved test prediction, without model loading."""

import json
import math
from pathlib import Path

from universal_gnn.data.preparation.qm9.conversion import write_json
from universal_gnn.data.preparation.qm9.source import digest
from .definitions import load_case


def scalar(value):
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Require one finite scalar per QM9 prediction/target")
    return value


def assess(definitions, identifier):
    case = load_case(definitions, identifier)
    folder = Path(case["run_directory"])
    report = json.loads((folder / "report.json").read_bytes())
    held = report["heldout"]
    prop = case["property"]
    settings = case["config"]["dataset"]
    config = report["config"]
    if (config["task"] != case["config"]["task"] or config["dataset"] != settings
            or config["backbone"]["name"] != case["model"]
            or config["backbone"]["initialization"] != case["initialization"]
            or config["structures"] != "all" or config["seed"] != 123):
        raise ValueError("QM9 training report belongs to a different experiment")
    if digest(settings["path"]) != settings["sha256"]:
        raise ValueError("QM9 data changed after training")
    manifest = json.loads(Path(settings["split_manifest"]).read_bytes())
    from universal_gnn.data.splits.manifest import validate_manifest
    from .definitions import canonical
    validate_manifest(manifest, source_sha256=settings["sha256"], source_count=130831)
    if canonical(manifest) != settings["split_manifest_sha256"]:
        raise ValueError("QM9 split changed")
    if (report["selected_structures"] != manifest["counts"]["train"]
            or held["structures"] != manifest["counts"]["test"]):
        raise ValueError("QM9 report does not cover the complete declared partitions")
    indices = set(manifest["partitions"]["test"])
    targets, ids = {}, []
    with Path(settings["path"]).open() as stream:
        for i, line in enumerate(stream):
            if i in indices:
                row = json.loads(line);ids.append(row["id"]);targets[row["id"]] = row["targets"][prop]
    absolute, squared, count = 0., 0., 0
    seen = []
    with Path(held["predictions"]).open() as stream:
        for line in stream:
            row = json.loads(line);name = row["id"]
            if count >= len(ids) or name != ids[count]:
                raise ValueError("QM9 test predictions missing/reordered/duplicated")
            prediction, target = scalar(row["predictions"][prop]), scalar(row["targets"][prop])
            if not math.isclose(target, targets[name], rel_tol=2e-6, abs_tol=1e-7):
                raise ValueError("Saved QM9 target differs from original label")
            error = prediction - target
            absolute += abs(error);squared += error * error;count += 1;seen.append(name)
    if count != len(ids) or held["checkpoint_role"] != "validation_best":
        raise ValueError("Require the complete validation-best QM9 test stream")
    metrics = dict(mae=absolute/count, rmse=math.sqrt(squared/count))
    for name, value in metrics.items():
        if not math.isclose(value, held["metrics"][prop][name], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Independent QM9 scalar metrics disagree")
    if digest(report["best_checkpoint"]) != held["selection"]["best_sha256"]:
        raise ValueError("QM9 best checkpoint changed after held-out selection")
    result = dict(status="passed", case_id=identifier, structures=count, metrics=metrics,
                  model_execution=False, report_sha256=digest(folder / "report.json"),
                  predictions_sha256=digest(held["predictions"]), dataset_sha256=settings["sha256"],
                  best_checkpoint_sha256=held["selection"]["best_sha256"])
    write_json(folder / "independent-assessment.json", result)
    status = json.loads((folder / "formal-status.json").read_bytes())
    status.update(status="passed", independent_assessment_sha256=digest(folder / "independent-assessment.json"))
    write_json(folder / "formal-status.json", status)
    return result
