"""Complete original graph reuse plus independent frozen CUDA capacity/physics."""

import copy
import getpass
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

from ..execution.gates import (case_spec, check_preparation, check_artifact_identity, compatible_sources,
                               file_sha, installed_versions, read_json)
from ..execution.slurm import running_gpu_allocation
from ..prediction_assessment.runtime import verify_physics
from ..preflight import run_preflight, write_json
from ..submission.planning import finite_budget, measured_train_estimate, partition_maximum
from .contracts import (DEFINITION_PATH, DEFINITION_SHA, PRIMARY_PATH, frozen_capacity,
                        frozen_config, selected_case)
from .definitions import inspect_frozen_inputs


def _slurm():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Frozen official preparation/checks require Slurm")


def reference_context(spec, reference_preparation, primary_path):
    matrix = read_json(primary_path)
    original = case_spec(matrix, spec["case"]["reference_finetune_case"])
    estimate = measured_train_estimate(reference_preparation, original)
    budget = finite_budget(estimate, partition_maximum())
    gate = check_preparation(matrix, original["case"]["id"], reference_preparation, budget_seconds=budget)
    config = frozen_config(spec, gate)
    if Path(sys.prefix).name != spec["case"]["python_environment"]:
        raise ValueError("Frozen preparation requires the original provider environment")
    original_prepared = read_json(Path(reference_preparation) / "report.json")
    graph_root = Path(original_prepared.get("graph_scan_path", str(Path(reference_preparation) / "graph-scan")))
    probe = read_json(graph_root / "probe.json")
    return matrix, gate, config, probe


def frozen_physics(physics, case, identifiers, *, device):
    if (not str(device).startswith("cuda") or physics.get("structure_ids") != identifiers):
        raise ValueError("Frozen CUDA physics must use the complete original scan's worst two records")
    verify_physics(physics, case["task"], dict(ids=identifiers), device=device, frozen_backbone=True)
    state = physics.get("frozen_state", {})
    before, after = state.get("backbone_state_before_sha256"), state.get("backbone_state_after_sha256")
    if (not isinstance(before, str) or len(before) != 64 or before != after or
            state.get("backbone_gradients_absent") is not True or state.get("frozen_modules_eval") is not True):
        raise ValueError("Frozen physical checks changed original backbone state, modes or gradients")
    return state


