"""Read only declared archive files and distinguish full runs from diagnostics."""

import hashlib
import copy
import json
from pathlib import Path

from ..prediction_assessment.contracts import compare, task_name
from ..prediction_assessment.runtime import verify_physics
from ..experiments.recipes import TASK_DATASETS
from ..experiments.registry import DATASETS


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not (root / relative).resolve().is_relative_to(root.resolve()):
        raise ValueError("Evidence path escaped its declared archive root")
    return root / relative


def leaves(tree, prefix=Path()):
    if not isinstance(tree, dict) or not tree:
        raise ValueError("Acceptance proof must declare a nonempty archive hash map")
    for name, value in tree.items():
        path = prefix / name
        if isinstance(value, dict):
            yield from leaves(value, path)
        elif isinstance(value, str) and len(value) == 64:
            yield path, value
        else:
            raise ValueError("Malformed archive hash entry")


class Inputs:
    def __init__(self):
        self.sha256 = {}

    def bind(self, path, expected=None):
        path = Path(path)
        digest = sha(path)
        if (expected is not None and digest != expected) or self.sha256.get(str(path), digest) != digest:
            raise ValueError("Declared acceptance evidence bytes changed")
        self.sha256[str(path)] = digest
        return path

    def read(self, path, expected=None):
        return json.loads(self.bind(path, expected).read_text(encoding="utf8"))

    def unchanged(self):
        for path, expected in self.sha256.copy().items():
            self.bind(path, expected)


def matching_training(report, identity, proof):
    if not isinstance(report, dict) or not {"config", "execution", "heldout", "completed_epochs"} <= set(report):
        return False
    config = report["config"]
    if identity["task"] == "generation":
        raise ValueError("Accepted generation proof requires its scientific quality schema adapter")
    source_sha, split = DATASETS[TASK_DATASETS[identity["task"]]]
    train, validation, test = split
    held = report["heldout"]
    return (report.get("passed") is True and config.get("seed") == 123 and config.get("structures") == "all"
        and config.get("max_atoms") is None and config.get("dtype") == "float32"
        and config.get("backbone", {}).get("name") == identity["model"]
        and config["backbone"].get("initialization") == identity["initialization"]
        and task_name(config) == identity["task"] and report["completed_epochs"] == proof["completed_epochs"]
        and config.get("dataset", {}).get("sha256") == source_sha
        and report.get("selected_structures") == held.get("declared_train_structures") == train
        and report.get("available_structures") == held.get("source_structures") == sum(split)
        and held.get("validation_structures") == validation and held.get("test_structures") == held.get("structures") == test)


def checked_metrics(actual, expected):
    if set(actual) != set(expected):
        raise ValueError("Acceptance and complete training metric names differ")
    for name in actual:
        compare(actual[name], expected[name], "accepted_metric." + name,
            **(dict(rtol=1e-5, atol=1e-6) if name == "energy_per_atom" else {}))


