"""Closed frozen definitions and strict single-probe state/capacity receipts."""

import copy
import math
from pathlib import Path
import re

from ..execution.gates import canonical_digest, file_sha, read_json
from ..probes.schedule import schedule_settings
from .definitions import build_frozen_definitions
from .worker import PROTOCOL

DEFINITION_PATH = Path("runs/frozen-definition-control-1288/definitions/definitions.json")
DEFINITION_SHA = "e6104992bc86dfbbc0bdc67b9d20105f79dcb5ba95dc3fabbdac7ef708c4b8f0"
PRIMARY_PATH = Path("runs/arxiv-v1/definition-947/matrix.json")


def frozen_case_spec(primary, definitions, identifier):
    expected = build_frozen_definitions(primary)
    actual = {key: value for key, value in definitions.items() if key != "full_input_audit"}
    if actual != expected:
        raise ValueError("Require all eight exact original frozen ablation definitions")
    cases = [case for case in expected["cases"] if case["id"] == identifier]
    if len(cases) != 1:
        raise ValueError("Select one of the eight original seed123 pretrained frozen cases")
    case = copy.deepcopy(cases[0])
    return dict(case=case, config=case["config"], counts=case["counts"], source_structures=case["source_structures"],
                primary_sha256=expected["primary_matrix_sha256"], definition_sha256=DEFINITION_SHA)


def selected_case(identifier, *, definitions=DEFINITION_PATH, primary=PRIMARY_PATH):
    if file_sha(definitions) != DEFINITION_SHA:
        raise ValueError("Accepted frozen definition file bytes changed")
    return frozen_case_spec(read_json(primary), read_json(definitions), identifier)


def frozen_config(spec, reference_gate):
    case = spec["case"]
    if (reference_gate.get("status") != "passed" or reference_gate["case"]["id"] != case["reference_finetune_case"] or
            reference_gate["counts"] != spec["counts"] or reference_gate["source_structures"] != spec["source_structures"] or
            reference_gate["matrix_sha256"] != spec["primary_sha256"]):
        raise ValueError("Frozen ablation requires the exact original complete finetune reference gate")
    actual = copy.deepcopy(reference_gate["config"])
    actual["optimization"]["train_backbone"] = False
    expected = copy.deepcopy(spec["config"])
    expected["batch_size"] = reference_gate["common_batch_size"]
    if actual != expected:
        raise ValueError("Frozen training may change only the backbone optimization flag at the matched reference batch")
    return actual


def checked_audit(audit, steps, *, instrumentation_sha256, delegate_sha256):
    if (not isinstance(audit, dict) or audit.get("protocol") != PROTOCOL or
            audit.get("optimizer_steps") != steps or audit.get("guard_checks") != 2 * steps + 2 or
            audit.get("backbone_optimizer_parameters") != 0 or audit.get("backbone_requires_grad_parameters") != 0 or
            any(audit.get(key) is not True for key in ("backbone_gradients_absent", "frozen_modules_eval",
                "state_exact_after_every_step", "readout_parameters_changed")) or
            any(audit.get(key) is not False for key in ("changed_optimizer_arithmetic", "changed_rng")) or
            audit.get("instrumentation_source_sha256") != instrumentation_sha256 or
            audit.get("delegate_source_sha256") != delegate_sha256):
        raise ValueError("Missing exact frozen state/optimizer/source evidence for every actual step")
    for key in ("backbone_state_before_sha256", "backbone_state_after_sha256", "readout_state_before_sha256",
                "readout_state_after_sha256", "readout_parameters_before_sha256", "readout_parameters_after_sha256"):
        if not isinstance(audit.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", audit[key]):
            raise ValueError("Frozen state/parameter fingerprints are missing")
    if (audit["backbone_state_before_sha256"] != audit["backbone_state_after_sha256"] or
            audit["readout_parameters_before_sha256"] == audit["readout_parameters_after_sha256"] or
            "backbone" in audit.get("optimizer_groups", []) or "readout" not in audit.get("optimizer_groups", [])):
        raise ValueError("Backbone state changed or readout parameters did not train")
    low, high = audit.get("minimum_readout_gradient_norm"), audit.get("maximum_readout_gradient_norm")
    if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in (low, high)) or high < low:
        raise ValueError("Frozen probe readout gradients must remain finite and positive")
    return audit


def frozen_capacity(directory, config, probe, counts):
    """Audit the existing disposable preflight schema; never fake an init pair."""
    directory = Path(directory)
    report = read_json(directory / "report.json")
    common = config["batch_size"]
    if (report.get("version") != 1 or report.get("status") != "passed" or report.get("passed") is not True or
            report.get("phase") != "train" or report.get("config") != config or report.get("probe") != probe or
            report.get("initial_batch_size") != common or report.get("final_batch_size") != common or
            report.get("effective_batch_size") != common or report.get("gradient_accumulation_steps") != 1):
        raise ValueError("Frozen capacity must fit the matched original reference batch without changing the recipe")
    attempts = report.get("attempts", [])
    if len(attempts) != 1:
        raise ValueError("Reduced exploratory batches cannot qualify a one-flag frozen comparison")
    attempt = attempts[0]
    path = directory / ("attempt-01-b" + str(common))
    request = read_json(path / "request.json")
    worker = read_json(path / "result.json")
    if (Path(attempt.get("directory", "")).resolve() != path.resolve() or attempt.get("batch_size") != common or
            attempt.get("returncode") != 0 or attempt.get("status") != "passed" or attempt.get("worker") != worker or
            request != dict(config=config, probe=probe, phase="train")):
        raise ValueError("Frozen attempt/request/worker receipt identity changed")
    schedule = schedule_settings(probe, common)
    measured, warmup = schedule["measure_batches"], schedule["warmup_batches"]
    if (worker.get("version") != 1 or worker.get("status") != "passed" or worker.get("stage") != "complete" or
            worker.get("phase") != "train" or worker.get("batch_size") != common or
            worker.get("selected_training_structures") != counts["train"] or
            worker.get("measured_batches") != measured or measured < 100 or
            worker.get("measured_structures") != measured * common or worker.get("coverage") != probe["coverage"] or
            worker.get("completed_worst_indices") != probe.get("worst_indices", probe["indices"]) or
            worker.get("all_declared_worst_cases_completed") is not True or
            worker.get("worst_case_policy") != "homogeneous_full_batch_v1" or
            type(worker.get("elapsed_seconds")) not in (int, float) or
            not math.isfinite(worker["elapsed_seconds"]) or worker["elapsed_seconds"] <= 0):
        raise ValueError("Frozen probe must complete all100 matched-size worst and ordinary training batches")
    instrumentation = Path(__file__).with_name("worker.py")
    delegate = Path(__file__).parents[1] / "probe_worker.py"
    checked_audit(worker.get("frozen_audit"), measured + warmup,
                  instrumentation_sha256=file_sha(instrumentation), delegate_sha256=file_sha(delegate))
    return dict(status="passed", common_batch_size=common, worker=worker,
                report_sha256=file_sha(directory / "report.json"), worker_sha256=file_sha(path / "result.json"),
                request_sha256=file_sha(path / "request.json"), seconds_per_batch=worker["elapsed_seconds"] / measured)
