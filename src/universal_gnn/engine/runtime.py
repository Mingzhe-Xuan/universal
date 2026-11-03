"""Checkpoint continuation and per-run logs shared by supervised and generative tasks."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

import torch


def checkpoint_config(saved):
    from universal_gnn.contracts.schema import CONTRACT_VERSIONS, validate_config, validate_version

    version = saved.get("format_version", 1)
    if version not in {1, 2}:
        raise ValueError(f"Unsupported checkpoint format {version}")
    config = deepcopy(saved["config"])
    from universal_gnn.backbones.official.profiles import PROFILES

    if config.get("backbone", {}).get("name") in PROFILES:
        config["backbone"].setdefault("implementation", "official" if saved.get("official_backbone") else "legacy")
    validate_config(config)
    for kind, value in saved.get("contract_versions", {}).items():
        if kind not in CONTRACT_VERSIONS:
            raise ValueError(f"Unknown checkpoint contract {kind!r}")
        validate_version(value, kind)
    if version == 1:
        config["task"].setdefault("adapter_version", 1)
    return config


def check_model_config(expected, actual, *, training=True):
    from universal_gnn.backbones.official.profiles import PROFILES

    def normalized(settings):
        value = dict(settings)
        if value.get("name") in PROFILES:
            value.setdefault("implementation", "official")
        return value

    if normalized(expected["backbone"]) != normalized(actual["backbone"]):
        raise ValueError("Model settings do not match the checkpoint backbone")
    if expected.get("graph") != actual.get("graph"):
        raise ValueError("Graph settings do not match the checkpoint")
    from universal_gnn.readouts.configuration import normalize_prediction, normalize_optimization

    cutoff = expected.get("resolved_components", {}).get("backbone_cutoff")
    if normalize_prediction(expected, cutoff=cutoff) != normalize_prediction(actual, cutoff=cutoff):
        raise ValueError("Prediction readout/adapter architecture differs from checkpoint; use explicit warm-start")
    if training and normalize_optimization(expected) != normalize_optimization(actual):
        raise ValueError("Optimization policy differs from checkpoint; use explicit warm-start")
    fields = ("kind", "property", "route", "channels", "unit", "spec")
    for key in fields:
        if expected["task"].get(key) != actual["task"].get(key):
            raise ValueError(f"Task setting {key!r} does not match the checkpoint")
    if expected["task"]["kind"] == "forcefield":
        from universal_gnn.tasks.supervision import supervised_outputs

        if supervised_outputs(expected) != supervised_outputs(actual):
            raise ValueError("Supervised outputs do not match the checkpoint; full resume requires the same loss targets")
    if expected["task"].get("adapter_version", 2) != actual["task"].get("adapter_version", 2):
        raise ValueError("Adapter version does not match the checkpoint")


def data_fingerprint(structures):
    from universal_gnn.data.formats import graph_dict

    digest = hashlib.sha256()
    digest.update(b"[")
    for index, structure in enumerate(structures):
        record = {"id": structure.identifier, "numbers": structure.numbers.tolist(),
                  "positions": structure.positions.tolist(), "cell": structure.cell.tolist(),
                  "pbc": structure.pbc.tolist(), "targets": structure.targets}
        if structure.graph is not None:
            record["graph"] = graph_dict(structure.graph)
        if index:
            digest.update(b", ")
        digest.update(json.dumps(record, sort_keys=True, default=lambda value: value.tolist()).encode())
    digest.update(b"]")
    return digest.hexdigest()


def verify_extensions(saved, model):
    expected = saved.get("extensions")
    if expected is None:
        return
    actual = getattr(model.backbone, "extension_provenance", {})
    if set(expected) != set(actual):
        raise ValueError("Checkpoint extensions do not match the current model/graph plugins")
    for role in expected:
        for key in ["source_sha256", "factory"]:
            if expected[role][key] != actual[role][key]:
                raise ValueError(f"Checkpoint {role} plugin code changed ({key})")


def restore_optimizer(saved, optimizer, config, fingerprint):
    check_model_config(checkpoint_config(saved), config)
    state = saved.get("training_state")
    if state is None:
        return None
    if state.get("version") != 1:
        raise ValueError("Unsupported optimizer continuation state")
    if saved.get("components") is not None:
        groups = [{"name": g.get("name"), "parameters": len(g["params"])} for g in optimizer.param_groups]
        expected_groups = [{"name": g["name"], "parameters": len(g["parameters"])} for g in saved["components"]["optimizer_groups"]]
        if groups != expected_groups:
            raise ValueError("Checkpoint optimizer parameter groups differ; use explicit warm-start")
    if state["data_fingerprint"] != fingerprint:
        raise ValueError("Resume requires the same selected structures, target bindings and labels")
    if saved["config"].get("seed", 123) != config.get("seed", 123):
        raise ValueError("Resume requires the same training seed")
    if "batching" in state:
        from universal_gnn.engine.batching import continuation_settings

        if state["batching"] != continuation_settings(config):
            raise ValueError("Resume requires the same batching, precision and sampling settings")
    optimizer.load_state_dict(state["optimizer_state_dict"])
    for group in optimizer.param_groups:
        group["lr"] = config.get("learning_rate", 1e-3)
    torch.set_rng_state(state["torch_rng_state"].cpu())
    devices = sorted({parameter.device.index for group in optimizer.param_groups
                      for parameter in group["params"] if parameter.is_cuda})
    cuda_states = state.get("cuda_rng_states")
    if devices and cuda_states:
        if len(devices) != len(cuda_states):
            raise ValueError("Resume CUDA device count differs from the checkpoint")
        for device, previous in zip(devices, sorted(cuda_states)):
            torch.cuda.set_rng_state(cuda_states[previous].cpu(), device)
    return state


def save_training_checkpoint(path, model, optimizer, config, versions, state, *, scales=None):
    from universal_gnn.contracts.schema import CONTRACT_VERSIONS

    devices = {parameter.device.index for parameter in model.parameters() if parameter.is_cuda}
    from universal_gnn.engine.batching import continuation_settings

    if state is not None:
        state = {**state, "batching": continuation_settings(config), "version": 1, "optimizer_state_dict": optimizer.state_dict(),
                 "torch_rng_state": torch.get_rng_state(),
                 "cuda_rng_states": {device: torch.cuda.get_rng_state(device) for device in devices} or None}
    payload = {"format_version": 2, "config": config, "state_dict": model.state_dict(),
               "versions": versions}
    if state is not None:
        payload["training_state"] = state
    payload["contract_versions"] = dict(CONTRACT_VERSIONS)
    payload["extensions"] = getattr(getattr(model, "backbone", None), "extension_provenance", {})
    artifact = getattr(getattr(model, "backbone", None), "official_artifact", None)
    if artifact is not None:
        payload["official_backbone"] = artifact
    if "prediction" in config or "optimization" in config:
        from universal_gnn.engine.optimization import component_checkpoint

        payload["components"] = component_checkpoint(model)
    if scales is not None:
        payload["scales"] = scales
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    try:
        torch.save(payload, temporary)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class RunLog:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.identifier = uuid.uuid4().hex

    def __call__(self, event, **values):
        record = {"time": datetime.now(timezone.utc).isoformat(), "run_id": self.identifier,
                  "event": event, **values}
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
        with (self.directory / "run.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{record['time']} {event} " + json.dumps(values) + "\n")