def prepare_frozen_case(identifier, reference_preparation, output, *, definitions=DEFINITION_PATH,
                        primary_path=PRIMARY_PATH, timeout=7200):
    _slurm()
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Declare a finite positive per-worker timeout")
    spec = selected_case(identifier, definitions=definitions, primary=primary_path)
    detail = subprocess.check_output(["scontrol", "show", "job", "-o", os.environ["SLURM_JOB_ID"]], text=True)
    fields = dict(token.split("=", 1) for token in shlex.split(detail) if "=" in token)
    allocation = running_gpu_allocation(fields, job_id=os.environ["SLURM_JOB_ID"], user=getpass.getuser())
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB reserve before frozen preparation")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    commit = compatible_sources([])
    report = dict(version=1, kind="full_frozen_backbone_preparation", status="running", stage="original_reference",
        case_id=identifier, definition_sha256=DEFINITION_SHA, git_commit=commit, slurm_job_id=os.environ["SLURM_JOB_ID"],
        reference_preparation=str(reference_preparation), gpu_allocation=allocation,
        formal_training_runs=0, formal_training_launched=False, frozen_training_ready=False, cuda_acceptance=False)
    def record(**values):
        report.update(values, updated_at=time.time());write_json(output / "report.json", report)
    started = time.perf_counter()
    try:
        record()
        matrix, reference, config, probe = reference_context(spec, reference_preparation, primary_path)
        write_json(output / "reference-gate.json", reference)
        write_json(output / "config.requested.json", config)
        inputs = inspect_frozen_inputs(matrix)
        if inputs != read_json(definitions).get("full_input_audit"):
            raise ValueError("Actual complete frozen source/labels differ from accepted definitions")
        write_json(output / "full-input-audit.json", inputs)
        record(stage="frozen_capacity", counts=spec["counts"], source_structures=spec["source_structures"],
               matched_reference_batch=config["batch_size"])
        capacity = run_preflight(config, output / "capacity", probe=probe, timeout=timeout,
            worker_module="universal_gnn.benchmarks.frozen_backbones.worker")
        if not capacity.get("passed"):
            raise RuntimeError("Frozen capacity failed; preserve attempts, no unknown-error retry")
        checked = frozen_capacity(output / "capacity", config, probe, spec["counts"])
        record(stage="frozen_physics")
        import torch
        from universal_gnn.engine.training import build_model, dataset, execution_record
        from universal_gnn.engine.batching import model_dtype
        from universal_gnn.engine.optimization import FrozenStateGuard, components
        from ..validation.derivatives import validate_derivatives
        from .worker import state_sha

        if not torch.cuda.is_available():
            raise RuntimeError("Frozen preparation requires actual CUDA; no CPU fallback")
        torch.manual_seed(config["seed"])
        model = build_model(config).to(device=config["device"], dtype=model_dtype(config))
        guard = FrozenStateGuard(model)
        before = state_sha(components(model)["backbone"])
        structures = dataset(config)
        indices = probe["worst_indices"][:2]
        if len(indices) != 2 or len(structures) != spec["counts"]["train"]:
            raise ValueError("Frozen physics requires complete source and two original worst records")
        examples = [structures[i] for i in indices]
        physics = validate_derivatives(model, examples, config)
        guard.verify()
        physics["execution"] = execution_record(model)
        physics["frozen_state"] = dict(backbone_state_before_sha256=before,
            backbone_state_after_sha256=state_sha(components(model)["backbone"]),
            backbone_gradients_absent=all(p.grad is None for p in components(model)["backbone"].parameters()),
            frozen_modules_eval=all(not m.training for m in components(model)["backbone"].modules()))
        write_json(output / "physics.json", physics)
        frozen_physics(physics, spec["case"], [s.identifier for s in examples], device=str(next(model.parameters()).device))
        if before != checked["worker"]["frozen_audit"]["backbone_state_before_sha256"]:
            raise ValueError("Frozen capacity and physics instantiated different pretrained backbone states")
        del model, structures
        torch.cuda.empty_cache()
        estimate = checked["seconds_per_batch"] * math.ceil(spec["counts"]["train"] / config["batch_size"]) * config["epochs"]
        budget = finite_budget(estimate, partition_maximum())
        record(status="passed", stage="complete", frozen_training_ready=True, cuda_acceptance=True,
               reference_gate_sha256=file_sha(output / "reference-gate.json"),
               input_audit_sha256=file_sha(output / "full-input-audit.json"),
               physics_sha256=file_sha(output / "physics.json"), config_sha256=file_sha(output / "config.requested.json"),
               capacity_sha256=checked["report_sha256"], probed_train_only_seconds=estimate,
               training_budget_seconds=budget, wall_seconds=time.perf_counter() - started,
               interpretation="Complete original graph reuse and independent frozen100-batch CUDA/physical evidence, at the matched original batch. No official frozen training launched; full trained-best science and independent assessment remain mandatory.")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error));raise


