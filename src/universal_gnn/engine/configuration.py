"""User configuration files and explicit command-line overrides."""

from copy import deepcopy
import json
from pathlib import Path


def load_config(path):
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        try:
            config = yaml.safe_load(content)
        except yaml.YAMLError as error:
            raise ValueError(f"Invalid YAML configuration: {error}") from error
    elif path.suffix.lower() == ".json":
        config = json.loads(content)
    else:
        raise ValueError("--config must be a .json, .yaml or .yml file")
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a mapping")
    from universal_gnn.contracts.schema import validate_config

    validate_config(config)
    for key in ("backbone", "dataset", "task"):
        if key in config and not isinstance(config[key], dict):
            raise ValueError(f"Configuration {key!r} must be a mapping")
    return config


def merge_config(base, changes):
    result = deepcopy(base)
    for key, value in changes.items():
        result[key] = (merge_config(result[key], value)
                       if isinstance(result.get(key), dict) and isinstance(value, dict) else deepcopy(value))
    return result


def resolve_dataset_settings(file_dataset, *, base=None, source_override=None):
    if not isinstance(file_dataset, dict) or (base is not None and not isinstance(base, dict)):
        raise ValueError("Dataset settings must be mappings")
    previous_dataset = base or {}
    result = merge_config(previous_dataset, file_dataset)
    fields = ("sha256", "split_manifest", "split_manifest_sha256", "partition")
    if previous_dataset.get("path") is not None and result.get("path") != previous_dataset["path"]:
        for field in fields:
            if field not in file_dataset:
                result.pop(field, None)
    if source_override is not None:
        if source_override != file_dataset.get("path", previous_dataset.get("path")):
            for field in fields:
                result.pop(field, None)
        result["path"] = source_override
    return result


def resolve_config(file_config, *, base=None, model=None, dataset=None, task=None,
                   graph=None, device=None, epochs=None, training=False):
    config = merge_config(base or {}, file_config)
    if "dataset" in config or dataset is not None:
        config["dataset"] = resolve_dataset_settings(file_config.get("dataset", {}),
                                                     base=(base or {}).get("dataset"), source_override=dataset)
    if model is not None:
        previous = config.get("backbone", {})
        from universal_gnn.backbones.official.profiles import PROFILES

        if (previous.get("name") != model and previous.get("implementation", "official") == "official"
                and model in PROFILES):
            config["backbone"] = {"name": model, "implementation": "official"}
        config.setdefault("backbone", {})["name"] = model
    if graph is not None:
        if config.get("graph", {}).get("name") != graph:
            config["graph"] = {"name": graph}
    if task is not None:
        previous = config.get("task", {})
        kind = task if task in {"forcefield", "generation"} else "supervised"
        if previous.get("kind") != kind:
            config["task"] = {"kind": kind}
        elif kind == "supervised" and previous.get("property") != task:
            config["task"] = {key: value for key, value in previous.items() if key in {"kind", "loss_weights"}}
        if kind == "supervised":
            config["task"]["property"] = task
    if device is not None:
        config["device"] = device
    if epochs is not None:
        config["epochs"] = epochs
    from universal_gnn.contracts.schema import validate_config

    validate_config(config)
    for key, field in [("backbone", "name"), ("dataset", "path"), ("task", "kind")]:
        if not config.get(key, {}).get(field):
            raise ValueError(f"Missing {key}.{field}; provide it in --config or the corresponding CLI flag")
    if config["task"]["kind"] == "supervised" and not config["task"].get("property"):
        raise ValueError("Supervised training requires --task or task.property")
    if training:
        config.setdefault("epochs", 30)
        config.setdefault("checkpoint_every", 1)
        for key, minimum in [("epochs", 1), ("checkpoint_every", 0)]:
            value = config.get(key, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                raise ValueError(f"{key} must be an integer >= {minimum}")
        limit = config.get("structures")
        if limit not in (None, "all") and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
            raise ValueError("structures must be a positive integer, null or all")
    from universal_gnn.engine.batching import validate_batching

    validate_batching(config)
    return config
