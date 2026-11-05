"""Bind launches to the eight already-submitted official preparation pipelines."""

import os
from pathlib import Path
import re
import shlex

from ..execution.gates import file_sha, read_json
from ..supplemental_tensors.telemetry import checked_fields, source_pinned
from .contracts import DEFINITION_SHA
from .execution import execution_spec

PREPARATION_COMMIT = "b1678818c0adf54022f3a2835d75c0342f61781c"
PREPARATION_CLAIMS = Path("runs/official-frozen-preparations-b167881-claim")
FIRST_JOBS = dict(cgcnn=1508, alignn=1516, mace=1524, nequip=1532)
PHASES = ("prepare", "prepare-terminal", "gate", "gate-terminal")


def original_entries(settings, identifier):
    spec = execution_spec(settings, identifier)
    case = spec["case"]
    claim = PREPARATION_CLAIMS
    jobs = read_json(claim / "jobs.json")
    expected_ids = {"frozen--seed-123--" + task + "--" + provider
                    for task in ("forcefield", "dielectric") for provider in FIRST_JOBS}
    if set(jobs) != expected_ids or set(jobs[identifier]) != set(PHASES):
        raise ValueError("Require the original eight closed frozen preparation pipelines")
    first = FIRST_JOBS[case["model"]] + (4 if case["task"] == "dielectric" else 0)
    preparation = "runs/arxiv-v1/frozen-preparation-" + str(first) + "-" + case["task"] + "-" + case["model"]
    gate = "runs/arxiv-v1/frozen-independent-gates-b167881/" + identifier + ".json"
    outputs = [preparation, str(claim / (identifier + "-preparation-terminal.json")), gate,
               str(claim / (identifier + "-gate-terminal.json"))]
    dependencies = [None, "afterany:" + str(first), "afterok:" + str(first) + ":" + str(first + 1),
                    "afterany:" + str(first + 2)]
    for index, phase in enumerate(PHASES):
        entry = jobs[identifier][phase]
        argv = entry.get("sbatch_argv", [])
        flags = dict(a.split("=", 1) for a in argv if a.startswith("--") and "=" in a)
        cpus, memory, limit, gpus, nice = resources(phase)
        request = claim / (identifier + "-" + phase + ".sh")
        expected = {"--partition": "compute", "--nodelist": "node42", "--cpus-per-task": str(cpus),
            "--mem": str(memory) + "G", "--time": limit, "--nice": str(nice),
            "--chdir": "/home/xmz/universal/runs/source-checkouts/" + PREPARATION_COMMIT,
            "--job-name": "ugnn-frozen-" + phase + "-" + identifier,
            "--comment": entry.get("submission_token")}
        if (entry.get("case_id") != identifier or entry.get("phase") != phase or
                entry.get("job") != str(first + index) or entry.get("git_commit") != PREPARATION_COMMIT or
                entry.get("source_checkout") != expected["--chdir"] or entry.get("formal_training_runs") != 0 or
                not re.fullmatch(r"ugnn-frozen-[0-9a-f]{32}", entry.get("submission_token", "")) or
                entry.get("output") != outputs[index] or
                Path(entry.get("request_path", "")).resolve() != request.resolve() or
                entry.get("request_sha256") != file_sha(request) or
                not argv or argv[0] != "sbatch" or "--parsable" not in argv or "--no-requeue" not in argv or
                any(flags.get(key) != value for key, value in expected.items()) or
                flags.get("--dependency") != dependencies[index] or
                flags.get("--gres") != ("gpu:1" if gpus else None)):
            raise ValueError("Original frozen request/case/source/token/resources/dependency differs")
    return spec, jobs[identifier]


def resources(phase):
    if phase == "prepare":
        return 2, 64, "16:00:00", 1, 1000
    if phase == "gate":
        return 1, 4, "00:20:00", 0, 0
    return 1, 1, "00:02:00", 0, 0


def checked_preparation_terminals(settings, identifier, preparation, independent_gate):
    """Require original successful retained prep AND gate evidence, even after purge."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen preparation terminal checks require Slurm")
    spec, entries = original_entries(settings, identifier)
    if (Path(entries["prepare"]["output"]).resolve() != Path(preparation).resolve() or
            Path(entries["gate"]["output"]).resolve() != Path(independent_gate).resolve()):
        raise ValueError("Use the original preparation and independent gate outputs")
    source_pinned(entries["prepare"])
    bindings = {str(PREPARATION_CLAIMS / "jobs.json"): file_sha(PREPARATION_CLAIMS / "jobs.json")}
    for phase in PHASES:
        bindings[entries[phase]["request_path"]] = file_sha(entries[phase]["request_path"])
    for phase, artifact in (("prepare", Path(preparation) / "report.json"), ("gate", Path(independent_gate))):
        entry = entries[phase]
        path = Path(entries[phase + "-terminal"]["output"])
        terminal = read_json(path)
        fields = dict(t.split("=", 1) for t in shlex.split(terminal.get("raw", "")) if "=" in t)
        cpus, memory, _, gpus, nice = resources(phase)
        if (terminal.get("status") != "retained" or terminal.get("successful") is not True or
                terminal.get("entry") != entry or terminal.get("fields") != fields or
                terminal.get("request_sha256") != entry["request_sha256"] or
                terminal.get("formal_training_runs") != 0 or fields.get("JobState") != "COMPLETED" or
                fields.get("ExitCode") != "0:0" or
                Path(terminal.get("artifact", "")).resolve() != artifact.resolve() or
                terminal.get("artifact_sha256") != file_sha(artifact)):
            raise ValueError("Require exact successful original frozen terminal and artifact bindings")
        checked_fields(fields, job=entry["job"], name="ugnn-frozen-" + phase + "-" + identifier,
            source=entry["source_checkout"], cpus=cpus, memory=memory,
            seconds=57600 if phase == "prepare" else 1200, gpus=gpus, token=entry["submission_token"], nice=nice)
        bindings[str(path)] = file_sha(path)
        bindings[str(artifact)] = file_sha(artifact)
    prepared, gate = read_json(Path(preparation) / "report.json"), read_json(independent_gate)
    if (prepared.get("git_commit") != PREPARATION_COMMIT or prepared.get("slurm_job_id") != entries["prepare"]["job"] or
            prepared.get("case_id") != identifier or prepared.get("status") != "passed" or
            prepared.get("stage") != "complete" or prepared.get("cuda_acceptance") is not True or
            gate.get("git_commit") != PREPARATION_COMMIT or gate.get("case") != spec["case"] or
            gate.get("definition_sha256") != DEFINITION_SHA or gate.get("status") != "passed"):
        raise ValueError("Original frozen CUDA preparation/gate source and successful identity differ")
    return dict(preparation_job=entries["prepare"]["job"], independent_gate_job=entries["gate"]["job"],
                source_commit=PREPARATION_COMMIT, input_sha256=bindings)