def check_frozen_preparation(identifier, preparation, *, definitions=DEFINITION_PATH,
                             primary_path=PRIMARY_PATH, budget_seconds=None):
    _slurm()
    spec = selected_case(identifier, definitions=definitions, primary=primary_path)
    preparation = Path(preparation);prepared = read_json(preparation / "report.json")
    allocation = prepared.get("gpu_allocation", {})
    if (prepared.get("kind") != "full_frozen_backbone_preparation" or prepared.get("status") != "passed" or
            prepared.get("stage") != "complete" or prepared.get("case_id") != identifier or
            prepared.get("definition_sha256") != DEFINITION_SHA or prepared.get("frozen_training_ready") is not True or
            prepared.get("cuda_acceptance") is not True or
            type(allocation.get("gpus")) is not int or allocation["gpus"] < 1 or
            allocation.get("evidence") not in {"AllocTRES", "TRES", "running_nodes_and_TresPerNode"} or
            allocation.get("node_list") in {None, "", "(null)"} or
            prepared.get("formal_training_runs") != 0 or prepared.get("formal_training_launched") is not False or
            prepared.get("counts") != spec["counts"] or prepared.get("source_structures") != spec["source_structures"]):
        raise ValueError("Wait for the complete separate frozen CUDA preparation")
    matrix, reference, config, probe = reference_context(spec, prepared["reference_preparation"], primary_path)
    old_reference = read_json(preparation / "reference-gate.json")
    if {k: v for k, v in old_reference.items() if k != "git_commit"} != {k: v for k, v in reference.items() if k != "git_commit"}:
        raise ValueError("Complete original reference gate changed")
    for name, key in (("reference-gate.json", "reference_gate_sha256"), ("full-input-audit.json", "input_audit_sha256"),
                      ("physics.json", "physics_sha256"), ("config.requested.json", "config_sha256")):
        if file_sha(preparation / name) != prepared.get(key):
            raise ValueError("Frozen preparation evidence bytes changed")
    if read_json(preparation / "config.requested.json") != config:
        raise ValueError("Frozen preparation changed the one-flag training configuration")
    if read_json(preparation / "full-input-audit.json") != read_json(definitions)["full_input_audit"]:
        raise ValueError("Frozen complete raw source/label audit differs")
    checked = frozen_capacity(preparation / "capacity", config, probe, spec["counts"])
    if checked["report_sha256"] != prepared["capacity_sha256"]:
        raise ValueError("Frozen capacity bytes changed")
    manifest = read_json(config["dataset"]["split_manifest"])
    identifiers = [manifest["records"][manifest["partitions"]["train"][i]]["id"] for i in probe["worst_indices"][:2]]
    physics = read_json(preparation / "physics.json")
    frozen_physics(physics, spec["case"], identifiers, device=config["device"] if ":" in config["device"] else config["device"] + ":0")
    if physics["frozen_state"]["backbone_state_before_sha256"] != checked["worker"]["frozen_audit"]["backbone_state_before_sha256"]:
        raise ValueError("Frozen physics/capacity backbone bytes differ")
    versions = installed_versions()
    worker = checked["worker"]
    if any(worker.get("versions", {}).get(key) != value for key, value in versions.items()):
        raise ValueError("Frozen capacity provider environment changed")
    definition = probe["coverage"]["graph_definition"]
    for execution in (worker["execution"], physics["execution"]):
        official = execution["official"]
        if official.get("initialization") != "pretrained" or official.get("parameter_coverage") != 1.:
            raise ValueError("Frozen models must retain the complete original pretrained body")
        check_artifact_identity(official, definition, matrix["registry"]["artifacts"][spec["case"]["model"]]["files"], spec["case"]["model"])
    commit = compatible_sources([prepared["git_commit"], reference["git_commit"], old_reference["git_commit"],
                                  worker["execution"]["git_commit"], physics["execution"]["git_commit"]])
    estimate = checked["seconds_per_batch"] * math.ceil(spec["counts"]["train"] / config["batch_size"]) * config["epochs"]
    if budget_seconds is None: budget_seconds = finite_budget(estimate, partition_maximum())
    if (type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or budget_seconds < 1.5 * estimate or
            estimate != prepared["probed_train_only_seconds"] or config["batch_size"] != prepared["matched_reference_batch"]):
        raise ValueError("Frozen execution budget or matched batch differs from complete measured evidence")
    return dict(status="passed", kind="formal_frozen_backbone_execution_gate", case=spec["case"], config=config,
        counts=spec["counts"], source_structures=spec["source_structures"], matrix_sha256=DEFINITION_SHA,
        primary_sha256=spec["primary_sha256"], definition_sha256=DEFINITION_SHA, git_commit=commit, versions=versions,
        preparation=str(preparation), preparation_sha256=file_sha(preparation / "report.json"),
        common_batch_size=config["batch_size"], backbone_cutoff=reference["backbone_cutoff"],
        physical_evidence_sha256=dict(frozen=file_sha(preparation / "physics.json")),
        frozen_audit=worker["frozen_audit"], capacity_worker_sha256=checked["worker_sha256"],
        reference_gate_sha256=file_sha(preparation / "reference-gate.json"), reference_preparation=prepared["reference_preparation"],
        budget_seconds=budget_seconds, probed_train_only_seconds=estimate,
        interpretation="Frozen preparation gate only; complete head-only training, trained-best heldout/physics/all-source inference and independent no-model acceptance remain separate.")
