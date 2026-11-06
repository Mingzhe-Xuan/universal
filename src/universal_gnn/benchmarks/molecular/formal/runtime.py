"""Full original training and separate CPU scientific acceptance for all nine cases."""

import json
import os
from pathlib import Path

from ...execution.gates import check_artifact_identity, compatible_sources, file_sha, read_json
from ...execution.runner import _run_prepared_case, verify_training_report
from ...prediction_assessment.contracts import compare
from ...prediction_assessment.numerics import forbid_models
from ...prediction_assessment.runtime import _postprocess_case, _verify_case
from ...preflight import write_json
from ..contracts import DEFINITION_PATH, DEFINITION_SHA, PRIMARY_PATH
from .cohorts import rescore_author_cohort
from .contracts import selected_case
from .gates import check_execution_gate


def verify_molecular_training(trained, gate, events):
    spec = selected_case(gate["case"]["id"])
    if gate.get("kind") != "formal_molecular_execution_gate" or gate["case"] != spec["case"]:
        raise ValueError("Molecular training must retain its exact closed case")
    if spec["official"]:
        official = trained["execution"]["official"]
        coverage = 1. if spec["case"]["initialization"] == "pretrained" else 0.
        if official.get("buffer_coverage") != coverage:
            raise ValueError("Molecular whole-backbone buffer initialization coverage differs")
        check_artifact_identity(official, gate["native_graph"],
            read_json(PRIMARY_PATH)["registry"]["artifacts"][spec["model"]]["files"], spec["model"])
    return verify_training_report(trained, gate, events, plugin_backbone=not spec["official"])


def run_molecular_case(identifier, preparation, terminal, *, budget_seconds):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Molecular full training requires Slurm")
    spec = selected_case(identifier)
    root = Path(spec["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to rerun or overwrite a molecular case")
    gate = check_execution_gate(identifier, preparation, terminal, budget_seconds=budget_seconds)
    return _run_prepared_case(identifier, gate, budget_seconds=budget_seconds, report_verifier=verify_molecular_training)


def molecular_context(settings, identifier):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Molecular scientific assessment requires Slurm")
    spec = selected_case(identifier);case = spec["case"]
    root = Path(case["run_directory"])
    formal, trained = read_json(root / "formal-status.json"), read_json(root / "report.json")
    original = read_json(root / "execution-gate.json")
    if (formal.get("status") != "passed" or formal.get("stage") != "complete"
            or formal.get("formal_training_runs_completed") != 1 or formal.get("case_id") != identifier
            or formal.get("matrix_sha256") != DEFINITION_SHA or formal.get("counts") != spec["counts"]
            or trained["execution"]["slurm"].get("SLURM_JOB_ID") != formal.get("slurm_job_id")
            or any(formal.get(k) != case[k] for k in ["model", "task", "seed", "initialization"])):
        raise ValueError("Molecular original formal identity/complete training differs")
    gate = check_execution_gate(identifier, original["joint_preparation"], original["joint_terminal"],
        budget_seconds=original["budget_seconds"])
    compare({k: v for k,v in gate.items() if k != "git_commit"},
        {k: v for k,v in original.items() if k != "git_commit"}, "original_molecular_gate")
    if gate["config"] != read_json(root / "config.requested.json"):
        raise ValueError("Original molecular requested recipe changed")
    commit = compatible_sources([formal["git_commit"], trained["execution"]["git_commit"], original["git_commit"]])
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf8").splitlines()]
    verified = verify_molecular_training(trained, gate, events)
    for key in ["completed_epochs", "best_epoch", "test_structures", "best_checkpoint_sha256"]:
        if formal.get(key) != verified[key]:
            raise ValueError("Molecular formal status differs from complete original execution")
    paths = [root / name for name in ["formal-status.json", "report.json", "execution-gate.json", "config.requested.json", "events.jsonl"]]
    paths += [Path(trained["best_checkpoint"]), Path(trained["checkpoint"]), Path(trained["heldout"]["predictions"]),
        Path(trained["config"]["dataset"]["path"]), Path(trained["config"]["dataset"]["split_manifest"]), DEFINITION_PATH, PRIMARY_PATH]
    return dict(spec=dict(spec, matrix_sha256=DEFINITION_SHA), gate=gate, trained=trained,
        report_path=root / "report.json", formal=formal, git_commit=commit, verified_training=verified,
        input_sha256={**gate["input_sha256"], **{str(path): file_sha(path) for path in paths}})


def postprocess_molecular_case(identifier, output):
    report = _postprocess_case({}, identifier, output, context_loader=molecular_context)
    try:
        context = molecular_context({}, identifier)
        compare(context["input_sha256"], report["input_sha256"], "molecular_post_inputs")
        author = rescore_author_cohort(context["report_path"], Path(output) / "author-test01")
        report.update(author_test01=author, author_report_sha256=file_sha(Path(output) / "author-test01/report.json"))
        write_json(Path(output) / "report.json", report)
        return report
    except Exception as error:
        report.update(status="failed", stage="author_test01", error_type=type(error).__name__, error=str(error))
        write_json(Path(output) / "report.json", report)
        raise


def verify_molecular_case(identifier, postprocessing, output):
    report = _verify_case({}, identifier, postprocessing, output, context_loader=molecular_context)
    try:
        with forbid_models():
            context = molecular_context({}, identifier)
            compare(context["input_sha256"], report["input_sha256"], "molecular_independent_inputs")
            parent = read_json(Path(postprocessing) / "report.json")
            path = Path(postprocessing) / "author-test01/report.json"
            if file_sha(path) != parent["author_report_sha256"]:
                raise ValueError("Original author cohort assessment bytes changed")
            author = rescore_author_cohort(context["report_path"], Path(output) / "author-test01")
            compare(author, read_json(path), "independent_author_test01")
            compare(author, parent["author_test01"], "parent_author_test01")
        report.update(author_test01=author, author_report_sha256=file_sha(Path(output) / "author-test01/report.json"))
        write_json(Path(output) / "report.json", report)
        return report
    except Exception as error:
        report.update(status="failed", stage="independent_author_test01", error_type=type(error).__name__, error=str(error))
        write_json(Path(output) / "report.json", report)
        raise
