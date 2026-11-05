"""Execute a new full predictive case without modifying its scientific recipe."""

import copy
import getpass
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import time

from .gates import check_preparation, case_spec, file_sha, read_json, canonical_digest
from ..preflight import write_json
from .slurm import running_gpu_allocation


def duration_seconds(value):
    days, separator, clock = value.partition("-")
    if not separator:
        days, clock = "0", days
    parts = clock.split(":")
    if len(parts) != 3 or not days.isdigit() or any(not p.isdigit() for p in parts):
        raise ValueError("Require Slurm D-HH:MM:SS or HH:MM:SS duration")
    hours, minutes, seconds = map(int, parts)
    if minutes >= 60 or seconds >= 60:
        raise ValueError("Invalid Slurm duration")
    return int(days) * 86400 + hours * 3600 + minutes * 60 + seconds


def allocation_budget(requested, estimate):
    if (type(requested) not in (int, float) or not math.isfinite(requested) or requested <= 0 or
            type(estimate) not in (int, float) or not math.isfinite(estimate) or estimate <= 0):
        raise ValueError("Require finite positive requested and measured wall-time budgets")
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal execution requires a running Slurm job")
    detail = subprocess.check_output(["scontrol", "show", "job", "-o", os.environ["SLURM_JOB_ID"]], text=True)
    fields = dict(token.split("=", 1) for token in shlex.split(detail) if "=" in token)
    running_gpu_allocation(fields, job_id=os.environ["SLURM_JOB_ID"], user=getpass.getuser())
    remaining = requested if fields.get("TimeLimit") == "UNLIMITED" else (
        duration_seconds(fields["TimeLimit"]) - duration_seconds(fields["RunTime"]))
    effective = min(requested, remaining)
    if effective < 1.5 * estimate:
        raise RuntimeError("Remaining Slurm wall time lacks measured training budget plus50% reserve")
    return effective


def same_runtime_config(actual, expected, cutoff):
    """Allow only the runtime's documented explicit default normalization."""
    actual, expected = copy.deepcopy(actual), copy.deepcopy(expected)
    actual.pop("resolved_components", None)
    expected["dataset"].setdefault("selection", "first")
    expected["dataset"].setdefault("selection_seed", expected["seed"])
    prediction = expected["prediction"]
    prediction.setdefault("adapter", {"name": "none", "version": 1})
    prediction["adapter"].setdefault("version", 1)
    readout = prediction["readout"]
    if readout["name"] in {"graph_mlp", "node_mlp"}:
        readout.setdefault("bias", True)
    processing = readout.setdefault("feature_processing", {"name": "none"})
    processing.setdefault("version", 1)
    if processing["name"] == "equivariant":
        processing.setdefault("cutoff", cutoff)
    if actual != expected:
        raise ValueError("Training changed the prepared recipe beyond documented normalization defaults")


def finite_shape(values, shape):
    if not shape:
        if isinstance(values, bool) or not isinstance(values, (int, float)) or not math.isfinite(values):
            raise ValueError("Nonfinite or nonnumeric heldout prediction/target")
        return
    if not isinstance(values, list) or len(values) != shape[0]:
        raise ValueError("Heldout prediction/target shape differs from the task contract")
    for value in values:
        finite_shape(value, shape[1:])


