"""Full supplemental execution after the separate closed sixteen-case gate."""

import json
import os
from pathlib import Path
import sys

from ..execution.gates import compatible_sources, file_sha, read_json
from ..execution.runner import _run_prepared_case, verify_training_report
from ..prediction_assessment.contracts import compare
from ..prediction_assessment.runtime import _postprocess_case, _verify_case
from .gate import (DEFINITION_PATH, DEFINITION_SHA, PRIMARY_PATH,
                   check_tensor_preparation, tensor_case_spec)


def selected_case(settings, identifier):
    definitions = settings.get("definitions", DEFINITION_PATH)
    primary = settings.get("primary_matrix", PRIMARY_PATH)
    if file_sha(definitions) != DEFINITION_SHA:
        raise ValueError("Original accepted supplemental definition bytes changed")
    return tensor_case_spec(read_json(primary), read_json(definitions), identifier)


def checked_pair_gate(settings, identifier, preparation, independent_gate, *, budget_seconds,
                      receipt_path=None):
    """Replay both immutable saved gates and independently rebuild the selected gate."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Supplemental execution checks must run through Slurm")
    spec = selected_case(settings, identifier)
    case = spec["case"]
    if Path(sys.prefix).name != case["python_environment"]:
        raise ValueError("Use the original provider Python environment")
    root = Path(independent_gate)
    parent_path = root / "report.json"
    parent_sha = file_sha(parent_path)
    parent = read_json(parent_path)
    if (parent.get("status") != "passed" or parent.get("stage") != "complete" or
            parent.get("kind") != "independent_supplemental_pair_preparation" or
            parent.get("definition_sha256") != DEFINITION_SHA or parent.get("pair_id") != case["pair_id"] or
            parent.get("seed") != 123 or parent.get("model") != case["model"] or parent.get("task") != case["task"] or
            parent.get("formal_training_runs") != 0 or parent.get("new_training_jobs") != 0 or
            parent.get("counts") != spec["counts"] or set(parent.get("gates", {})) != {"pretrained", "scratch"} or
            parent.get("budget_seconds") != budget_seconds):
        raise ValueError("Wait for the complete independently checked original supplemental pair")
    bindings = {str(parent_path): parent_sha}
    gates = {}
    for mode in ("pretrained", "scratch"):
        path = root / ("gate-" + mode + ".json")
        digest = file_sha(path)
        gate = read_json(path)
        entry = parent["gates"][mode]
        if (entry != dict(case_id=case["pair_id"] + "--" + mode, status="passed", sha256=digest) or
                gate.get("status") != "passed" or gate.get("kind") != "independent_supplemental_tensor_execution_gate" or
                gate.get("definition_sha256") != DEFINITION_SHA or
                gate.get("matrix_sha256") != DEFINITION_SHA or gate.get("case", {}).get("id") != entry["case_id"] or
                gate.get("case") != selected_case(settings, entry["case_id"])["case"] or
                gate.get("budget_seconds") != budget_seconds or gate.get("counts") != spec["counts"] or
                gate.get("common_batch_size") != parent.get("common_batch_size") or
                Path(gate.get("preparation", "")).resolve() != Path(preparation).resolve()):
            raise ValueError("Independent pair gate bytes/case/recipe/budget binding differs")
        bindings[str(path)] = digest
        gates[mode] = gate
    compatible_sources([parent["git_commit"], *(g["git_commit"] for g in gates.values())])
    rebuilt = check_tensor_preparation(settings.get("definitions", DEFINITION_PATH), identifier, preparation,
        budget_seconds=budget_seconds, primary_path=settings.get("primary_matrix", PRIMARY_PATH), receipt_path=receipt_path)
    saved = dict(gates[case["initialization"]])
    # Source commits may advance only when compatible_sources has proved that
    # the original model, graph, training and capacity code is unchanged.
    saved.pop("git_commit")
    compare({key: value for key, value in rebuilt.items() if key != "git_commit"}, saved, "rebuilt_independent_gate")
    if any(file_sha(path) != digest for path, digest in bindings.items()):
        raise ValueError("Independent pair evidence changed during execution checks")
    return dict(rebuilt, independent_pair_gate=dict(directory=str(root), input_sha256=bindings),
                execution_definitions=str(settings.get("definitions", DEFINITION_PATH)),
                execution_primary_matrix=str(settings.get("primary_matrix", PRIMARY_PATH)))


def run_tensor_case(settings, identifier, preparation, independent_gate, *, budget_seconds, receipt_path=None):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Supplemental training must run through Slurm")
    spec = selected_case(settings, identifier)
    root = Path(spec["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to rerun an existing supplemental case")
    gate = checked_pair_gate(settings, identifier, preparation, independent_gate,
                             budget_seconds=budget_seconds, receipt_path=receipt_path)
    return _run_prepared_case(identifier, gate, budget_seconds=budget_seconds)


def tensor_context(settings, identifier):
    """Rebuild the complete original gate and verify all saved training/test events."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Supplemental assessment must run through Slurm")
    spec = selected_case(settings, identifier)
    case = spec["case"]
    if Path(sys.prefix).name != case["python_environment"]:
        raise ValueError("Use the original provider Python environment")
    root = Path(case["run_directory"])
    formal_path, trained_path = root / "formal-status.json", root / "report.json"
    formal, trained = read_json(formal_path), read_json(trained_path)
    if (formal.get("status") != "passed" or formal.get("stage") != "complete" or
            formal.get("formal_training_runs_completed") != 1 or formal.get("case_id") != identifier or
            formal.get("matrix_sha256") != DEFINITION_SHA or formal.get("counts") != spec["counts"] or
            any(formal.get(key) != case[key] for key in ("model", "task", "seed", "initialization"))):
        raise ValueError("Supplemental formal execution identity/coverage differs")
    original_path = root / "execution-gate.json"
    original = read_json(original_path)
    if (original.get("case") != case or original.get("definition_sha256") != DEFINITION_SHA or
            original.get("kind") != "independent_supplemental_tensor_execution_gate" or
            original.get("execution_definitions") != str(settings.get("definitions", DEFINITION_PATH)) or
            original.get("execution_primary_matrix") != str(settings.get("primary_matrix", PRIMARY_PATH))):
        raise ValueError("Original execution used another supplemental definition or gate")
    gate = checked_pair_gate(settings, identifier, original["preparation"],
        original["independent_pair_gate"]["directory"], budget_seconds=original["budget_seconds"],
        receipt_path=original["preparation_receipt"]["receipt"])
    compare({key: value for key, value in gate.items() if key != "git_commit"},
            {key: value for key, value in original.items() if key != "git_commit"}, "original_execution_gate")
    commit = compatible_sources([formal["git_commit"], trained["execution"]["git_commit"], original["git_commit"]])
    if read_json(root / "config.requested.json") != gate["config"]:
        raise ValueError("Supplemental training changed its independently prepared recipe")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf8").splitlines()]
    verified = verify_training_report(trained, gate, events)
    paths = [formal_path, trained_path, original_path, root / "config.requested.json", root / "events.jsonl",
             Path(trained["best_checkpoint"]), Path(trained["checkpoint"]), Path(trained["heldout"]["predictions"]),
             Path(trained["config"]["dataset"]["path"]), Path(trained["config"]["dataset"]["split_manifest"]),
             Path(original["preparation"]) / "report.json", Path(settings.get("definitions", DEFINITION_PATH)),
             Path(settings.get("primary_matrix", PRIMARY_PATH))]
    bindings = {str(path): file_sha(path) for path in paths}
    bindings.update(gate["independent_pair_gate"]["input_sha256"])
    receipt = Path(gate["preparation_receipt"]["receipt"])
    for path in (receipt, receipt.parent / "terminal.json", receipt.parent / "request.sh"):
        bindings[str(path)] = file_sha(path)
    return dict(spec=spec, gate=gate, trained=trained, report_path=trained_path, formal=formal,
                git_commit=commit, verified_training=verified, input_sha256=bindings)


def postprocess_tensor_case(settings, identifier, output):
    return _postprocess_case(settings, identifier, output, context_loader=tensor_context)


def verify_tensor_case(settings, identifier, postprocessing, output):
    return _verify_case(settings, identifier, postprocessing, output, context_loader=tensor_context)
