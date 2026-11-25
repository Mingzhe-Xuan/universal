"""Unique claim receipts and held, dependency-checked Slurm campaign submission."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import time
import uuid

from universal_gnn.data.preparation.qm9.conversion import write_json
from universal_gnn.data.preparation.qm9.source import digest
from .definitions import MODELS, MODES, PROPERTIES

ENVIRONMENTS = dict(cgcnn="universal-official", alignn="universal-official", mace="universal-mace", nequip="universal")


def campaign_layout(campaign="runs/qm9-v1/launches", train_time="14-00:00:00", *, profile="full"):
    if profile not in {"full", "hl12k"}:
        raise ValueError("Unknown QM9 campaign profile")
    subset = profile == "hl12k"
    root = "runs/qm9-hl12k-v1" if subset else "runs/qm9-v1"
    definitions = root + "/definition"
    properties = ("homo", "lumo") if subset else PROPERTIES
    prefix = "qm9-hl12k" if subset else "qm9"
    stages = []
    def add(key, command, *, parent=None, **options):
        command = command + ["--definitions", definitions]
        stages.append(dict(key=key, command=command, parent=parent, dependency_kind="afterok", options=options))
        stages.append(dict(key=key + "-terminal", command=["terminal", "--receipt", (Path(campaign) / key / "launch.json").as_posix()],
                           parent=key, dependency_kind="afterany", options=dict(cpus=1, memory=1, time_limit="00:05:00")))
    prepare = ["subset", "--data", "data/qm9/hl12k-v1", "--run-root", root] if subset else ["prepare"]
    data_report = "data/qm9/hl12k-v1/report.json" if subset else "data/qm9/prepared-v1/report.json"
    add("prepare", prepare, time_limit="01:00:00", artifacts=[data_report, definitions + "/definitions.json"])
    # Put all capacity gates ahead of long fitting jobs in the Slurm submission order.
    for model in MODELS:
        smoke_path, capacity_path = root + "/smoke/" + model, root + "/preflight/" + model
        add("smoke-" + model, ["smoke", "--model", model, "--output", smoke_path], model=model,
            parent="prepare", memory=16, time_limit="02:00:00", artifacts=[smoke_path + "/report.json"])
        add("preflight-" + model, ["preflight", "--model", model, "--output", capacity_path, "--smoke", smoke_path],
            model=model, parent="smoke-" + model, gpus=1, memory=64, time_limit="12:00:00", artifacts=[capacity_path + "/report.json"])
    for model in MODELS:
        capacity_path = root + "/preflight/" + model
        for prop in properties:
            for mode in MODES:
                case = f"{prefix}--seed-123--{prop}--{model}--{mode}"
                folder = root + "/cases/" + case
                add(case, ["train", "--case", case, "--preparation", capacity_path], model=model,
                    parent="preflight-" + model, gpus=1, memory=64, time_limit=train_time,
                    artifacts=[folder + "/report.json", folder + "/checkpoint.pt", folder + "/checkpoint.best.pt"])
                add(case + "-assess", ["assess", "--case", case], model=model, parent=case,
                    memory=4, time_limit="00:20:00", artifacts=[folder + "/independent-assessment.json"])
    return stages


def inspect(job):
    raw = subprocess.check_output(["scontrol", "show", "job", "-o", str(job)], text=True)
    return dict(token.split("=", 1) for token in shlex.split(raw) if "=" in token)


def seconds(value):
    days, clock = value.split("-", 1) if "-" in value else ("0", value)
    h, m, s = map(int, clock.split(":"))
    return int(days) * 86400 + h * 3600 + m * 60 + s


def check_job(entry, actual, *, held=False):
    for field, expected in dict(JobId=entry["job"], JobName=entry["name"], WorkDir=entry["source_checkout"],
                                Comment=entry["submission_token"], Partition="compute", ReqNodeList="node42",
                                NumCPUs=str(entry["cpus"]), MinMemoryNode=f"{entry['memory_gib']}G", Requeue="0").items():
        if actual[field] != expected:
            raise ValueError("QM9 Slurm identity/resource mismatch: " + field)
    if actual["UserId"].split("(")[0] != "xmz" or seconds(actual["TimeLimit"]) != seconds(entry["time"]):
        raise ValueError("QM9 Slurm owner/time mismatch")
    if actual.get("TresPerNode", "") not in ({"gres:gpu:1"} if entry["gpus"] else {"", "(null)"}):
        raise ValueError("QM9 Slurm GPU allocation differs")
    if held:
        if actual["JobState"] != "PENDING" or actual["Priority"] != "0" or actual["Reason"] != "JobHeldUser":
            raise ValueError("QM9 submission must remain held until fully recorded")
        actual_dep = actual.get("Dependency", "").split("(")[0]
        if actual_dep != (entry.get("dependency") or "") and not (not entry.get("dependency") and actual_dep in {"", "(null)"}):
            raise ValueError("QM9 held job dependency differs")


def submit_campaign(source, *, campaign="runs/qm9-v1/launches", train_time="14-00:00:00", profile="full"):
    """Lightweight submission only; all numerical work lives in scheduled children."""
    source = str(Path(source).resolve())
    commit = subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", source, "status", "--porcelain"], text=True).strip():
        raise ValueError("QM9 requires an immutable clean source checkout")
    campaign = Path(campaign)
    if not campaign.resolve().is_relative_to(Path('/home/xmz/universal/runs').resolve()):
        raise ValueError("QM9 launch claims must remain inside task runs")
    campaign.mkdir(parents=True, exist_ok=False)
    result = dict(status="submitting", git_commit=commit, source_checkout=source, jobs={}, released=[],
                  formal_training_runs_completed=0, defined_training_runs=16 if profile == "hl12k" else 32, profile=profile)
    write_json(campaign / "campaign.json", result)

    def submit(key, command, *, model=None, dependency=None, gpus=0, memory=8, cpus=2, time_limit="02:00:00", artifacts=()):
        claim = campaign / key
        claim.mkdir(parents=True, exist_ok=False)
        env = ENVIRONMENTS.get(model, "universal-official")
        python = f"/home/xmz/.venvs/{env}/bin/python"
        body = "#!/bin/bash\nset -euo pipefail\ncd " + shlex.quote(source) + "\n"
        body += 'export PYTHONPATH="$PWD/src" PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8\n'
        if not gpus:
            body += 'export CUDA_VISIBLE_DEVICES=""\n'
        body += "exec " + shlex.join([python, "scripts/run_qm9.py", *command]) + "\n"
        subprocess.run(["bash", "-n"], input=body, text=True, check=True)
        request = claim / "request.sh"
        request.write_text(body)
        token = "ugnn-" + uuid.uuid4().hex
        name = "ugnn-qm9-" + key
        entry = dict(key=key, name=name, source_checkout=source, git_commit=commit, submission_token=token,
                     dependency=dependency, gpus=gpus, memory_gib=memory, cpus=cpus, time=time_limit,
                     request_path=str(request), request_sha256=digest(request), artifacts=list(artifacts))
        argv = ["sbatch", "--parsable", "--hold", "--no-requeue", "--partition=compute", "--nodelist=node42",
                f"--cpus-per-task={cpus}", f"--mem={memory}G", f"--time={time_limit}", "--chdir=" + source,
                "--job-name=" + name, "--comment=" + token, "--output=" + str(claim / "%j.out"), "--error=" + str(claim / "%j.err")]
        if gpus:
            argv.append("--gres=gpu:1")
        if dependency:
            argv.append("--dependency=" + dependency)
        entry["sbatch_argv"] = argv
        write_json(claim / "intent.json", entry)
        process = subprocess.run(argv, input=body, text=True, capture_output=True)
        write_json(claim / "submission-rpc.json", dict(exit=process.returncode, stdout=process.stdout, stderr=process.stderr))
        job = process.stdout.strip().split(";")[0]
        if process.returncode or not job.isdecimal():
            raise RuntimeError("Ambiguous QM9 submission: preserve intent/RPC and reconcile token; never resubmit")
        entry.update(job=job, submitted_at=time.time())
        write_json(claim / "launch.json", entry)
        result["jobs"][key] = entry
        write_json(campaign / "campaign.json", result)
        check_job(entry, inspect(job), held=True)
        return entry

    for stage in campaign_layout(str(campaign), train_time, profile=profile):
        parent = stage["parent"]
        dependency = stage["dependency_kind"] + ":" + result["jobs"][parent]["job"] if parent else None
        submit(stage["key"], stage["command"], dependency=dependency, **stage["options"])
    prep = result["jobs"]["prepare"]
    if len(result["jobs"]) != (82 if profile == "hl12k" else 146):
        raise RuntimeError("QM9 campaign stage count differs")
    for entry in result["jobs"].values():
        check_job(entry, inspect(entry["job"]), held=True)
    # Every dependent stage is armed before its root preparation can execute.
    for key, entry in list(result["jobs"].items())[1:] + [("prepare", prep)]:
        subprocess.run(["scontrol", "release", entry["job"]], check=True)
        result["released"].append(entry["job"])
        write_json(campaign / "campaign.json", result)
    result.update(status="submitted", slurm_jobs=len(result["jobs"]), preparation_job=prep["job"])
    write_json(campaign / "campaign.json", result)
    return result


def record_terminal(receipt):
    receipt = Path(receipt)
    entry = json.loads(receipt.read_bytes())
    if digest(entry["request_path"]) != entry["request_sha256"]:
        raise ValueError("QM9 terminal request changed")
    actual = inspect(entry["job"])
    check_job(entry, actual)
    if actual["JobState"] not in {"COMPLETED", "FAILED", "TIMEOUT", "CANCELLED", "OUT_OF_MEMORY", "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE"}:
        raise ValueError("QM9 parent is not terminal")
    result = dict(status="retained", entry=entry, fields=actual,
                  successful=actual["JobState"] == "COMPLETED" and actual["ExitCode"] == "0:0",
                  artifact_sha256={name:digest(name) for name in entry["artifacts"] if Path(name).is_file()},
                  observer_slurm_job=os.environ["SLURM_JOB_ID"])
    write_json(receipt.parent / "terminal.json", result)
    return result
