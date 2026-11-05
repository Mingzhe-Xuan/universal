"""Retain exact Slurm terminal identities before accounting handles are purged."""

import getpass
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

from ..execution.gates import file_sha, read_json
from ..execution.runner import duration_seconds
from ..submission.dispatch import MANAGED, stage_kind
from .execution import selected_case

GATE_COMMIT = "3483500042732aa2b2e9e7b5e0b11e4018e55e8d"
GATE_CLAIMS = Path("runs/rank34-independent-gates-3483500-claim")
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL",
                   "BOOT_FAIL", "PREEMPTED", "REVOKED", "DEADLINE"}


def original_gate_entry(settings, pair):
    selected_case(settings, pair + "--pretrained")
    path = GATE_CLAIMS / pair / "job.json"
    entry = read_json(path)
    request = path.parent / "request.sh"
    flags = dict(part.split("=", 1) for part in entry.get("sbatch_argv", []) if part.startswith("--") and "=" in part)
    expected = {"--partition": "compute", "--nodelist": "node42", "--cpus-per-task": "1", "--mem": "4G",
                "--time": "00:20:00", "--chdir": entry.get("source_checkout"),
                "--job-name": "ugnn-rank34-independent-gate-" + pair,
                "--dependency": "afterok:" + str(entry.get("preparation_job")) + ":" + str(entry.get("terminal_observer_job"))}
    if (entry.get("pair") != pair or entry.get("seed") != 123 or entry.get("git_commit") != GATE_COMMIT or
            entry.get("source_checkout") != "/home/xmz/universal/runs/source-checkouts/" + GATE_COMMIT or
            entry.get("state") != "submitted" or entry.get("formal_training_runs") != 0 or
            entry.get("acceptance_control_job") != "1252" or not re.fullmatch(r"[1-9][0-9]*", entry.get("job", "")) or
            Path(entry.get("request_path", "")).resolve() != request.resolve() or
            entry.get("request_sha256") != file_sha(request) or entry.get("dependency") != expected["--dependency"] or
            any(flags.get(key) != value for key, value in expected.items()) or "--gres" in flags or
            entry.get("sbatch_argv", [None])[0] != "sbatch" or "--no-requeue" not in entry.get("sbatch_argv", [])):
        raise ValueError("Original independent gate receipt/request/source/resources differ")
    return path, entry


def checked_fields(fields, *, job, name, source, cpus, memory, seconds, gpus=0, token=None, nice=None):
    if (fields.get("JobId") != job or fields.get("UserId", "").split("(")[0] != getpass.getuser() or
            fields.get("JobName") != name or fields.get("WorkDir") != source or fields.get("Partition") != "compute" or
            fields.get("Requeue") != "0" or fields.get("NumCPUs") != str(cpus) or
            fields.get("MinMemoryNode") != str(memory) + "G" or duration_seconds(fields.get("TimeLimit", "")) != seconds or
            (token is not None and fields.get("Comment") != token) or
            (nice is not None and fields.get("Nice") != str(nice))):
        raise ValueError("Actual Slurm identity/source/resources differ from the exact request")
    gpu_field = fields.get("TresPerNode", "")
    if (gpus and gpu_field != "gres:gpu:" + str(gpus)) or (not gpus and gpu_field not in {"", "(null)"}):
        raise ValueError("Actual requested GPU profile differs")
    if fields.get("ReqNodeList", "node42") != "node42":
        raise ValueError("Slurm request names another node")


def source_pinned(entry):
    source = entry["source_checkout"]
    if (subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip() != entry["git_commit"] or
            subprocess.check_output(["git", "-C", source, "status", "--porcelain", "--untracked-files=no"], text=True).strip()):
        raise ValueError("Original submitted source cache changed")


