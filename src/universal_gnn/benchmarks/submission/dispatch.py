"""Persist exact requests and receipts; never retry an ambiguous Slurm submission."""

from contextlib import contextmanager
import hashlib
import getpass
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
import uuid

from ..execution.gates import read_json
from ..preflight import write_json
from .planning import build_submission_plan

MANAGED = "ugnn_full_pair_dispatch_v1"


@contextmanager
def pair_lock(root):
    active = root / "active"
    active.mkdir()
    try:
        write_json(active / "owner.json", dict(slurm_job_id=os.environ["SLURM_JOB_ID"]))
        yield
    finally:
        (active / "owner.json").unlink(missing_ok=True)
        active.rmdir()


def claim_directory(item):
    root = Path("runs/arxiv-v1/launches") / item["case_id"]
    return root if item["phase"] == "train" else root / item["phase"]


def validate_submitted_job(receipt):
    """Only reuse a retained, same-user Slurm job with the exact submission token."""
    try:
        raw = subprocess.check_output(["scontrol", "show", "job", "-o", receipt["job"]], text=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError("Slurm no longer retains this receipt; reconcile actual artifacts before retry") from error
    fields = dict(token.split("=", 1) for token in shlex.split(raw) if "=" in token)
    kind = "formal" if receipt["phase"] == "train" else "generation-" + receipt["phase"]
    if (fields.get("JobId") != receipt["job"] or
            fields.get("UserId", "").split("(")[0] != getpass.getuser() or
            fields.get("JobName") != "ugnn-" + kind + "-" + receipt["case_id"] or
            fields.get("Comment") != receipt["submission_token"] or
            fields.get("JobState") not in {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING", "COMPLETED"}):
        raise RuntimeError("Existing Slurm owner/token/name/state does not match this exact stage")


def check_existing_cases(plan):
    for case in plan["cases"]:
        directory = Path("runs/arxiv-v1/launches") / case["id"]
        if directory.exists() or directory.is_symlink():
            if directory.is_symlink() or not (directory / "submission-intent.json").is_file():
                raise FileExistsError("An external or older case claim already owns " + case["id"])
            intent = read_json(directory / "submission-intent.json")
            if intent.get("managed_by") != MANAGED or intent.get("fingerprint") != plan["fingerprint"]:
                raise FileExistsError("Existing case provenance differs; preserve it")
            if not (directory / "launch.json").is_file():
                raise RuntimeError("Prior submission is ambiguous; reconcile its Slurm token before any retry")
        elif Path(case["run_directory"]).exists() or Path(case["run_directory"]).is_symlink():
            raise FileExistsError("Refusing to rerun an existing primary result " + case["id"])


def submit_stage(plan, item, jobs):
    directory = claim_directory(item)
    dependency = None if item["depends_on"] is None else "afterok:" + jobs[item["depends_on"]]["job"]
    expected = dict(managed_by=MANAGED, fingerprint=plan["fingerprint"], key=item["key"],
                    case_id=item["case_id"], phase=item["phase"], dependency=dependency,
                    request_sha256=item["request_sha256"], resources=item["resources"],
                    git_commit=plan["provenance"]["git_commit"], source_checkout=str(Path.cwd().resolve()))
    intent_path, receipt_path = directory / "submission-intent.json", directory / "launch.json"
    if directory.exists() or directory.is_symlink():
        if directory.is_symlink() or not intent_path.is_file() or not receipt_path.is_file():
            raise RuntimeError("Unfinished/ambiguous stage claim; preserve and reconcile it")
        intent, receipt = read_json(intent_path), read_json(receipt_path)
        if (any(intent.get(k) != v or receipt.get(k) != v for k, v in expected.items()) or
                intent.get("state") != "submitted" or receipt.get("state") != "submitted" or
                intent.get("submission_token") != receipt.get("submission_token") or
                not re.fullmatch(r"ugnn-[0-9a-f]{32}", receipt.get("submission_token", "")) or
                not re.fullmatch(r"[1-9][0-9]*", receipt.get("job", "")) or
                hashlib.sha256((directory / "request.sh").read_bytes()).hexdigest() != item["request_sha256"]):
            raise RuntimeError("Existing request/receipt is not the exact submitted stage")
        validate_submitted_job(receipt)
        return dict(receipt, reused=True)
    directory.mkdir(parents=True, exist_ok=False)
    body = item["script"].encode()
    if hashlib.sha256(body).hexdigest() != item["request_sha256"]:
        raise ValueError("Planned script bytes changed")
    (directory / "request.sh").write_bytes(body)
    token = "ugnn-" + uuid.uuid4().hex
    intent = dict(expected, state="submitting", submission_token=token,
                  parent_slurm_job=os.environ["SLURM_JOB_ID"], created_at=time.time())
    write_json(intent_path, intent)
    resources = item["resources"]
    kind = "formal" if item["phase"] == "train" else "generation-" + item["phase"]
    argv = ["sbatch", "--parsable", "--no-requeue", "--partition=" + resources["partition"],
            "--nodelist=" + resources["node"], "--cpus-per-task=" + str(resources["cpus_per_task"]),
            "--mem=" + str(resources["memory_gib"]) + "G", "--time=" + resources["time"],
            "--chdir=" + str(Path.cwd().resolve()), "--job-name=ugnn-" + kind + "-" + item["case_id"],
            "--comment=" + token, "--output=runs/arxiv-v1/" + kind + "-%j.out",
            "--error=runs/arxiv-v1/" + kind + "-%j.err"]
    if resources["gpus"]:
        argv.append("--gres=gpu:" + str(resources["gpus"]))
    if dependency:
        argv.append("--dependency=" + dependency)
    intent["sbatch_argv"] = argv
    write_json(intent_path, intent)
    try:
        result = subprocess.run(argv, input=body, capture_output=True, timeout=30)
        match = re.fullmatch(rb"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?", result.stdout.strip())
        if result.returncode or match is None:
            raise RuntimeError("Slurm did not return an unambiguous parsable job receipt")
        receipt = dict(intent, state="submitted", job=match.group(1).decode(), submitted_at=time.time(),
                       request_path=str(directory / "request.sh"), formal_training_runs_completed=0)
        write_json(receipt_path, receipt)
        intent["state"] = "submitted"
        write_json(intent_path, intent)
        return dict(receipt, reused=False)
    except Exception as error:
        intent.update(state="submission_unknown", error_type=type(error).__name__, error=str(error))
        write_json(intent_path, intent)
        raise


def dispatch_pair(matrix, pair_id, preparation, *, matrix_path):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Pair gate/submission must run through Slurm")
    plan = build_submission_plan(matrix, pair_id, preparation, matrix_path=matrix_path)
    check_existing_cases(plan)
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB free disk reserve before submission")
    root = Path("runs/arxiv-v1/dispatch") / pair_id
    root.mkdir(parents=True, exist_ok=True)
    with pair_lock(root):
        identity = root / "provenance.json"
        if identity.exists() and read_json(identity).get("fingerprint") != plan["fingerprint"]:
            raise RuntimeError("Existing pair dispatch belongs to different evidence/source")
        write_json(identity, dict(fingerprint=plan["fingerprint"], provenance=plan["provenance"]))
        attempt = root / "attempts" / os.environ["SLURM_JOB_ID"]
        attempt.mkdir(parents=True, exist_ok=False)
        write_json(attempt / "plan.json", plan)
        report = dict(status="dispatching", pair_id=pair_id, fingerprint=plan["fingerprint"],
                      parent_slurm_job=os.environ["SLURM_JOB_ID"], jobs={}, formal_training_runs_completed=0)
        try:
            for item in plan["stages"]:
                report["jobs"][item["key"]] = submit_stage(plan, item, report["jobs"])
                write_json(attempt / "report.json", report)
            report.update(status="submitted", formal_training_jobs=len(plan["cases"]),
                          newly_submitted_training_jobs=sum(not r["reused"] and r["phase"] == "train" for r in report["jobs"].values()),
                          interpretation="Job receipts only, not completion or independent scientific acceptance. Known receipts are reused; unknown claims never resubmit automatically")
            write_json(attempt / "report.json", report)
            write_json(root / "latest.json", dict(attempt=str(attempt), **report))
            return report
        except Exception as error:
            report.update(status="submission_failed", error_type=type(error).__name__, error=str(error))
            write_json(attempt / "report.json", report)
            raise
