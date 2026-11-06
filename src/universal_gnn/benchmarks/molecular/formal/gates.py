"""Read real retained joint preparation before allocating or executing a full case."""

import importlib.metadata
import math
import os
from pathlib import Path
import subprocess
import sys

from ...execution.gates import checked_config, compatible_sources, file_sha, read_json
from ...pairing.evidence import verify_capacity_evidence
from ..capacity import single_worker_evidence, validate_workers
from ..contracts import DEFINITION_SHA
from ..parity.runtime import ENVIRONMENTS
from ..readiness.evidence import Evidence, successful_parent
from .contracts import selected_case, execution_budget


def check_execution_gate(identifier, preparation, terminal, *, budget_seconds=None, maximum=None):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Molecular formal gates require Slurm")
    spec = selected_case(identifier)
    if Path(sys.prefix).name != ENVIRONMENTS[spec["model"]]:
        raise ValueError("Use the registered original provider environment")
    evidence = Evidence()
    preparation = evidence.path(preparation)
    path = preparation / "report.json"
    saved = evidence.read(path)
    modes = set(spec["configs"])
    if (saved.get("version") != 1 or saved.get("kind") != "joint_molecular_preparation_evidence"
            or saved.get("status") != "passed" or saved.get("preparation_gate_passed") is not True
            or saved.get("formal_training_ready") is not False or saved.get("formal_training_runs") != 0
            or saved.get("model") != spec["model"] or saved.get("counts") != spec["counts"]
            or saved.get("definition_sha256") != DEFINITION_SHA or set(saved.get("initializations", [])) != modes
            or not saved.get("input_sha256") or not saved.get("versions")):
        raise ValueError("Wait for actual complete joint CUDA/physics/original-reference preparation")
    successful_parent(evidence, terminal, path)
    commit = compatible_sources([saved["git_commit"], saved["capacity_parent"]["git_commit"], saved["parity_parent"]["git_commit"]])
    changes = subprocess.check_output(["git", "diff", "--name-only", saved["git_commit"], commit,
        "--", "src/universal_gnn/benchmarks/molecular/readiness"], text=True).splitlines()
    if any(name.endswith(".py") for name in changes):
        raise ValueError("Original joint verifier changed after the accepted preparation")
    for name, expected in saved["versions"].items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != expected:
            raise ValueError("Original provider package versions changed")
    for name, expected in saved["input_sha256"].items():
        if file_sha(name) != expected:
            raise ValueError("Accepted complete joint preparation/source evidence changed")
    capacity = Path(saved["capacity_parent"]["output"])
    probe = evidence.read(capacity / "graph-scan/probe.json")
    workers = (verify_capacity_evidence(capacity / "capacity", probe) if spec["official"]
               else single_worker_evidence(capacity / "capacity", probe))
    common = validate_workers(workers, probe)
    if common != saved["common_batch_size"]:
        raise ValueError("Joint common batch differs from the original CUDA workers")
    configs = {}
    for mode, expected in spec["configs"].items():
        config = evidence.read(preparation / ("config." + mode + ".resolved.json"))
        if config != evidence.read(capacity / ("config." + mode + ".resolved.json")):
            raise ValueError("Joint exported configuration differs from retained actual CUDA preparation")
        if spec["official"]:
            checked_config(config, expected, common, spec["counts"])
        elif dict(config, batch_size=expected["batch_size"]) != expected or config["batch_size"] != common:
            raise ValueError("Plugin recipe changed beyond the checked common batch")
        configs[mode] = config
    budget = execution_budget(spec["case"]["config"], workers, maximum=maximum)
    if budget_seconds is None:
        budget_seconds = budget["budget_seconds"]
    if (type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds)
            or budget_seconds < budget["budget_seconds"] or maximum is not None and budget_seconds > maximum):
        raise ValueError("Allocation must cover the complete finite protocol estimate and reserve")
    graph = evidence.read(capacity / "graph-scan/report.json")
    evidence.unchanged()
    if any(file_sha(name) != expected for name, expected in saved["input_sha256"].items()):
        raise ValueError("Original complete preparation/source bytes changed during gate replay")
    return dict(kind="formal_molecular_execution_gate", case=spec["case"], counts=spec["counts"],
        source_structures=100000, config=configs[spec["case"]["initialization"]], git_commit=commit,
        definition_sha256=DEFINITION_SHA, matrix_sha256=DEFINITION_SHA, preparation=str(capacity),
        joint_preparation=str(preparation), joint_terminal=str(terminal), joint_report_sha256=file_sha(path),
        joint_terminal_sha256=file_sha(terminal), native_graph=graph["graph_definition"]["native_graph"],
        capacity_commit=saved["capacity_parent"]["git_commit"], backbone_cutoff=graph["graph_definition"]["cutoff"],
        budget_seconds=budget_seconds, execution_budget=budget, probed_execution_seconds=budget["estimated_execution_seconds"],
        input_sha256={**saved["input_sha256"], **evidence.sha256}, formal_training_ready=True,
        formal_training_runs=0, scientific_quality_accepted=False)
