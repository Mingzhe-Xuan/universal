"""Closed16 supplemental cases with independent gates and exact managed requests."""

import hashlib
import os
from pathlib import Path
import shutil
import sys

from ..execution.gates import canonical_digest, file_sha, read_json
from ..preflight import write_json
from ..submission.dispatch import MANAGED, pair_lock, stage_kind, submit_stage, validate_submitted_job
from ..submission.planning import finite_budget, measured_train_estimate, partition_maximum, request_script, slurm_duration
from .execution import checked_pair_gate, selected_case
from .telemetry import checked_fields, checked_gate_terminal

LAUNCHES = Path("runs/arxiv-v1/supplemental-launches")
DISPATCHES = Path("runs/arxiv-v1/supplemental-dispatch")


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


def build_tensor_submission_plan(settings, pair, preparation, independent_gate, *, post_seconds=259200, verify_seconds=14400):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Supplemental pair submission must run through Slurm")
    specs = [selected_case(settings, pair + "--" + mode) for mode in ("pretrained", "scratch")]
    cases = [spec["case"] for spec in specs]
    if (any(case["pair_id"] != pair or case["seed"] != 123 for case in cases) or
            Path(sys.prefix).name != cases[0]["python_environment"]):
        raise ValueError("Require one registered seed123 pair in its original provider environment")
    original_terminal = checked_gate_terminal(settings, pair, independent_gate)
    maximum = partition_maximum()
    for value in (post_seconds, verify_seconds):
        if type(value) is not int or value <= 0 or maximum is not None and value > maximum:
            raise ValueError("CPU assessment budgets must be finite positive integers within partition limits")
    estimate = measured_train_estimate(preparation, specs[0])
    budget = finite_budget(estimate, maximum)
    gates = {case["initialization"]: checked_pair_gate(settings, case["id"], preparation, independent_gate,
                                                     budget_seconds=budget) for case in cases}
    commits = {gate["git_commit"] for gate in gates.values()}
    if len(commits) != 1:
        raise ValueError("Both supplemental modes must use one checked execution source")
    commit = commits.pop()
    settings = {key: str(value) for key, value in settings.items()}
    options = []
    for key, flag in (("definitions", "--definitions"), ("primary_matrix", "--primary-matrix")):
        if key in settings: options += [flag, settings[key]]
    stages = []
    for case in cases:
        identifier = case["id"]
        post = "runs/arxiv-v1/supplemental-postprocessing/" + identifier + "-" + commit[:7] + "-attempt-001"
        verify = "runs/arxiv-v1/supplemental-acceptance/" + identifier + "-" + commit[:7] + "-attempt-001"
        common = [str(Path(sys.executable).absolute()), "scripts/run_tensor_case.py"]
        for phase, seconds, output in (("train", budget, case["run_directory"]), ("post", post_seconds, post), ("verify", verify_seconds, verify)):
            args = common + [phase, "--case", identifier] + options
            if phase == "train":
                args += ["--preparation", str(preparation), "--independent-gate", str(independent_gate), "--budget-seconds", str(budget)]
            else:
                args += ["--output", output]
                if phase == "verify": args += ["--postprocessing", post]
            dependency = None if phase == "train" else identifier + (":train" if phase == "post" else ":post")
            item = _stage(case, phase, args, seconds, depends_on=dependency, output=output)
            stages.append(item)
            receipt = claim_path(item) / "launch.json"
            terminal_args = [str(Path(sys.executable).absolute()), "scripts/record_tensor_terminal.py", "stage",
                             "--receipt", str(receipt), "--stage-output", output]
            stages.append(_stage(case, "terminal_" + phase, terminal_args, 120,
                                 depends_on=item["key"], output=str(receipt.parent / "terminal.json")))
    provenance = dict(git_commit=commit, pair_id=pair, definitions=settings, original_independent_gate=original_terminal,
        python=str(Path(sys.executable).absolute()), preparation=str(preparation), independent_gate=str(independent_gate),
        gates={mode: canonical_digest(gate) for mode, gate in gates.items()},
        stages=[{key: value for key, value in item.items() if key != "script"} for item in stages])
    return dict(status="checked", kind="supplemental_tensor_pair_submission_plan", pair_id=pair, cases=cases,
        provenance=provenance, fingerprint=canonical_digest(provenance), gates=gates, stages=stages,
        probed_train_only_seconds=estimate, training_budget_seconds=budget, formal_training_runs_completed=0,
        interpretation="Twelve finite managed requests per pair:two trainings,four scientific CPU stages,six terminal recorders. Requests are not completed experiments.")


