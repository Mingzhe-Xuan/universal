"""Bind full original graphs, paired capacity and applicable CUDA physical checks."""

import math
import os
from pathlib import Path
import shutil
import time

from ..execution.gates import checked_config, check_preparation, read_json
from ..pairing.evidence import verify_capacity_evidence
from ..preflight import write_json
from ..submission.planning import finite_budget
from .specification import predictive_spec, runtime_context, full_manifest, physical_indices
from . import runtime


def prepare_predictive_pair(matrix, pair_id, output, *, timeout=7200):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Full predictive preparation must run through Slurm")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Require a finite positive per-worker timeout")
    spec = predictive_spec(matrix, pair_id)
    context = runtime_context(spec)
    output = Path(output)
    if any(Path(case["run_directory"]).exists() or
           Path("runs/arxiv-v1/launches", case["id"]).exists() for case in spec["cases"]):
        raise FileExistsError("A primary result or launch claim already owns this pair")
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB disk reserve")
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = dict(version=1, kind="full_predictive_pair_preparation", status="running", stage="frozen_inputs",
                  pair_id=pair_id, model=spec["model"], task=spec["task"], seed=spec["seed"],
                  matrix_sha256=spec["matrix_sha256"], counts=spec["counts"], **context,
                  formal_training_runs=0, formal_training_launched=False)
    def record(**fields):
        report.update(fields, updated_at=time.time())
        write_json(output / "report.json", report)
    try:
        record()
        manifest = full_manifest(spec)
        configs = spec["configs"]
        for mode, config in configs.items():
            write_json(output / ("input-" + mode + ".json"), config)
        structures = runtime.load_training(configs["pretrained"])
        if (len(structures) != spec["counts"]["train"] or len(structures.source) != spec["source_structures"] or
                list(structures.indices) != manifest["partitions"]["train"]):
            raise ValueError("Training loader does not cover the complete ordered frozen partition")
        record(stage="original_prediction_parity")
        parity = runtime.native_parity(structures, configs["pretrained"])
        if not isinstance(parity, dict) or parity.get("structures") != 2:
            raise ValueError("Original package parity must cover both declared examples")
        record(stage="full_original_training_graph_scan", native_parity=parity,
               parity_scope="Original package features/head; CGCNN CSV labels are unused reference-reader-only copies")
        probe = runtime.graph_scan(configs["pretrained"], output / "graph-scan")
        if not probe["coverage"].get("verified_full_training_scan") or probe["coverage"].get("structures") != len(structures):
            raise ValueError("Missing complete original/auxiliary training graph scan")
        record(stage="full_data_paired_capacity")
        capacity = runtime.paired_capacity(configs, output / "capacity", probe, timeout)
        if not capacity.get("passed"):
            raise RuntimeError("Full paired capacity failed; preserve every original worker attempt")
        evidence = verify_capacity_evidence(output / "capacity", probe)
        common = evidence["common_batch_size"]
        resolved = {}
        for mode in ("pretrained", "scratch"):
            actual = read_json(output / "capacity" / ("config." + mode + ".resolved.json"))
            checked_config(actual, configs[mode], common, spec["counts"])
            resolved[mode] = actual
        if spec["task"] in {"forcefield", "dielectric"}:
            chosen = physical_indices(probe, len(structures))
            record(stage="worst_structure_physical_acceptance", physical_training_indices=chosen,
                   common_batch_size=common)
            mandatory = ("forces_finite_difference", "stress_finite_difference") if spec["task"] == "forcefield" else (
                "response_auxiliary_finite_difference",)
            for mode in ("pretrained", "scratch"):
                validation = runtime.derivatives([structures[i] for i in chosen], resolved[mode])
                write_json(output / ("derivatives-" + mode + ".json"), validation)
                if (not validation.get("passed") or validation.get("dtype") != "torch.float32" or
                        not str(validation.get("device", "")).startswith("cuda") or
                        any(not validation.get("checks", {}).get(key, {}).get("required") for key in mandatory) or
                        any(not c["passed"] for c in validation.get("checks", {}).values() if c["required"])):
                    raise ValueError("Both modes require passed original worst-input CUDA physical checks")
        slowest = max(worker["elapsed_seconds"] / worker["measured_batches"] for worker in evidence["successful_workers"])
        estimate = slowest * math.ceil(len(structures) / common) * configs["pretrained"]["epochs"]
        record(status="passed", stage="complete", cuda_acceptance=True, final_gate_check_pending=True,
               common_batch_size=common, final_configs=capacity["final_configs"],
               capacity_evidence={k: value for k, value in evidence.items() if k != "successful_workers"},
               resource_estimate=dict(probed_seconds_per_batch=slowest, train_only_300_epoch_seconds=estimate))
        gates = {}
        for case in spec["cases"]:
            gate = check_preparation(matrix, case["id"], output, budget_seconds=finite_budget(estimate))
            if gate["git_commit"] != context["git_commit"]:
                raise ValueError("Final full gate executed under a different source checkout")
            gates[case["initialization"]] = dict(status=gate["status"], common_batch_size=gate["common_batch_size"])
        record(final_gate_check_pending=False, final_full_gates=gates, elapsed_seconds=time.perf_counter() - started,
               interpretation="Complete source/original graph/paired100-batch/native calibration/applicable CUDA physics and both full mode gates. No formal training or scientific accuracy acceptance")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error))
        raise
