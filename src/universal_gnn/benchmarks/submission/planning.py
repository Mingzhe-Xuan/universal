"""Read complete scientific evidence before planning finite Slurm allocations."""

import hashlib
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys

from ..execution.gates import case_spec, check_preparation, file_sha, read_json
from ..execution.runner import duration_seconds
from ..experiments.registry import canonical_digest
from ..pairing.evidence import verify_capacity_evidence


def finite_budget(estimate, maximum=None):
    if type(estimate) not in (int, float) or not math.isfinite(estimate) or estimate <= 0:
        raise ValueError("Capacity estimate must be finite and positive")
    reserved = 1.5 * estimate + 900
    if not math.isfinite(reserved):
        raise ValueError("Measured allocation budget overflowed")
    if maximum is not None and (type(maximum) is not int or maximum <= 0):
        raise ValueError("Partition maximum must be a positive finite integer or unlimited")
    budget = max(3600, math.ceil(reserved / 60) * 60)
    if maximum is not None and budget > maximum:
        raise ValueError("Measured full protocol exceeds this partition's finite time limit")
    return budget


def slurm_duration(seconds):
    if type(seconds) is not int or seconds <= 0:
        raise ValueError("Require a positive finite integer budget")
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}-{hours:02d}:{minutes:02d}:{seconds:02d}"


def partition_maximum():
    value = subprocess.check_output(["scontrol", "show", "partition", "compute", "-o"], text=True)
    fields = dict(item.split("=", 1) for item in shlex.split(value) if "=" in item)
    if fields.get("PartitionName") != "compute" or fields.get("State") != "UP":
        raise ValueError("The configured compute partition is unavailable")
    return None if fields.get("MaxTime") == "UNLIMITED" else duration_seconds(fields["MaxTime"])


def measured_train_estimate(preparation, spec):
    preparation = Path(preparation)
    prepared = read_json(preparation / "report.json")
    if prepared.get("status") != "passed" or prepared.get("stage") != "complete":
        raise ValueError("Wait for an actually completed full preparation")
    root = (preparation / "train-capacity" if spec["case"]["task"] == "generation" else
            Path(prepared.get("capacity_path", str(preparation / "capacity"))))
    graph = Path(prepared.get("graph_scan_path", str(preparation / "graph-scan")))
    evidence = verify_capacity_evidence(root, read_json(graph / "probe.json"))
    timings = []
    for worker in evidence["successful_workers"]:
        elapsed, batches = worker["elapsed_seconds"], worker["measured_batches"]
        if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0 or
                type(batches) is not int or batches < 100):
            raise ValueError("Missing finite measured full-capacity training timing")
        timings.append(elapsed / batches)
    return max(timings) * math.ceil(spec["counts"]["train"] / evidence["common_batch_size"]) * spec["case"]["config"]["epochs"]


def request_script(arguments, *, repository=None, cpu_only=False):
    repository = Path(repository).resolve() if repository is not None else Path.cwd().resolve()
    return ("#!/bin/bash\nset -euo pipefail\ncd " + shlex.quote(str(repository)) + "\n" +
            "export PYTHONPATH=" + shlex.quote(str(repository / "src")) + " PYTHONNOUSERSITE=1\n" +
            "export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8\n" +
            ('export CUDA_VISIBLE_DEVICES=""\n' if cpu_only else "") +
            "exec " + shlex.join([str(value) for value in arguments]) + "\n")


def stage(case, phase, arguments, budget, dependency=None):
    body = request_script(arguments)
    assessment = phase == "assessment"
    return dict(key=case["id"] + ":" + phase, case_id=case["id"], phase=phase,
                depends_on=dependency, script=body, request_sha256=hashlib.sha256(body.encode()).hexdigest(),
                resources=dict(partition="compute", node="node42", gpus=0 if assessment else 1,
                               cpus_per_task=2, memory_gib=8 if assessment else 64,
                               time=slurm_duration(budget), budget_seconds=budget))


