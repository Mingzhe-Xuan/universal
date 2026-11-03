"""Strict, versioned prediction configuration; no backbone execution or lazy layers."""

from copy import deepcopy

from universal_gnn.contracts.components import positive_dimension
from universal_gnn.properties import property_spec


def fields(value, allowed, path):
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a mapping")
    unknown = set(value) - set(allowed)
    if unknown:
        raise ValueError(f"{path} unknown fields: {sorted(unknown)}")


def version(value, path):
    if type(value) is not int or value != 1:
        raise ValueError(f"{path} unsupported version {value!r}")


def task_spec(config):
    task = config["task"]
    if task["kind"] == "forcefield":
        return property_spec("total_energy")
    return property_spec(task["property"], channels=task.get("channels"), unit=task.get("unit"), definition=task.get("spec"))


def normalize_processing(value=None, *, cutoff=None, path="readout.feature_processing"):
    value = deepcopy(value if value is not None else {"name": "none"})
    fields(value, {"name", "version", "profile", "basis_version", "cutoff"}, path)
    name = value.get("name")
    if not isinstance(name, str) or name not in {"none", "scalar_invariants", "equivariant"}:
        raise ValueError(f"{path}.name unsupported {name!r}")
    value.setdefault("version", 1)
    version(value["version"], path + ".version")
    if name == "equivariant":
        if value.get("profile") != "small_response":
            raise ValueError(f"{path}.profile must explicitly select small_response")
        if type(value.get("basis_version")) is not int or value["basis_version"] not in {1, 2}:
            raise ValueError(f"{path}.basis_version must explicitly select 1 or 2")
        actual = value.get("cutoff", cutoff)
        if actual is not None:
            import math

            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual) or actual <= 0:
                raise ValueError(f"{path}.cutoff must be positive and finite")
            value["cutoff"] = actual
    elif set(value) - {"name", "version"}:
        raise ValueError(f"{path}: {name} does not accept profile/basis_version/cutoff")
    return value


def normalize_prediction(config, *, cutoff=None):
    if "prediction" not in config:
        return None
    from .factory import READOUTS

    if config["task"]["kind"] not in {"supervised", "forcefield"}:
        raise ValueError("prediction is not supported for generation")
    if {"route", "adapter_version"} & set(config["task"]):
        raise ValueError("prediction conflicts with legacy task.route/task.adapter_version")
    value = deepcopy(config["prediction"])
    fields(value, {"version", "readout", "adapter"}, "prediction")
    version(value.get("version"), "prediction.version")
    if "readout" not in value:
        raise ValueError("prediction.readout is required")
    readout = value["readout"]
    if not isinstance(readout, dict) or not isinstance(readout.get("name"), str) or readout.get("name") not in READOUTS:
        raise ValueError(f"prediction.readout.name must select a registered readout: {sorted(READOUTS)}")
    registration = READOUTS[readout["name"]]
    fields(readout, {"name", "pooling", "feature_processing"} | set(registration.fields), "prediction.readout")
    spec = task_spec(config)
    for n in spec.shape:
        positive_dimension(n, "PropertySpec.shape")
    if spec.scope not in registration.requirement.scopes or spec.construction != registration.requirement.construction:
        raise ValueError(f"prediction.readout {readout['name']} requires scope={registration.requirement.scopes}, construction={registration.requirement.construction}; actual {spec.to_dict()}")
    readout.setdefault("pooling", spec.reduction)
    pooling = readout["pooling"]
    if not isinstance(pooling, str) or pooling not in {"sum", "mean", "none"} or pooling != spec.reduction:
        raise ValueError(f"readout.pooling={pooling!r} conflicts with PropertySpec.reduction={spec.reduction!r}")
    if (spec.scope == "graph" and pooling == "none") or (spec.scope == "node" and pooling != "none"):
        raise ValueError("readout.pooling must be sum/mean for graph scope and none for node scope")
    if readout["name"] == "response" and pooling not in {"mean", "none"}:
        raise ValueError("response readout only supports graph mean or node none pooling")
    if config["task"]["kind"] == "forcefield" and (readout["name"] != "node_mlp" or pooling != "sum"):
        raise ValueError("prediction.readout: new forcefield requires node_mlp + pooling=sum for atomic energy summation")
    if readout["name"] in {"graph_mlp", "node_mlp"}:
        hidden = readout.get("hidden_features")
        if not isinstance(hidden, list) or not hidden:
            raise ValueError("readout.hidden_features must be a nonempty positive-integer list")
        for n in hidden:
            positive_dimension(n, "readout.hidden_features")
        readout.setdefault("activation", "silu")
        if readout["activation"] != "silu":
            raise ValueError("readout.activation supports only silu")
    if "bias" in registration.fields:
        readout.setdefault("bias", True)
        if type(readout["bias"]) is not bool:
            raise ValueError("readout.bias must be bool")
    for key, mapping, path in [("feature_processing", readout, "readout.feature_processing"), ("adapter", value, "prediction.adapter")]:
        if key in mapping and not isinstance(mapping[key], dict):
            raise ValueError(f"{path} must be a mapping")
    readout["feature_processing"] = normalize_processing(readout.get("feature_processing"), cutoff=cutoff)
    value["adapter"] = normalize_processing(value.get("adapter"), cutoff=cutoff, path="prediction.adapter")
    if value["adapter"]["name"] != "none" and value["adapter"]["name"] == readout["feature_processing"]["name"]:
        raise ValueError("prediction.adapter and readout.feature_processing duplicate the same conversion")
    return value


def normalize_optimization(config, *, has_adapter=None):
    if config.get("task", {}).get("kind") == "generation":
        if "optimization" in config or "prediction" in config:
            raise ValueError("prediction/optimization are not supported for generation")
        return None
    if has_adapter is None:
        prediction = normalize_prediction(config)
        has_adapter = prediction is None or prediction["adapter"]["name"] != "none"
    result = deepcopy(config.get("optimization", {}))
    fields(result, {"train_backbone", "train_readout", "train_adapter"}, "optimization")
    if not has_adapter and "train_adapter" in result:
        raise ValueError("optimization.train_adapter requires an independent adapter; internal processing belongs to train_readout")
    for component in ("backbone", "adapter", "readout") if has_adapter else ("backbone", "readout"):
        key = "train_" + component
        result.setdefault(key, True)
        if type(result[key]) is not bool:
            raise ValueError(f"optimization.{key} must be bool")
    return result


def validate_component_config(config):
    if "prediction" in config or "optimization" in config:
        if "prediction" in config:
            fields(config["prediction"], {"version", "readout", "adapter"}, "prediction")
            version(config["prediction"].get("version"), "prediction.version")
        if "optimization" in config:
            fields(config["optimization"], {"train_backbone", "train_readout", "train_adapter"}, "optimization")
            for key, value in config["optimization"].items():
                if type(value) is not bool:
                    raise ValueError(f"optimization.{key} must be bool")
        task = config.get("task", {})
        if "kind" not in task or (task["kind"] == "supervised" and "property" not in task):
            return
        normalize_optimization(config)
