"""Full frozen test partitions for matching original public task heads."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from ..experiments.registry import DATASETS, canonical_digest
from ..preflight import write_json


def native_baseline_config(matrix, provider):
    """Keep full source/target conventions; select the matching original task."""
    if provider not in {"cgcnn", "alignn", "mace", "nequip"}:
        raise ValueError("Native baselines cover the four primary original providers")
    if (matrix.get("kind") != "arxiv_v1_primary_matrix" or matrix.get("definition_revision") != 2 or
            matrix.get("registry_sha256") != canonical_digest(matrix.get("registry"))):
        raise ValueError("Require the corrected frozen primary matrix")
    task = "bandgap" if provider in {"cgcnn", "alignn"} else "forcefield"
    candidates = [c for c in matrix["cases"] if c["model"] == provider and c["task"] == task
                  and c["initialization"] == "pretrained" and c["seed"] == 123]
    if len(candidates) != 1:
        raise ValueError("Require one unambiguous original pretrained matching-task case")
    case = candidates[0]
    if canonical_digest(case["config"]) != case["config_sha256"]:
        raise ValueError("Frozen case digest differs")
    config = copy.deepcopy(case["config"])
    expected_source = "jarvis-gap" if task == "bandgap" else "mlearn-forcefield"
    if (config.get("structures") != "all" or config.get("max_atoms") is not None or
            config.get("dtype") != "float32" or config.get("graph") is not None or
            config.get("backbone") != {"name": provider, "implementation": "official", "initialization": "pretrained"} or
            config.get("dataset", {}).get("sha256") != DATASETS[expected_source][0] or
            config["dataset"].get("partition") != "train" or
            not config["dataset"].get("split_manifest_sha256")):
        raise ValueError("Native baseline requires the full original source and graph conventions")
    if task == "bandgap":
        if config["task"] != {"kind": "supervised", "property": "bandgap"}:
            raise ValueError("Bandgap original head requires its matching task")
    elif (config["task"].get("kind") != "forcefield" or
          config["task"].get("supervised_outputs") != ["total_energy", "forces"]):
        raise ValueError("Native forcefield requires total energy and forces")
    config["device"] = "cpu"
    config["dataset"]["partition"] = "test"
    config["prediction"] = {"version": 1, "head_mode": "native"}
    config["optimization"] = {"train_backbone": False, "train_readout": False}
    return dict(config=config, parent_case_id=case["id"], task=task, provider=provider,
                matrix_sha256=canonical_digest(matrix),
                counts=dict(zip(("train", "validation", "test"), DATASETS[expected_source][1])))


def state_digest(model):
    """Hash every persistent tensor, including original head and normalization."""
    import torch

    digest = hashlib.sha256()
    for name, tensor in model.state_dict().items():
        digest.update(json.dumps([name, str(tensor.dtype), list(tensor.shape)], separators=(",", ":")).encode())
        digest.update(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def evaluate_native_baseline(matrix, provider, output):
    """Evaluate every frozen test record under Slurm; never fit or update weights."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Native baseline evaluation must run through Slurm")
    spec = native_baseline_config(matrix, provider)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version=1, kind="official_native_zero_shot_baseline", status="running",
                  provider=provider, task=spec["task"], parent_case_id=spec["parent_case_id"],
                  matrix_sha256=spec["matrix_sha256"], slurm_job_id=os.environ["SLURM_JOB_ID"],
                  git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  config=spec["config"], device="cpu", formal_training_runs=0,
                  parameter_updates=0, fitted_target_statistics=False, target_reference_alignment=False,
                  counts=spec["counts"], native_head_preserved=True)

    def record(**values):
        report.update(values, updated_at=time.time())
        write_json(output / "report.json", report)

    try:
        record(stage="complete_test_partition")
        import resource
        import torch
        from universal_gnn.engine.training import build_model, dataset, execution_record, version_record
        from universal_gnn.engine.evaluation.heldout import score_partition

        config = spec["config"]
        structures = dataset(config)
        manifest = json.loads(Path(config["dataset"]["split_manifest"]).read_text())
        if (len(structures) != spec["counts"]["test"] or
                len(structures.source) != sum(spec["counts"].values()) or
                list(structures.indices) != manifest["partitions"]["test"] or
                any(len(manifest["partitions"][role]) != count for role, count in spec["counts"].items())):
            raise ValueError("Incomplete frozen source or test partition")
        torch.manual_seed(config["seed"])
        model = build_model(config).to(device="cpu", dtype=torch.float32).eval()
        if any(p.requires_grad for p in model.parameters()):
            raise ValueError("Native baseline must freeze every model component")
        before = state_digest(model)
        sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
        from validate_official import independent_reference

        parity = independent_reference(model.backbone, [structures[0], structures[1]], config)
        if state_digest(model) != before:
            raise RuntimeError("Original-head parity changed model state")
        scales = {name: 1. for name in (["total_energy", "forces"] if spec["task"] == "forcefield" else ["bandgap"])}
        record(stage="complete_native_test_evaluation", original_prediction_parity=parity,
               state_sha256_before=before, execution=execution_record(model), versions=version_record())
        started = time.perf_counter()
        scored = score_partition(model, structures, config, scales, output / "test", metadata=dict(
            partition="test", checkpoint_role="official_pretrained_native_no_selection",
            source_sha256=config["dataset"]["sha256"], manifest_sha256=config["dataset"]["split_manifest_sha256"]))
        elapsed = time.perf_counter() - started
        after = state_digest(model)
        if after != before:
            raise RuntimeError("Native test evaluation changed model state")
        expected_ids = [manifest["records"][i]["id"] for i in manifest["partitions"]["test"]]
        seen, prediction_hash = [], hashlib.sha256()
        with Path(scored["predictions"]).open("rb") as stream:
            for raw in stream:
                prediction_hash.update(raw)
                seen.append(json.loads(raw)["id"])
        if seen != expected_ids or scored["structures"] != len(expected_ids):
            raise RuntimeError("Native predictions do not cover every frozen ordered test ID")
        record(status="passed", stage="complete", heldout=scored, state_sha256_after=after,
               all_ordered_test_ids_verified=True, predictions_sha256=prediction_hash.hexdigest(),
               test_inference_and_scoring_wall_seconds=elapsed,
               peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
               interpretation="Original public weights/head/normalization, no training or target shift. Test IDs use the main frozen partition. Pretraining material exposure and target/reference conventions differ: raw unshifted metrics are a native transfer baseline, not a leak-free or matched-DFT ranking. Unit aggregation scales do not alter predictions; CPU cost is separate from GPU training.")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error))
        raise
