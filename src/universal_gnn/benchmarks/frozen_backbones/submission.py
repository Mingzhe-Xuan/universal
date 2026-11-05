"""Six managed stages per closed frozen case, using only original ready inputs."""

import hashlib
import os
from pathlib import Path
import shutil
import sys

from ..execution.gates import canonical_digest, file_sha, read_json
from ..preflight import write_json
from ..submission.dispatch import MANAGED, pair_lock, stage_kind, submit_stage, validate_submitted_job
from ..submission.planning import finite_budget, partition_maximum, request_script, slurm_duration
from ..supplemental_tensors.telemetry import checked_fields
from .execution import checked_execution_gate, execution_spec
from .telemetry import checked_preparation_terminals

LAUNCHES = Path("runs/arxiv-v1/frozen-launches")
DISPATCHES = Path("runs/arxiv-v1/frozen-dispatch")


def claim_path(item):
    root = LAUNCHES / item["case_id"]
    return root if item["phase"] == "train" else root / item["phase"]


def _stage(case, phase, args, seconds, *, depends_on=None, output=None):
    terminal = phase.startswith("terminal_")
    body = request_script(args, cpu_only=phase != "train")
    return dict(key=case["id"] + ":" + phase, case_id=case["id"], phase=phase, depends_on=depends_on,
        dependency_kind="afterany" if terminal else "afterok", script=body,
        request_sha256=hashlib.sha256(body.encode()).hexdigest(), output=output,
        resources=dict(partition="compute", node="node42", gpus=int(phase == "train"),
            cpus_per_task=2 if phase in {"train", "post"} else 1,
            memory_gib=64 if phase == "train" else 32 if phase == "post" else 8 if phase == "verify" else 1,
            time=slurm_duration(seconds), budget_seconds=seconds, nice=0 if terminal else 1000))


def build_frozen_submission_plan(settings, identifier, preparation, independent_gate, *, post_seconds=259200, verify_seconds=14400):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen planning/submission requires Slurm")
    spec = execution_spec(settings, identifier)
    case = spec["case"]
    if Path(sys.prefix).name != case["python_environment"]:
        raise ValueError("Use the original frozen provider environment")
    original = checked_preparation_terminals(settings, identifier, preparation, independent_gate)
    maximum = partition_maximum()
    for seconds in (post_seconds, verify_seconds):
        if type(seconds) is not int or seconds <= 0 or maximum is not None and seconds > maximum:
            raise ValueError("CPU budgets must be finite positive integers within partition limits")
    saved = read_json(independent_gate)
    gate = checked_execution_gate(settings, identifier, preparation, independent_gate, budget_seconds=saved["budget_seconds"])
    estimate = gate["probed_train_only_seconds"]
    budget = finite_budget(estimate, maximum)
    if budget != gate["budget_seconds"]:
        raise ValueError("Frozen training must retain its complete measured finite budget")
    commit = gate["git_commit"]
    settings = {key: str(value) for key, value in settings.items()}
    options = []
    for key, flag in (("definitions", "--definitions"), ("primary_matrix", "--primary-matrix")):
        if key in settings:options += [flag, settings[key]]
    post = "runs/arxiv-v1/frozen-postprocessing/" + identifier + "-" + commit[:7] + "-attempt-001"
    verify = "runs/arxiv-v1/frozen-acceptance/" + identifier + "-" + commit[:7] + "-attempt-001"
    stages = []
    for phase, seconds, output in (("train", budget, case["run_directory"]), ("post", post_seconds, post), ("verify", verify_seconds, verify)):
        args = [str(Path(sys.executable).absolute()), "scripts/run_frozen_case.py", phase, "--case", identifier] + options
        if phase == "train":
            args += ["--preparation", str(preparation), "--independent-gate", str(independent_gate), "--budget-seconds", str(budget)]
        else:
            args += ["--output", output]
            if phase == "verify":args += ["--postprocessing", post]
        item = _stage(case, phase, args, seconds, output=output,
                      depends_on=None if phase == "train" else identifier + (":train" if phase == "post" else ":post"))
        stages.append(item)
        receipt = claim_path(item) / "launch.json"
        args = [str(Path(sys.executable).absolute()), "scripts/record_tensor_terminal.py", "stage",
                "--receipt", str(receipt), "--stage-output", output]
        stages.append(_stage(case, "terminal_" + phase, args, 120, depends_on=item["key"], output=str(receipt.parent / "terminal.json")))
    if any(file_sha(path) != digest for path, digest in original["input_sha256"].items()):
        raise ValueError("Original frozen evidence changed during planning")
    provenance = dict(git_commit=commit, case_id=identifier, definitions=settings, original_preparation=original,
        python=str(Path(sys.executable).absolute()), preparation=str(preparation), independent_gate=str(independent_gate),
        gate=canonical_digest(gate), stages=[{k: v for k, v in item.items() if k != "script"} for item in stages])
    return dict(status="checked", kind="frozen_case_submission_plan", case_id=identifier, cases=[case], gate=gate,
        provenance=provenance, fingerprint=canonical_digest(provenance), stages=stages,
        probed_train_only_seconds=estimate, training_budget_seconds=budget, formal_training_runs_completed=0,
        interpretation="One full frozen train,two CPU scientific stages,three afterany recorders. Requests are not scientific completion.")


