"""Strict primary output formats and raw-source identity, without model imports."""

import copy
import hashlib
import json
import math
from pathlib import Path
import struct

from ..execution.gates import canonical_digest, file_sha, read_json
from universal_gnn.data.splits import validate_manifest

SHAPES = {"bandgap": (1, 1), "classification": (1, 2), "dielectric": (1, 3, 3),
          "spectrum": (1, 200), "total_energy": (1, 1), "stress": (1, 3, 3)}
UNITS = {"bandgap": "eV", "classification": "class", "dielectric": "dimensionless",
         "spectrum": "dataset_defined", "total_energy": "eV", "forces": "eV/angstrom"}


def finite_shape(value, shape):
    if not shape:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Prediction/label scalar must be finite numeric")
        return 1
    if not isinstance(value, list) or len(value) != shape[0]:
        raise ValueError("Prediction/label shape differs from the output contract")
    return sum(finite_shape(item, shape[1:]) for item in value)


def task_name(config):
    task = config["task"]
    name = "forcefield" if task.get("kind") == "forcefield" else task.get("property")
    if name not in {"forcefield", "bandgap", "classification", "dielectric", "spectrum"}:
        raise ValueError("Only the five primary predictive task formats are supported")
    if name != "forcefield" and task.get("kind") != "supervised":
        raise ValueError("Direct predictive outputs require a supervised task")
    if name == "forcefield" and task.get("supervised_outputs") != ["total_energy", "forces"]:
        raise ValueError("Primary forcefield assessment requires the original E+F outputs")
    return name


def target_names(task):
    return ("total_energy", "forces") if task == "forcefield" else (task,)


def rounded(value, dtype):
    if isinstance(value, list):
        return [rounded(item, dtype) for item in value]
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Raw primary labels must be finite numeric values")
    result = struct.unpack("f", struct.pack("f", value))[0] if dtype == "float32" else float(value)
    if not math.isfinite(result):
        raise ValueError("Raw primary label overflows the configured dtype")
    return result


def compare(actual, expected, name="metrics", *, rtol=1e-12, atol=1e-12):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(name + " keys differ")
        for key in expected:
            compare(actual[key], expected[key], name + "." + key, rtol=rtol, atol=atol)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(name + " length differs")
        for index, value in enumerate(expected):
            compare(actual[index], value, name + "." + str(index), rtol=rtol, atol=atol)
    elif type(expected) is float:
        if (type(actual) not in (int, float) or not math.isfinite(actual) or not math.isfinite(expected)
                or not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol)):
            raise ValueError(name + " numeric observation differs")
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(name + " observation differs")


def source_context(training_report):
    """Stream all source IDs and retain only heldout labels plus per-source atom counts."""
    path = Path(training_report)
    report_sha = file_sha(path)
    trained = read_json(path)
    config, held = trained["config"], trained["heldout"]
    task = task_name(config)
    if (not trained.get("passed") or config.get("structures") != "all" or
            config.get("max_atoms") is not None or config.get("dtype") not in {"float32", "float64"} or
            config["dataset"].get("partition") != "train" or held.get("partition") != "test" or
            held.get("checkpoint_role") != "validation_best"):
        raise ValueError("Require complete declared partitions and validation-best heldout outputs")
    settings = config["dataset"]
    names = target_names(task)
    bindings = settings.get("bindings", {})
    if set(bindings) != set(names):
        raise ValueError("Raw label bindings differ from the primary task")
    for name, binding in bindings.items():
        if (not isinstance(binding, dict) or set(binding) != {"key", "unit"} or
                not isinstance(binding["key"], str) or not binding["key"] or binding["unit"] != UNITS[name]):
            raise ValueError("Require explicit original raw key/unit bindings without transforms")
    manifest = read_json(settings["split_manifest"])
    validate_manifest(manifest, source_sha256=settings["sha256"], source_count=manifest["source_count"])
    if (canonical_digest(manifest) != settings["split_manifest_sha256"] or
            held.get("source_sha256") != settings["sha256"]):
        raise ValueError("Frozen source/manifest fingerprint differs")
    counts = manifest["counts"]
    for actual, expected in [(trained.get("selected_structures"), counts["train"]),
                             (held.get("declared_train_structures"), counts["train"]),
                             (held.get("validation_structures"), counts["validation"]),
                             (held.get("source_structures"), manifest["source_count"]),
                             (held.get("structures"), counts["test"]), (held.get("test_structures"), counts["test"])]:
        if actual != expected:
            raise ValueError("Training/heldout population differs from the complete declared split")
    if held["selection"]["tracker"]["manifest_sha256"] != settings["split_manifest_sha256"]:
        raise ValueError("Validation selection belongs to a different manifest")
    ids = [r["id"] for r in manifest["records"]]
    test_ids = [ids[i] for i in manifest["partitions"]["test"]]
    wanted, labels, natoms = set(test_ids), {}, []
    digest = hashlib.sha256()
    with Path(settings["path"]).open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw)
            index = len(natoms)
            if index >= len(ids) or row.get("id") != ids[index]:
                raise ValueError("Raw source ordered IDs differ from the frozen manifest")
            atoms = row.get("atoms", row)
            numbers = atoms.get("numbers", atoms.get("elements"))
            if not isinstance(numbers, list) or not numbers:
                raise ValueError("Source structure requires nonempty atoms")
            natoms.append(len(numbers))
            if row["id"] not in wanted:
                continue
            targets = {}
            for name in names:
                value = row["targets"][bindings[name]["key"]]
                if name == "classification":
                    if type(value) is not int or value not in (0, 1):
                        raise ValueError("Binary source label must be integer0/1")
                    targets[name] = [value]
                else:
                    if name in {"total_energy", "bandgap"}:
                        finite_shape(value, ())
                        value = [[value]]
                    elif name != "forces":
                        value = [value]
                    value = rounded(value, config["dtype"])
                    finite_shape(value, (len(numbers), 3) if name == "forces" else SHAPES[name])
                    targets[name] = value
            labels[row["id"]] = targets
    if len(natoms) != len(ids) or digest.hexdigest() != settings["sha256"]:
        raise ValueError("Complete raw source fingerprint/count differs")
    if file_sha(path) != report_sha:
        raise ValueError("Training report changed while reading raw source")
    return dict(trained=trained, config=config, task=task, manifest=manifest, ids=ids,
                natoms=natoms, labels=labels, test_ids=test_ids, training_report_sha256=report_sha)


def unchanged_source(context, training_report):
    settings = context["config"]["dataset"]
    if (file_sha(training_report) != context["training_report_sha256"] or
            file_sha(settings["path"]) != settings["sha256"] or
            canonical_digest(read_json(settings["split_manifest"])) != settings["split_manifest_sha256"]):
        raise ValueError("Original training report/source/split changed during assessment")


def full_inference_config(config):
    result = copy.deepcopy(config)
    result.pop("resolved_components", None)
    result["device"] = "cpu"
    for key in ("split_manifest", "split_manifest_sha256", "partition"):
        result["dataset"].pop(key, None)
    result["structures"] = "all"
    return result
