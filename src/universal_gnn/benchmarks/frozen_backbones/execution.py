"""Closed eight-case full training, CPU post and independent saved-output acceptance."""

import json
import os
from pathlib import Path
import re
import sys

from ..execution.gates import compatible_sources, file_sha, read_json
from ..execution.runner import _run_prepared_case, verify_training_report
from ..prediction_assessment.contracts import compare
from ..prediction_assessment.runtime import _postprocess_case, _verify_case
from .contracts import DEFINITION_PATH, DEFINITION_SHA, PRIMARY_PATH, selected_case
from .readiness import check_frozen_preparation
from .training_audit import audited_training, check_training_audit


def execution_spec(settings, identifier):
    return selected_case(identifier, definitions=settings.get("definitions", DEFINITION_PATH),
                         primary=settings.get("primary_matrix", PRIMARY_PATH))


def checked_execution_gate(settings, identifier, preparation, independent_gate, *, budget_seconds):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen execution gates require Slurm")
    spec = execution_spec(settings, identifier)
    if Path(sys.prefix).name != spec["case"]["python_environment"]:
        raise ValueError("Use the original frozen provider Python environment")
    path = Path(independent_gate)
    digest = file_sha(path)
    saved = read_json(path)
    if (saved.get("status") != "passed" or saved.get("kind") != "formal_frozen_backbone_execution_gate" or
            saved.get("case") != spec["case"] or saved.get("definition_sha256") != DEFINITION_SHA or
            Path(saved.get("preparation", "")).resolve() != Path(preparation).resolve() or
            saved.get("budget_seconds") != budget_seconds):
        raise ValueError("Wait for the complete original independent frozen CUDA gate")
    compatible_sources([saved["git_commit"]])
    rebuilt = check_frozen_preparation(identifier, preparation,
        definitions=settings.get("definitions", DEFINITION_PATH), primary_path=settings.get("primary_matrix", PRIMARY_PATH),
        budget_seconds=budget_seconds)
    compare({k: v for k, v in rebuilt.items() if k != "git_commit"},
            {k: v for k, v in saved.items() if k != "git_commit"}, "independent_frozen_gate")
    if file_sha(path) != digest:
        raise ValueError("Independent frozen gate bytes changed during replay")
    return dict(rebuilt, independent_frozen_gate=dict(path=str(path), sha256=digest),
        execution_definitions=str(settings.get("definitions", DEFINITION_PATH)),
        execution_primary_matrix=str(settings.get("primary_matrix", PRIMARY_PATH)))


def verify_frozen_training(trained, gate, events):
    result = verify_training_report(trained, gate, events, frozen_backbone=True)
    return dict(result, frozen_training=check_training_audit(trained, gate))


def run_frozen_case(settings, identifier, preparation, independent_gate, *, budget_seconds):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen formal training requires Slurm")
    spec = execution_spec(settings, identifier)
    root = Path(spec["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to rerun or overwrite an existing frozen case")
    gate = checked_execution_gate(settings, identifier, preparation, independent_gate, budget_seconds=budget_seconds)
    return _run_prepared_case(identifier, gate, budget_seconds=budget_seconds,
        training_executor=audited_training, report_verifier=verify_frozen_training)


def frozen_context(settings, identifier):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen assessment requires Slurm")
    spec = execution_spec(settings, identifier)
    case = spec["case"]
    if Path(sys.prefix).name != case["python_environment"]:
        raise ValueError("Use the original frozen provider environment")
    root = Path(case["run_directory"])
    formal, trained = read_json(root / "formal-status.json"), read_json(root / "report.json")
    if (formal.get("status") != "passed" or formal.get("stage") != "complete" or
            formal.get("formal_training_runs_completed") != 1 or formal.get("case_id") != identifier or
            formal.get("matrix_sha256") != DEFINITION_SHA or formal.get("counts") != spec["counts"] or
            not isinstance(formal.get("slurm_job_id"), str) or
            not re.fullmatch(r"[1-9][0-9]*", formal["slurm_job_id"]) or
            trained.get("execution", {}).get("slurm", {}).get("SLURM_JOB_ID") != formal["slurm_job_id"] or
            any(formal.get(key) != case[key] for key in ("model", "task", "seed", "initialization"))):
        raise ValueError("Frozen formal execution identity or full coverage differs")
    original = read_json(root / "execution-gate.json")
    if (original.get("case") != case or original.get("kind") != "formal_frozen_backbone_execution_gate" or
            original.get("execution_definitions") != str(settings.get("definitions", DEFINITION_PATH)) or
            original.get("execution_primary_matrix") != str(settings.get("primary_matrix", PRIMARY_PATH))):
        raise ValueError("Original frozen execution used another definition or gate")
    gate = checked_execution_gate(settings, identifier, original["preparation"],
        original["independent_frozen_gate"]["path"], budget_seconds=original["budget_seconds"])
    compare({k: v for k, v in gate.items() if k != "git_commit"},
            {k: v for k, v in original.items() if k != "git_commit"}, "original_frozen_execution_gate")
    commit = compatible_sources([formal["git_commit"], trained["execution"]["git_commit"], original["git_commit"]])
    if read_json(root / "config.requested.json") != gate["config"]:
        raise ValueError("Frozen training changed its independently prepared original recipe")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf8").splitlines()]
    verified = verify_frozen_training(trained, gate, events)
    compare(formal.get("frozen_training"), verified["frozen_training"], "formal_frozen_state_evidence")
    for key in ("completed_epochs", "best_epoch", "test_structures", "best_checkpoint_sha256"):
        if formal.get(key) != verified[key]:
            raise ValueError("Frozen formal status differs from full training and heldout evidence")
    paths = [root / name for name in ("formal-status.json", "report.json", "execution-gate.json",
             "config.requested.json", "events.jsonl", "frozen-training-audit.json")]
    paths += [Path(trained["best_checkpoint"]), Path(trained["checkpoint"]), Path(trained["heldout"]["predictions"]),
        Path(trained["config"]["dataset"]["path"]), Path(trained["config"]["dataset"]["split_manifest"]),
        Path(original["preparation"]) / "report.json", Path(original["reference_preparation"]) / "report.json",
        Path(settings.get("definitions", DEFINITION_PATH)), Path(settings.get("primary_matrix", PRIMARY_PATH)),
        Path(original["independent_frozen_gate"]["path"])]
    return dict(spec=dict(spec, matrix_sha256=DEFINITION_SHA), gate=gate, trained=trained,
        report_path=root / "report.json", formal=formal, git_commit=commit, verified_training=verified,
        input_sha256={str(path): file_sha(path) for path in paths})


def postprocess_frozen_case(settings, identifier, output):
    return _postprocess_case(settings, identifier, output, context_loader=frozen_context)


def verify_frozen_case(settings, identifier, postprocessing, output):
    return _verify_case(settings, identifier, postprocessing, output, context_loader=frozen_context)