def build_submission_plan(matrix, pair_id, preparation, *, matrix_path):
    """Slurm-only read-only plan. Existing cases are marked, never rerun here."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Pair gate/submission must run through Slurm")
    cases = [case for case in matrix["cases"] if case["pair_id"] == pair_id]
    if len(cases) != 2 or {case["initialization"] for case in cases} != {"pretrained", "scratch"}:
        raise ValueError("Select one complete frozen initialization pair")
    cases.sort(key=lambda case: case["initialization"] != "pretrained")
    generation = cases[0]["task"] == "generation"
    specs = [case_spec(matrix, case["id"], allow_generation=generation) for case in cases]
    if canonical_digest(read_json(matrix_path)) != specs[0]["matrix_sha256"]:
        raise ValueError("On-disk matrix differs from the checked complete144 definition")
    environments = {"cgcnn": "universal-official", "alignn": "universal-official",
                    "mace": "universal-mace", "nequip": "universal"}
    if any(case["python_environment"] != environments[case["model"]] or
           Path(sys.prefix).name != environments[case["model"]] for case in cases):
        raise ValueError("Run the CPU gate in this original provider's Python environment")
    maximum = partition_maximum()
    estimate = measured_train_estimate(preparation, specs[0])
    train_budget = finite_budget(estimate, maximum)
    gates = {}
    for case in cases:
        gate = check_preparation(matrix, case["id"], preparation, budget_seconds=train_budget,
                                 allow_generation=generation)
        if not math.isclose(gate["probed_train_only_seconds"], estimate, rel_tol=1e-14):
            raise ValueError("Budget estimate disagrees with the complete verified gate")
        gates[case["initialization"]] = gate
    commits = {gate["git_commit"] for gate in gates.values()}
    if len(commits) != 1:
        raise ValueError("Both initialization gates require the same fixed source")
    commit = commits.pop()
    matrix_path = str(Path(matrix_path).resolve())
    interpreter = str(Path(sys.executable).absolute())
    stages = []
    for case in cases:
        common = [matrix_path, "--matrix-sha256", specs[0]["matrix_sha256"], "--case", case["id"]]
        train = [interpreter, "scripts/run_generation_case.py" if generation else "scripts/run_formal_case.py",
                 *common, "--preparation", str(preparation), "--budget-seconds", str(train_budget)]
        if generation:
            train += ["--stage", "train"]
        stages.append(stage(case, "train", train, train_budget))
        if generation:
            gate = gates[case["initialization"]]
            quality_budget = finite_budget(gate["probed_sample_batch_seconds"] * 1000, maximum)
            quality = [interpreter, "scripts/run_generation_case.py", *common, "--stage", "quality",
                       "--budget-seconds", str(quality_budget)]
            stages.append(stage(case, "quality", quality, quality_budget, case["id"] + ":train"))
            if maximum is not None and maximum < 14400:
                raise ValueError("The independent CPU assessment allocation needs four hours")
            assessment = [interpreter, "scripts/assess_generation_quality.py", "--matrix", matrix_path,
                          "--matrix-sha256", specs[0]["matrix_sha256"], "--case", case["id"],
                          "--output", "runs/arxiv-v1/assessments/" + case["id"]]
            stages.append(stage(case, "assessment", assessment, 14400, case["id"] + ":quality"))
    provenance = dict(matrix_sha256=specs[0]["matrix_sha256"], pair_id=pair_id,
                      preparation=str(Path(preparation).resolve()), preparation_sha256=file_sha(Path(preparation) / "report.json"),
                      git_commit=commit, python=interpreter,
                      configs={mode: canonical_digest(gate["config"]) for mode, gate in gates.items()},
                      stages=[{k: value for k, value in item.items() if k != "script"} for item in stages])
    return dict(status="checked", kind="formal_pair_submission_plan", pair_id=pair_id,
                provenance=provenance, fingerprint=canonical_digest(provenance), cases=cases, gates=gates, stages=stages,
                partition_maximum_seconds=maximum, probed_train_only_seconds=estimate,
                existing_case_paths={case["id"]: Path(case["run_directory"]).exists() or Path(case["run_directory"]).is_symlink() for case in cases},
                formal_training_runs_submitted=0,
                interpretation="Read-only full gates and finite resource plans. Generation quality remains1000/5/456/100x2. Independent scientific acceptance is separate")