def legacy_mace_evidence(inputs, base, proof, trained):
    """The first historical proof predates embedding its separate993/1002 evidence."""
    case = "seed-123--forcefield--mace--pretrained"
    if proof.get("formal_case_id") != case or proof.get("formal_job") != "968":
        raise ValueError("Only the explicit first historical MACE proof uses this adapter")
    folder = base / "supplements/arxiv-v1"
    post = inputs.read(folder / "mace-full-postevaluation-993/report.json")
    physical = inputs.read(folder / "mace-full-postevaluation-993/trained-best-physics.json")
    verified = inputs.read(folder / "mace-inference-verification-1002/report.json")
    gates = inputs.read(base / "gates-verified.json")
    if (post.get("status") != "passed" or post.get("stage") != "complete" or post.get("case_id") != case
            or post.get("slurm_job_id") != "993" or post.get("test_ids_verified") != 164
            or post.get("best_checkpoint_sha256") != proof["best_checkpoint_sha256"]
            or post.get("training_commit") != trained["execution"]["git_commit"]
            or post.get("inference_structures") != 1566 or physical.get("passed") is not True
            or any(not row["passed"] for row in physical.get("checks", {}).values() if row["required"])
            or not physical.get("checks") or gates.get("mace993", {}).get("trained_best_cpu_physics") is not True
            or verified.get("status") != "passed" or verified.get("slurm_job_id") != "1002"
            or verified.get("structures") != 1566 or verified.get("all_ordered_ids_match_source") is not True
            or verified.get("completion_marker_verified") is not True
            or verified.get("prediction_sha256") != post.get("inference_prediction_sha256")
            or verified.get("prediction_bytes") != post.get("inference_prediction_bytes")
            or verified.get("source_sha256") != trained["config"]["dataset"]["sha256"]):
        raise ValueError("Historical MACE scientific post-processing/physics/inference binding differs")
    rescored = copy.deepcopy(post["rescored"])
    expected = proof["metrics"]["energy_per_atom"]
    if (set(rescored["energy_per_atom"]) == set(expected) - {"unit"} and expected.get("unit") == "eV/atom"
            and trained["config"]["dataset"]["bindings"]["total_energy"]["unit"] == "eV"):
        rescored["energy_per_atom"]["unit"] = "eV/atom"
    checked_metrics(rescored, proof["metrics"])
    verify_physics(physical, "forcefield", dict(ids=physical["structure_ids"]))
    compare(gates["inference1002"], verified, "legacy_independent_inference")
    return dict(cpu_postevaluation_cost=dict(wall_seconds=post["wall_seconds"], peak_process_rss_bytes=post["peak_process_rss_bytes"]),
        cpu_independent_verification_seconds=verified["wall_seconds"], source_format="legacy_968_plus_993_1002")


def accepted_case(inputs, base, row, identity):
    proof_path = inside(base, row["proof"])
    proof = inputs.read(proof_path)
    legacy = identity["case_id"] == "seed-123--forcefield--mace--pretrained" and "status" not in proof
    if not legacy and (proof.get("status") != "passed" or proof.get("scientific_postevaluation_verified") is not True):
        raise ValueError("Only independently accepted scientific cases enter the result table")
    if (proof.get("case_id", proof.get("formal_case_id")) != identity["case_id"]
            or str(proof.get("job", proof.get("formal_job"))) != str(row["job"])):
        raise ValueError("Index/proof case or original training job differs")
    candidates, statuses = {}, []
    for name, digest in leaves(proof["archived_sha256"]):
        path = inputs.bind(inside(proof_path.parent, name), digest)
        if path.name == "report.json":
            value = json.loads(path.read_text(encoding="utf8"))
            if matching_training(value, identity, proof):
                candidates.setdefault(digest, (path, value))
        elif path.name == "formal-status.json":
            value = json.loads(path.read_text(encoding="utf8"))
            if value.get("case_id") == identity["case_id"]:
                statuses.append(value)
    if len(candidates) != 1:
        raise ValueError("Require exactly one distinct declared full training report, never a diagnostic or conflict")
    training_path, trained = next(iter(candidates.values()))
    matching_statuses = [value for value in statuses if value.get("status") == "passed"
        and value.get("slurm_job_id") == str(row["job"]) and value.get("completed_epochs") == proof["completed_epochs"]]
    if not matching_statuses:
        raise ValueError("Missing original successful full formal status for the accepted case")
    for value in matching_statuses:
        for name, expected in proof["resource_costs"].items():
            if value.get(name) != expected:
                raise ValueError("Accepted resource costs differ from the original formal execution record")
    held = trained["heldout"]
    if (held.get("checkpoint_role") != "validation_best" or held.get("partition") != "test"
            or held.get("selection", {}).get("best_sha256") != proof["best_checkpoint_sha256"]
            or trained["execution"].get("slurm", {}).get("SLURM_JOB_ID") != str(row["job"])):
        raise ValueError("Actual validation-best full test or original job identity differs")
    checked_metrics(proof["metrics"], held["metrics"])
    extension = legacy_mace_evidence(inputs, base, proof, trained) if legacy else {}
    return proof, trained, dict(proof=str(proof_path), training_report=str(training_path), **extension)
