"""Molecular CUDA graph/capacity/physics subset; original parity is a separate gate."""

import getpass
import copy
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from ..execution.gates import compatible_sources, read_json, file_sha, checked_config, check_artifact_identity
from ..execution.slurm import running_gpu_allocation
from ..pairing.capacity import run_paired_capacity
from ..pairing.evidence import verify_capacity_evidence
from ..preflight import run_preflight, write_json
from ..preparation.specification import physical_indices
from .contracts import selected_group, checked_graph_metadata, PRIMARY_PATH
from .graphs import scan_molecular_graphs
from .schedule import checked_mixed_capacity


WORKER = "universal_gnn.benchmarks.molecular.worker"


def device_context(model):
    environments = dict(cgcnn="universal-official", alignn="universal-official", mace="universal-mace",
                        nequip="universal", custom_knn_gcn="universal-official")
    if Path(sys.prefix).name != environments[model]:
        raise RuntimeError("Use the registered molecular provider environment")
    commit = compatible_sources([])
    raw = subprocess.check_output(["scontrol", "show", "job", "-o", os.environ["SLURM_JOB_ID"]], text=True)
    fields = dict(token.split("=", 1) for token in shlex.split(raw) if "=" in token)
    allocation = running_gpu_allocation(fields, job_id=os.environ["SLURM_JOB_ID"], user=getpass.getuser())
    return dict(git_commit=commit, source_checkout=str(Path.cwd().resolve()), python=sys.executable,
                slurm_job_id=os.environ["SLURM_JOB_ID"], allocation=allocation)