def _existing(plan):
    receipts = {}
    for item in plan["stages"]:
        claim = claim_path(item)
        if claim.exists() or claim.is_symlink():
            if claim.is_symlink() or not (claim / "submission-intent.json").is_file() or not (claim / "launch.json").is_file():
                raise RuntimeError("Existing supplemental claim is foreign or ambiguous; preserve it")
            intent = read_json(claim / "submission-intent.json")
            if intent.get("managed_by") != MANAGED or intent.get("fingerprint") != plan["fingerprint"]:
                raise RuntimeError("Existing supplemental request provenance differs")
            if item["depends_on"] is not None and item["depends_on"] not in receipts:
                raise RuntimeError("Existing child claim has no exact original parent receipt")
            receipt = submit_stage(plan, item, receipts, directory=claim, dependency_kind=item["dependency_kind"])
            checked_request_resources(receipt)
            receipts[item["key"]] = receipt
        elif Path(item["output"]).exists() or Path(item["output"]).is_symlink():
            raise FileExistsError("Unclaimed supplemental output already exists")
    return receipts


def checked_request_resources(receipt):
    fields = validate_submitted_job(receipt)
    resources = receipt["resources"]
    checked_fields(fields, job=receipt["job"], name="ugnn-" + stage_kind(receipt["phase"]) + "-" + receipt["case_id"],
        source=receipt["source_checkout"], cpus=resources["cpus_per_task"], memory=resources["memory_gib"],
        seconds=resources["budget_seconds"], gpus=resources["gpus"], token=receipt["submission_token"], nice=resources["nice"])


def dispatch_tensor_pair(settings, pair, preparation, independent_gate, **options):
    plan = build_tensor_submission_plan(settings, pair, preparation, independent_gate, **options)
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB free disk reserve before submission")
    root = DISPATCHES / pair
    root.mkdir(parents=True, exist_ok=True)
    with pair_lock(root):
        existing = _existing(plan)
        identity = root / "provenance.json"
        if identity.exists() and read_json(identity).get("fingerprint") != plan["fingerprint"]:
            raise RuntimeError("Supplemental pair source/evidence differs from its original dispatch")
        write_json(identity, dict(fingerprint=plan["fingerprint"], provenance=plan["provenance"]))
        attempt = root / "attempts" / os.environ["SLURM_JOB_ID"]
        attempt.mkdir(parents=True, exist_ok=False)
        write_json(attempt / "plan.json", plan)
        report = dict(status="dispatching", pair_id=pair, fingerprint=plan["fingerprint"],
            parent_slurm_job=os.environ["SLURM_JOB_ID"], jobs={}, formal_training_runs_completed=0)
        try:
            for item in plan["stages"]:
                receipt = existing.get(item["key"])
                if receipt is None:
                    receipt = submit_stage(plan, item, report["jobs"], directory=claim_path(item),
                                           dependency_kind=item["dependency_kind"])
                    report["jobs"][item["key"]] = receipt
                    write_json(attempt / "report.json", report)
                    checked_request_resources(receipt)
                report["jobs"][item["key"]] = receipt
                write_json(attempt / "report.json", report)
            report.update(status="submitted", formal_training_jobs=2, scientific_cpu_jobs=4, terminal_recorders=6,
                newly_submitted_training_jobs=sum(not row["reused"] and row["phase"] == "train" for row in report["jobs"].values()),
                newly_submitted_jobs=sum(not row["reused"] for row in report["jobs"].values()),
                interpretation="Exact requests only; known receipts reused. Foreign/unknown/purged claims stop without resubmission. No scientific completion count.")
            write_json(attempt / "report.json", report)
            write_json(root / "latest.json", dict(attempt=str(attempt), **report))
            return report
        except Exception as error:
            report.update(status="submission_failed", error_type=type(error).__name__, error=str(error))
            write_json(attempt / "report.json", report)
            raise