def verify_training_report(trained, gate, events, *, frozen_backbone=False):
    """Verify full epoch/selection/test coverage; do not claim independent source re-score."""
    config, counts = gate["config"], gate["counts"]
    epochs = trained.get("completed_epochs")
    if type(frozen_backbone) is not bool:
        raise ValueError("Declare an explicit backbone training policy")
    if frozen_backbone:
        from ..frozen_backbones.contracts import DEFINITION_SHA

        case = gate["case"]
        if (gate.get("kind") != "formal_frozen_backbone_execution_gate" or
                gate.get("definition_sha256") != DEFINITION_SHA or
                case.get("model") not in {"cgcnn", "alignn", "mace", "nequip"} or
                case.get("task") not in {"forcefield", "dielectric"} or case.get("seed") != 123 or
                case.get("id") != "frozen--seed-123--" + case["task"] + "--" + case["model"] or
                case.get("initialization") != "pretrained" or
                config.get("optimization", {}).get("train_backbone") is not False or
                config.get("optimization", {}).get("train_readout") is not True):
            raise ValueError("Zero-backbone gradients are restricted to the closed frozen ablation")
        norms = trained.get("gradient_norms", [])
        if (len(norms) != epochs or any(type(g) not in (int, float) or not math.isfinite(g) or g <= 0 for g in norms)):
            raise ValueError("Frozen training requires positive active-component gradients in every epoch")
        for key in ("components", "components_during_training"):
            body = trained.get(key, {}).get("backbone", {})
            head = trained.get(key, {}).get("readout", {})
            if (body.get("trainable_parameters") != 0 or body.get("mode") != "eval" or
                    body.get("module_modes", {}).get("train") != 0 or
                    head.get("trainable_parameters", 0) <= 0 or
                    key == "components_during_training" and head.get("mode") != "train"):
                raise ValueError("Frozen body or active readout mode/parameter policy changed")
    if (not trained.get("passed") or not trained.get("checkpoint_reload") or
            type(epochs) is not int or not 1 <= epochs <= config["epochs"] or
            trained.get("requested_epochs") != config["epochs"] or
            trained.get("selected_structures") != counts["train"] or
            trained.get("available_structures") != gate["source_structures"] or
            trained.get("resume") != {"path": None, "kind": "none", "completed_epochs_before": 0} or
            len(trained.get("history", [])) != epochs or len(trained.get("backbone_gradient_norms", [])) != epochs or
            any(type(g) not in (int, float) or not math.isfinite(g) or
                (g != 0. if frozen_backbone else g <= 0) for g in trained["backbone_gradient_norms"])):
        raise ValueError("Missing full fresh training coverage or original-backbone gradients")
    same_runtime_config(trained["config"], config, gate["backbone_cutoff"])
    reload = trained.get("reload_verification", {})
    if not reload.get("state_exact") or not reload.get("deterministic_algorithms"):
        raise ValueError("Exact state and deterministic checkpoint reload are required")
    official = trained["execution"]["official"]
    if official.get("initialization") != gate["case"]["initialization"]:
        raise ValueError("Actual backbone initialization differs")
    if official["initialization"] == "scratch":
        if official.get("parameter_coverage") != 0. or official.get("buffer_coverage") != 0. or not official.get("state_layout_verified"):
            raise ValueError("Actual scratch inherited source state or changed original layout")
    elif official.get("parameter_coverage") != 1.:
        raise ValueError("Actual pretrained model did not load all original parameters")
    train = [row for row in events if row["event"] == "epoch"]
    validation = [row for row in events if row["event"] == "validation"]
    if (len(train) != epochs or len(validation) != epochs or
            [r["epoch"] for r in train] != list(range(1, epochs + 1)) or
            any(r["structures"] != counts["train"] or r["minibatches"] != math.ceil(counts["train"] / config["batch_size"]) for r in train) or
            any(r["structures"] != counts["validation"] for r in validation)):
        raise ValueError("Not every complete training/validation epoch was recorded")
    held = trained["heldout"]
    if (held.get("structures") != counts["test"] or held.get("test_structures") != counts["test"] or
            held.get("validation_structures") != counts["validation"] or held.get("declared_train_structures") != counts["train"] or
            held.get("source_structures") != gate["source_structures"] or held.get("partition") != "test" or
            held.get("checkpoint_role") != "validation_best" or
            held.get("source_sha256") != config["dataset"]["sha256"]):
        raise ValueError("Incomplete independent validation-best test partition")
    tracker = held["selection"]["tracker"]
    if tracker["manifest_sha256"] != config["dataset"]["split_manifest_sha256"]:
        raise ValueError("Selection was performed against another split")
    if len(tracker["history"]) != epochs or any(r["epoch"] != h["epoch"] or r["loss"] != h["loss"] for r, h in zip(validation, tracker["history"])):
        raise ValueError("Selection history differs from actual complete validation events")
    best = min(tracker["history"], key=lambda row: row["loss"])
    if best["epoch"] != tracker["best_epoch"] or best["loss"] != tracker["best_loss"]:
        raise ValueError("Checkpoint was not the actual minimum validation loss")
    if epochs < config["epochs"] and (not trained.get("early_stopped") or tracker["bad_epochs"] != config["evaluation"]["patience"]):
        raise ValueError("Training ended without the declared early stopping rule")
    if file_sha(trained["best_checkpoint"]) != held["selection"]["best_sha256"]:
        raise ValueError("Validation-best checkpoint bytes changed")
    manifest = read_json(config["dataset"]["split_manifest"])
    if (canonical_digest(manifest) != config["dataset"]["split_manifest_sha256"] or
            file_sha(config["dataset"]["path"]) != config["dataset"]["sha256"]):
        raise ValueError("Full source/split changed during training")
    expected = [manifest["records"][i]["id"] for i in manifest["partitions"]["test"]]
    seen = []
    with Path(held["predictions"]).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            names = ("total_energy", "forces") if gate["case"]["task"] == "forcefield" else (gate["case"]["task"],)
            if set(row["predictions"]) != set(names) or set(row["targets"]) != set(names):
                raise ValueError("Heldout outputs differ from the task")
            for name in names:
                shape = {"bandgap": (1, 1), "classification": (1, 2), "dielectric": (1, 3, 3),
                         "spectrum": (1, 200), "total_energy": (1, 1),
                         "piezoelectric": (1, 3, 3, 3), "elastic": (1, 3, 3, 3, 3)}.get(name)
                if shape is None and name != "forces":
                    raise ValueError("Unsupported heldout output format")
                if name == "forces":
                    if type(row.get("natoms")) is not int or row["natoms"] <= 0:
                        raise ValueError("Missing forcefield atom count")
                    shape = (row["natoms"], 3)
                finite_shape(row["predictions"][name], shape)
                finite_shape(row["targets"][name], (1,) if name == "classification" else shape)
                if name == "classification" and (type(row["targets"][name][0]) is not int or row["targets"][name][0] not in (0, 1)):
                    raise ValueError("Binary class label differs from the frozen protocol")
            seen.append(row["id"])
    if seen != expected or len(seen) != counts["test"]:
        raise ValueError("Saved predictions do not cover every ordered test ID exactly once")
    return dict(completed_epochs=epochs, best_epoch=tracker["best_epoch"], test_structures=len(seen),
                best_checkpoint_sha256=held["selection"]["best_sha256"],
                interpretation="Full training and heldout execution verified; independent raw-source re-score/post-training physics remain separate")


