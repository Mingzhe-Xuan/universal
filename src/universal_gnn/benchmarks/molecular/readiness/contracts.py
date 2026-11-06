"""Pure checks joining complete CUDA preparation and original CPU comparisons."""

import re

from ...experiments.registry import canonical_digest
from ..source import COUNTS


def checked_capacity(report, graph, spec):
    if (type(report.get("version")) is not int or report.get("version") != 1 or report.get("kind") != "molecular_cuda_capacity_and_physics"
            or report.get("status") != "passed" or report.get("stage") != "cuda_capacity_and_physics_only"
            or report.get("model") != spec["model"] or report.get("counts") != COUNTS
            or report.get("definition_sha256") != spec["definition_sha256"] or report.get("cuda_capacity") is not True
            or type(report.get("formal_training_runs")) is not int or report["formal_training_runs"] != 0
            or report.get("formal_training_ready") is not False or report.get("original_package_parity_verified") is not False
            or report.get("slurm_job_id") != graph.get("slurm_job_id")
            or report.get("git_commit") != graph.get("git_commit")
            or not re.fullmatch(r"[0-9a-f]{64}", report.get("graph_report_sha256", ""))):
        raise ValueError("Require the complete original CUDA capacity/physics subset")
    common = report.get("common_batch_size")
    if type(common) is not int or not 1 <= common <= spec["reference_config"]["batch_size"]:
        raise ValueError("Common batch can only retain or decrease the frozen initial size")
    if type(report.get("allocation", {}).get("gpus")) is not int or report["allocation"]["gpus"] < 1:
        raise ValueError("Capacity must retain its actual GPU allocation")
    return common


def checked_probe(probe, rebuilt, graph):
    expected = dict(rebuilt)
    expected["coverage"] = dict(rebuilt["coverage"], verified_full_training_scan=True,
        complete_source_graphs=100000, kind="complete_molecular_source_and_training_native_graphs",
        geometry_scope="all_source_and_source_ordered_train", device=graph["device"],
        verified_full_cuda_training_scan=True, model_forward_executed=False,
        graph_definition=graph["graph_definition"], scan_slurm_job_id=graph["slurm_job_id"])
    if (probe != expected or probe.get("measure_batches", 0) < 100 or probe.get("warmup_batches", 0) < 2
            or canonical_digest(probe) != graph["probe_sha256"]):
        raise ValueError("Require the original complete CUDA probe with100 measured batches and two warmups")
    return probe


def checked_capacity_summary(report, evidence):
    summary = {key: value for key, value in evidence.items() if key != "successful_workers"}
    if report.get("capacity_evidence") != summary or report.get("common_batch_size") != evidence.get("common_batch_size"):
        raise ValueError("Retained capacity summary differs from the complete original worker chain")
