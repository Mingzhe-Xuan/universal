"""Six managed stages; no repeat after foreign, unknown or purged submissions."""

import hashlib
import os
from pathlib import Path
import shutil
import sys

from ...execution.gates import canonical_digest, read_json
from ...preflight import write_json
from ...submission.dispatch import check_existing_cases, claim_directory, pair_lock, stage_kind, submit_stage, validate_submitted_job
from ...submission.planning import partition_maximum, request_script, slurm_duration
from ...supplemental_tensors.telemetry import checked_fields
from .gates import check_execution_gate


def _stage(case, phase, args, seconds, dependency=None, output=None):
    recorder = phase.startswith("terminal_")
    body = request_script(args, cpu_only=phase != "train")
    return dict(key=case["id"] + ":" + phase, case_id=case["id"], phase=phase, depends_on=dependency,
        dependency_kind="afterany" if recorder else "afterok", script=body,
        request_sha256=hashlib.sha256(body.encode()).hexdigest(), output=output,
        resources=dict(partition="compute", node="node42", gpus=int(phase == "train"), cpus_per_task=1,
            memory_gib=64 if phase == "train" else 16 if phase == "post" else 8 if phase == "verify" else 1,
            time=slurm_duration(seconds), budget_seconds=seconds, nice=0))


def build_submission_plan(identifier, preparation, terminal, *, post_seconds, verify_seconds):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Molecular planning/submission requires CPU Slurm")
    maximum = partition_maximum()
    for value in [post_seconds, verify_seconds]:
        if type(value) is not int or value <= 0 or maximum is not None and value > maximum:
            raise ValueError("Declare finite positive CPU budgets within the partition limit")
    gate = check_execution_gate(identifier, preparation, terminal, maximum=maximum)
    case, commit = gate["case"], gate["git_commit"]
    post = "runs/arxiv-v1/molecular-postprocessing/" + identifier + "-" + commit[:7] + "-attempt-001"
    verify = "runs/arxiv-v1/molecular-acceptance/" + identifier + "-" + commit[:7] + "-attempt-001"
    stages = []
    for phase, seconds, output in [("train", gate["budget_seconds"], case["run_directory"]),
                                   ("post", post_seconds, post), ("verify", verify_seconds, verify)]:
        args = [str(Path(sys.executable).absolute()), "scripts/run_molecular_case.py", phase, "--case", identifier]
        if phase == "train":
            args += ["--preparation", str(preparation), "--preparation-terminal", str(terminal), "--budget-seconds", str(seconds)]
        else:
            args += ["--output", output]
            if phase == "verify":args += ["--postprocessing", post]
        item = _stage(case, phase, args, seconds, None if phase == "train" else identifier + (":train" if phase == "post" else ":post"), output)
        stages.append(item)
        receipt = claim_directory(item) / "launch.json"
        args = [str(Path(sys.executable).absolute()), "scripts/record_tensor_terminal.py", "stage", "--receipt", str(receipt), "--stage-output", output]
        stages.append(_stage(case, "terminal_" + phase, args, 120, item["key"], str(receipt.parent / "terminal.json")))
    provenance = dict(git_commit=commit, case_id=identifier, joint_preparation=str(preparation), joint_terminal=str(terminal),
        execution_gate_sha256=canonical_digest(gate), stages=[{k: v for k,v in row.items() if k != "script"} for row in stages])
    return dict(status="checked", kind="molecular_full_case_submission_plan", case_id=identifier, cases=[case], gate=gate,
        stages=stages, provenance=provenance, fingerprint=canonical_digest(provenance), formal_training_runs_submitted=0,
        partition_maximum_seconds=maximum, interpretation="One full900/100/99000 train, CPU raw-label/physics/all-source/author1000 post, no-model verification and three terminal recorders. Requests are not scientific completion.")


def dispatch_case(identifier, preparation, terminal, **options):
    plan = build_submission_plan(identifier, preparation, terminal, **options)
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB disk reserve before molecular submission")
    root = Path("runs/arxiv-v1/molecular-dispatch") / identifier
    if root.is_symlink():raise FileExistsError("Foreign dispatch symlink")
    root.mkdir(parents=True, exist_ok=True)
    with pair_lock(root):
        check_existing_cases(plan)
        provenance = root / "provenance.json"
        if provenance.exists() and read_json(provenance).get("fingerprint") != plan["fingerprint"]:
            raise RuntimeError("Molecular dispatch provenance changed; preserve original claims")
        write_json(provenance, dict(fingerprint=plan["fingerprint"], provenance=plan["provenance"]))
        attempt = root / "attempts" / os.environ["SLURM_JOB_ID"]
        attempt.mkdir(parents=True, exist_ok=False)
        write_json(attempt / "plan.json", plan)
        report = dict(status="dispatching", case_id=identifier, fingerprint=plan["fingerprint"], jobs={}, formal_training_runs_completed=0)
        try:
            for item in plan["stages"]:
                claim = claim_directory(item)
                if not claim.exists() and (Path(item["output"]).exists() or Path(item["output"]).is_symlink()):
                    raise FileExistsError("Unclaimed original molecular output already exists")
                receipt = submit_stage(plan, item, report["jobs"], dependency_kind=item["dependency_kind"])
                report["jobs"][item["key"]] = receipt
                write_json(attempt / "report.json", report)
                fields = validate_submitted_job(receipt);resources = receipt["resources"]
                checked_fields(fields, job=receipt["job"], name="ugnn-" + stage_kind(receipt["phase"]) + "-" + identifier,
                    source=receipt["source_checkout"], cpus=resources["cpus_per_task"], memory=resources["memory_gib"],
                    seconds=resources["budget_seconds"], gpus=resources["gpus"], token=receipt["submission_token"], nice=0)
            report.update(status="submitted", newly_submitted_training_jobs=sum(row["phase"] == "train" and not row["reused"] for row in report["jobs"].values()),
                interpretation="Exact managed requests only; unknown/foreign/purged claims stop. No scientific completion.")
            write_json(attempt / "report.json", report)
            return report
        except Exception as error:
            report.update(status="submission_failed", error_type=type(error).__name__, error=str(error))
            write_json(attempt / "report.json", report)
            raise