def single_worker_evidence(directory, probe):
    """Check the plugin's single-initialization retained preflight, including typed OOM."""
    directory = Path(directory)
    report = read_json(directory / "report.json")
    if report.get("status") != "passed" or report.get("passed") is not True or report.get("probe") != probe:
        raise ValueError("Plugin capacity receipt belongs to a failed or different probe")
    batch = report["initial_batch_size"]
    attempts = report.get("attempts", [])
    if not attempts:
        raise ValueError("Plugin capacity lacks retained attempts")
    worker = None
    for index, attempt in enumerate(attempts):
        target = Path(attempt["directory"]).resolve()
        if not target.is_relative_to(directory.resolve()):
            raise ValueError("Plugin attempt escaped its capacity directory")
        request = read_json(target / "request.json")
        worker = read_json(target / "result.json")
        if (worker != attempt.get("worker") or attempt.get("batch_size") != batch
                or request.get("config") != dict(report["config"], batch_size=batch)
                or request.get("probe") != probe or request.get("phase") != "train"
                or worker.get("batch_size") != batch or worker.get("phase") != "train"):
            raise ValueError("Plugin retained request/worker identity differs")
        if index + 1 < len(attempts):
            if (batch <= 1 or attempt.get("returncode") != 42 or attempt.get("status") != "cuda_oom"
                    or worker.get("status") != "cuda_oom" or worker.get("error_type") != "cuda_out_of_memory"):
                raise ValueError("Only typed CUDA OOM may shrink the plugin batch")
            batch = max(1, batch // 2)
        elif attempt.get("returncode") != 0 or attempt.get("status") != "passed" or worker.get("status") != "passed":
            raise ValueError("Plugin capacity did not finish successfully")
    if batch != report.get("final_batch_size"):
        raise ValueError("Plugin final batch differs from its last retained worker")
    return dict(common_batch_size=batch, successful_workers=[worker], successful_worker_count=1,
                trial_count=1, cuda_oom_attempts=len(attempts) - 1)


def validate_workers(evidence, probe):
    common = evidence["common_batch_size"]
    workers = evidence["successful_workers"]
    if not workers:
        raise ValueError("Molecular capacity lacks measured workers")
    for worker in workers:
        base = worker.get("base_capacity", {})
        if (worker.get("version") != 1 or worker.get("status") != "passed" or worker.get("stage") != "complete"
                or worker.get("phase") != "train" or worker.get("worker_kind") != "molecular_homogeneous_and_mixed_v1"
                or worker.get("selected_training_structures") != 900 or worker.get("coverage") != probe["coverage"]
                or worker.get("completed_worst_indices") != probe["worst_indices"]
                or worker.get("all_declared_worst_cases_completed") is not True
                or type(base.get("measured_batches")) is not int or base["measured_batches"] < probe["measure_batches"]):
            raise ValueError("Molecular worker lacks original full-sized homogeneous CUDA coverage")
        checked_mixed_capacity(worker.get("mixed_capacity"), probe, worker["batch_size"], require_cuda=True)
        if (worker["measured_batches"] != base["measured_batches"] + worker["mixed_capacity"]["measured_batches"]
                or worker["measured_structures"] != base["measured_structures"] + worker["mixed_capacity"]["measured_structures"]):
            raise ValueError("Molecular worker aggregate counts differ from the measured phases")
    return common


def physical_checks(config, probe):
    from universal_gnn.engine.training import dataset
    from ..preparation.runtime import derivatives
    structures = dataset(config)
    chosen = physical_indices(probe, len(structures))
    return derivatives([structures[index] for index in chosen], config)


def prepare_molecular_capacity(model, output, *, timeout=7200):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Molecular CUDA preparation must run through Slurm")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Use a finite positive per-worker timeout")
    spec = selected_group(model)
    context = device_context(model)
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB disk reserve")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version=1, kind="molecular_cuda_capacity_and_physics", status="running", model=model,
        stage="complete_cuda_inputs", **context, counts=spec["counts"], definition_sha256=spec["definition_sha256"],
        formal_training_runs=0, formal_training_ready=False, original_package_parity_verified=False)
    def record(**fields):
        report.update(fields)
        write_json(output / "report.json", report)
    record()
    try:
        graph = scan_molecular_graphs(model, output / "graph-scan", device="cuda")
        checked_graph_metadata(graph, spec, require_cuda=True)
        probe = read_json(output / "graph-scan" / "probe.json")
        if probe.get("coverage", {}).get("verified_full_cuda_training_scan") is not True:
            raise ValueError("CPU graph coverage cannot certify molecular CUDA capacity")
        configs = {mode: read_json(output / "graph-scan" / ("config." + mode + ".json")) for mode in spec["configs"]}
        record(stage="paired_homogeneous_and_mixed_capacity", graph_report_sha256=file_sha(output / "graph-scan" / "report.json"))
        if spec["official"]:
            capacity = run_paired_capacity(configs, output / "capacity", probe=probe, timeout=timeout, worker_module=WORKER)
            if capacity.get("passed") is not True:
                raise ValueError("Paired molecular capacity failed")
            evidence = verify_capacity_evidence(output / "capacity", probe)
            resolved = {mode: read_json(output / "capacity" / ("config." + mode + ".resolved.json")) for mode in configs}
        else:
            capacity = run_preflight(configs["scratch"], output / "capacity", probe=probe, timeout=timeout, worker_module=WORKER)
            if capacity.get("passed") is not True:
                raise ValueError("Plugin molecular capacity failed")
            evidence = single_worker_evidence(output / "capacity", probe)
            resolved = {"scratch": read_json(output / "capacity" / "config.resolved.json")}
        common = validate_workers(evidence, probe)
        if type(common) is not int or not 1 <= common <= spec["reference_config"]["batch_size"]:
            raise ValueError("Capacity can only retain or decrease the frozen initial batch")
        for mode, config in resolved.items():
            if spec["official"]:
                checked_config(config, spec["configs"][mode], common, spec["counts"])
            else:
                original = copy.deepcopy(config)
                original["batch_size"] = spec["configs"][mode]["batch_size"]
                if original != spec["configs"][mode] or config["batch_size"] != common:
                    raise ValueError("Plugin capacity changed its recipe beyond batch size")
        if spec["official"]:
            artifacts = read_json(PRIMARY_PATH)["registry"]["artifacts"][model]["files"]
            for worker in evidence["successful_workers"]:
                official = worker["execution"]["official"]
                check_artifact_identity(official, graph["graph_definition"]["native_graph"], artifacts, model)
                coverage = 0. if official["initialization"] == "scratch" else 1.
                if official.get("parameter_coverage") != coverage or official.get("buffer_coverage") != coverage:
                    raise ValueError("Molecular worker must preserve whole official initialization coverage")
                if coverage == 0. and official.get("state_layout_verified") is not True:
                    raise ValueError("Molecular scratch must preserve the original model layout")
        record(stage="worst_input_cuda_physics", common_batch_size=common,
               capacity_evidence={key: value for key, value in evidence.items() if key != "successful_workers"})
        for mode, config in resolved.items():
            validation = physical_checks(config, probe)
            write_json(output / ("physics." + mode + ".json"), validation)
            if (validation.get("passed") is not True or validation.get("dtype") != "torch.float32"
                    or not str(validation.get("device", "")).startswith("cuda")
                    or any(not validation.get("checks", {}).get(key, {}).get("required") for key in [
                        "forces_finite_difference", "stress_finite_difference"])
                    or any(not row["passed"] for row in validation["checks"].values() if row["required"])):
                raise ValueError("Both original molecular forcefield derivative checks must pass on CUDA")
            write_json(output / ("config." + mode + ".resolved.json"), config)
        record(status="passed", stage="cuda_capacity_and_physics_only", cuda_capacity=True,
               interpretation="CompleteCUDAinputs/900trainStats/homogeneous100+mixed100/commonbatch/applicablephysics. Originalpackageparity remains separate; no formaltraining/99000quality acceptance.")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error))
        raise