def run_formal_case(matrix, identifier, preparation, *, budget_seconds):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal training must run through Slurm")
    spec = case_spec(matrix, identifier)
    root = Path(spec["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to rerun or overwrite an existing primary case")
    gate = check_preparation(matrix, identifier, preparation, budget_seconds=budget_seconds)
    return _run_prepared_case(identifier, gate, budget_seconds=budget_seconds)


def _run_prepared_case(identifier, gate, *, budget_seconds, training_executor=None, report_verifier=None):
    """Shared executor; callers must independently validate their closed case domain."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal training must run through Slurm")
    root = Path(gate["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to rerun or overwrite an existing formal case")
    effective_budget = allocation_budget(budget_seconds, gate["probed_train_only_seconds"])
    import resource
    import torch
    from universal_gnn.engine.training import run_training

    if not torch.cuda.is_available():
        raise RuntimeError("Required CUDA device is unavailable; no CPU fallback")
    if shutil.disk_usage(root.parent.parent).free < 20 * 1024**3:
        raise RuntimeError("Less than20GiB free disk reserve")
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "execution-gate.json", gate)
    config = gate["config"]
    write_json(root / "config.requested.json", config)
    started = time.perf_counter()
    status = dict(status="running", case_id=identifier, task=gate["case"]["task"],
                  model=gate["case"]["model"], initialization=gate["case"]["initialization"],
                  seed=gate["case"]["seed"], git_commit=gate["git_commit"],
                  matrix_sha256=gate["matrix_sha256"], slurm_job_id=os.environ["SLURM_JOB_ID"],
                  formal_training_runs_completed=0, counts=gate["counts"],
                  wall_budget_seconds=effective_budget, independent_postevaluation_verified=False)

    def record(**values):
        status.update(values, updated_at=time.time())
        write_json(root / "formal-status.json", status)

    def event(name, **values):
        row = dict(event=name, time=time.time(), **values)
        with (root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
        if name == "epoch":
            if values["structures"] != gate["counts"]["train"] or values["minibatches"] != math.ceil(gate["counts"]["train"] / config["batch_size"]):
                raise RuntimeError("A formal epoch did not cover the complete train partition")
            record(last_completed_epoch=values["epoch"], last_training_loss=values["loss"])
            print(json.dumps(dict(event=name, epoch=values["epoch"], loss=values["loss"])), flush=True)
            if shutil.disk_usage(root).free < 20 * 1024**3:
                raise RuntimeError("Disk reserve below20GiB; retain the last committed checkpoint")

    try:
        record(stage="full_training_and_validation")
        torch.cuda.reset_peak_memory_stats()
        train = run_training if training_executor is None else training_executor
        verify = verify_training_report if report_verifier is None else report_verifier
        trained = train(config, root, event_callback=event)
        events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        accepted = verify(trained, gate, events)
        record(status="passed", stage="complete", formal_training_runs_completed=1,
               **accepted, heldout_metrics=trained["heldout"]["metrics"],
               wall_seconds=time.perf_counter() - started,
               peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),
               peak_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
               peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               final_artifact_bytes=sum(p.stat().st_size for p in root.rglob("*") if p.is_file()),
               final_free_bytes=shutil.disk_usage(root).free)
        return status
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error), wall_seconds=time.perf_counter() - started)
        raise