def checked_request_resources(receipt):
    fields = validate_submitted_job(receipt)
    resources = receipt["resources"]
    checked_fields(fields, job=receipt["job"], name="ugnn-" + stage_kind(receipt["phase"]) + "-" + receipt["case_id"],
        source=receipt["source_checkout"], cpus=resources["cpus_per_task"], memory=resources["memory_gib"],
        seconds=resources["budget_seconds"], gpus=resources["gpus"], token=receipt["submission_token"], nice=resources["nice"])
    if fields["JobState"] == "COMPLETED" and fields.get("ExitCode") != "0:0":
        raise ValueError("Known completed stage lacks a successful original exit")


def _existing(plan):
    receipts = {}
    for item in plan["stages"]:
        claim = claim_path(item)
        if claim.exists() or claim.is_symlink():
            if claim.is_symlink() or not (claim / "submission-intent.json").is_file() or not (claim / "launch.json").is_file():
                raise RuntimeError("Existing frozen claim is foreign or ambiguous; preserve it")
            intent = read_json(claim / "submission-intent.json")
            if intent.get("managed_by") != MANAGED or intent.get("fingerprint") != plan["fingerprint"]:
                raise RuntimeError("Existing frozen request provenance differs")
            if item["depends_on"] is not None and item["depends_on"] not in receipts:
                raise RuntimeError("Existing frozen child has no exact original parent receipt")
            receipt = submit_stage(plan, item, receipts, directory=claim, dependency_kind=item["dependency_kind"])
            checked_request_resources(receipt)
            receipts[item["key"]] = receipt
        elif Path(item["output"]).exists() or Path(item["output"]).is_symlink():
            raise FileExistsError("Unclaimed frozen output already exists")
    return receipts


def dispatch_frozen_case(settings, identifier, preparation, independent_gate, **options):
    plan = build_frozen_submission_plan(settings, identifier, preparation, independent_gate, **options)
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB free disk reserve before submission")
    root = DISPATCHES / identifier
    if root.is_symlink():
        raise FileExistsError("Foreign frozen dispatch symlink")
    root.mkdir(parents=True, exist_ok=True)
    with pair_lock(root):
        existing = _existing(plan)
        identity = root / "provenance.json"
        if identity.exists() and read_json(identity).get("fingerprint") != plan["fingerprint"]:
            raise RuntimeError("Frozen source/evidence differs from its original dispatch")
        write_json(identity, dict(fingerprint=plan["fingerprint"], provenance=plan["provenance"]))
        attempt = root / "attempts" / os.environ["SLURM_JOB_ID"]
        attempt.mkdir(parents=True, exist_ok=False)
        write_json(attempt / "plan.json", plan)
        report = dict(status="dispatching", case_id=identifier, fingerprint=plan["fingerprint"],
            parent_slurm_job=os.environ["SLURM_JOB_ID"], jobs={}, formal_training_runs_completed=0)
        try:
            for item in plan["stages"]:
                receipt = existing.get(item["key"])
                if receipt is None:
                    receipt = submit_stage(plan, item, report["jobs"], directory=claim_path(item), dependency_kind=item["dependency_kind"])
                    report["jobs"][item["key"]] = receipt
                    write_json(attempt / "report.json", report)
                    checked_request_resources(receipt)
                report["jobs"][item["key"]] = receipt
                write_json(attempt / "report.json", report)
            report.update(status="submitted", formal_training_jobs=1, scientific_cpu_jobs=2, terminal_recorders=3,
                newly_submitted_training_jobs=sum(not row["reused"] and row["phase"] == "train" for row in report["jobs"].values()),
                newly_submitted_jobs=sum(not row["reused"] for row in report["jobs"].values()),
                interpretation="Exact requests only; known receipts reused, unknown/foreign/purged claims stop. No scientific completion.")
            write_json(attempt / "report.json", report)
            write_json(root / "latest.json", dict(attempt=str(attempt), **report))
            return report
        except Exception as error:
            report.update(status="submission_failed", error_type=type(error).__name__, error=str(error))
            write_json(attempt / "report.json", report)
            raise