def _save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _capture(entry, receipt_path, artifacts, output, check):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Terminal recording must run through Slurm")
    if Path(output).exists() or Path(output).is_symlink():
        raise FileExistsError("Retained terminal evidence must never be overwritten")
    source_pinned(entry)
    result = subprocess.run(["scontrol", "show", "job", "-o", entry["job"]], capture_output=True, text=True)
    fields = dict(token.split("=", 1) for token in shlex.split(result.stdout) if "=" in token)
    value = dict(status="unavailable", entry=entry, receipt=str(receipt_path), receipt_sha256=file_sha(receipt_path),
        request_sha256=file_sha(entry["request_path"]), exit=result.returncode, raw=result.stdout, stderr=result.stderr,
        fields=fields, observer_slurm_job=os.environ["SLURM_JOB_ID"], observed_at=time.time(), formal_training_runs=0,
        artifact_sha256={str(p): file_sha(p) for p in artifacts if Path(p).is_file()})
    try:
        if result.returncode == 0:
            check(fields)
            if fields.get("JobState") not in TERMINAL_STATES:
                raise ValueError("afterany terminal recorder observed a nonterminal parent")
            value.update(status="retained", successful=fields["JobState"] == "COMPLETED" and fields.get("ExitCode") == "0:0")
        _save(output, value)
        return value
    except Exception as error:
        value.update(status="invalid_identity", error_type=type(error).__name__, error=str(error))
        _save(output, value)
        raise


def record_gate_terminal(settings, pair):
    path, entry = original_gate_entry(settings, pair)
    output = path.parent / "terminal.json"
    check = lambda fields: checked_fields(fields, job=entry["job"], name="ugnn-rank34-independent-gate-" + pair,
        source=entry["source_checkout"], cpus=1, memory=4, seconds=1200, nice=0)
    return _capture(entry, path, [Path(entry["output"]) / "report.json"], output, check)


def checked_gate_terminal(settings, pair, independent_gate):
    path, entry = original_gate_entry(settings, pair)
    source_pinned(entry)
    terminal_path = path.parent / "terminal.json"
    terminal = read_json(terminal_path)
    parent_path = Path(independent_gate) / "report.json"
    parent = read_json(parent_path)
    if (Path(entry["output"]).resolve() != Path(independent_gate).resolve() or
            terminal.get("status") != "retained" or terminal.get("successful") is not True or terminal.get("exit") != 0 or
            terminal.get("entry") != entry or terminal.get("receipt_sha256") != file_sha(path) or
            terminal.get("request_sha256") != entry["request_sha256"] or
            terminal.get("artifact_sha256", {}).get(str(parent_path)) != file_sha(parent_path) or
            parent.get("slurm_job_id") != entry["job"] or parent.get("git_commit") != entry["git_commit"]):
        raise ValueError("Require the exact retained successful independent gate terminal/report proof")
    fields = dict(token.split("=", 1) for token in shlex.split(terminal.get("raw", "")) if "=" in token)
    if fields != terminal.get("fields") or fields.get("JobState") != "COMPLETED" or fields.get("ExitCode") != "0:0":
        raise ValueError("Independent gate retained terminal does not prove success")
    checked_fields(fields, job=entry["job"], name="ugnn-rank34-independent-gate-" + pair,
                   source=entry["source_checkout"], cpus=1, memory=4, seconds=1200, nice=0)
    return dict(receipt=str(path), receipt_sha256=file_sha(path), terminal=str(terminal_path),
                terminal_sha256=file_sha(terminal_path), request_sha256=entry["request_sha256"], job=entry["job"])


def record_stage_terminal(receipt_path, stage_output):
    receipt_path = Path(receipt_path)
    entry = read_json(receipt_path)
    phase = entry.get("phase")
    token = entry.get("submission_token", "")
    if (entry.get("managed_by") != MANAGED or phase not in {"train", "post", "verify"} or
            entry.get("state") != "submitted" or not re.fullmatch(r"[1-9][0-9]*", entry.get("job", "")) or
            not re.fullmatch(r"ugnn-[0-9a-f]{32}", token) or
            entry.get("key") != entry.get("case_id", "") + ":" + phase or
            Path(entry.get("request_path", "")).resolve() != (receipt_path.parent / "request.sh").resolve() or
            entry.get("request_sha256") != file_sha(entry["request_path"])):
        raise ValueError("Managed scientific stage receipt/request/token differs")
    resources = entry["resources"]
    output = receipt_path.parent / "terminal.json"
    check = lambda fields: checked_fields(fields, job=entry["job"], name="ugnn-" + stage_kind(phase) + "-" + entry["case_id"],
        source=entry["source_checkout"], cpus=resources["cpus_per_task"], memory=resources["memory_gib"],
        seconds=resources["budget_seconds"], gpus=resources["gpus"], token=token, nice=resources.get("nice"))
    artifacts = [Path(stage_output) / "report.json"]
    if phase == "train": artifacts.append(Path(stage_output) / "formal-status.json")
    return _capture(entry, receipt_path, artifacts, output, check)
