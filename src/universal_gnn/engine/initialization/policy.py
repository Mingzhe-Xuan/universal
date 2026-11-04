"""Bind native graph statistics to complete training data without importing a model runtime."""

import copy
import re

from universal_gnn.backbones.blueprints import neighbor_normalization


def requires_native_neighbor_statistics(config):
    backbone = config.get("backbone", {})
    return (backbone.get("name") in {"mace", "nequip"} and
            backbone.get("implementation", "official") == "official" and
            backbone.get("initialization", "pretrained") == "scratch")


def inherit_neighbor_statistics(config, saved_config):
    resolved = copy.deepcopy(config)
    if (requires_native_neighbor_statistics(resolved) and requires_native_neighbor_statistics(saved_config) and
            resolved["backbone"]["name"] == saved_config["backbone"]["name"] and
            "neighbor_statistics" not in resolved["backbone"] and "neighbor_statistics" in saved_config["backbone"]):
        resolved["backbone"]["neighbor_statistics"] = copy.deepcopy(saved_config["backbone"]["neighbor_statistics"])
    return resolved


def training_identity(settings, selected_indices, training_indices, *, source_sha256, manifest_sha256,
                      training_fingerprint, dtype):
    if not isinstance(settings, dict) or not settings.get("split_manifest") or settings.get("partition") != "train":
        raise ValueError("Native calibration requires an explicit training split manifest")
    selected, training = list(selected_indices), list(training_indices)
    if (not training or any(type(index) is not int or index < 0 for index in selected + training) or
            len(selected) != len(training) or len(set(training)) != len(training) or
            len(set(selected)) != len(selected) or set(selected) != set(training)):
        raise ValueError("Native calibration must cover the complete training partition exactly once")
    if dtype not in ("float32", "float64"):
        raise ValueError("Native calibration requires a supported input precision")
    result = dict(source_sha256=source_sha256, manifest_sha256=manifest_sha256,
                  training_fingerprint=training_fingerprint, dtype=dtype,
                  declared_training_structures=len(training))
    for key in ("source_sha256", "manifest_sha256", "training_fingerprint"):
        if not isinstance(result[key], str) or not re.fullmatch(r"[0-9a-f]{64}", result[key]):
            raise ValueError("Native calibration requires source/manifest/training fingerprints")
    return result


def validate_bound_statistics(statistics, identity, *, provider, cutoff, native_graph):
    normalization = neighbor_normalization(statistics, provider=provider, cutoff=cutoff)
    if any(statistics.get(key) != value for key, value in identity.items()):
        raise ValueError("Native neighbor statistics do not match the selected training data or precision")
    if not isinstance(native_graph, dict) or not native_graph or statistics.get("native_graph") != native_graph:
        raise ValueError("Native neighbor statistics do not match the original graph implementation/artifact")
    return normalization
