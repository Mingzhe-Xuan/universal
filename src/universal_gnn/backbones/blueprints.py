"""Prepare original constructor arguments without reusing fitted model statistics."""

import copy
import math
import re


def aggregate_native_neighbor_counts(counts, *, provider, cutoff, dtype, source_sha256,
                                     manifest_sha256, training_fingerprint, declared_training_structures):
    """Aggregate original graph counts; callers must independently bind their training selection."""
    if type(declared_training_structures) is not int or declared_training_structures < 1:
        raise ValueError("Declared training size must be a positive integer")
    totals = dict(structures=0, atomic_nodes=0, active_receivers=0, directed_edges=0)
    for count in counts:
        fields = ("atomic_nodes", "active_receivers", "directed_edges")
        if (not isinstance(count, dict) or any(type(count.get(key)) is not int for key in fields) or
                count["atomic_nodes"] < 1 or not 0 <= count["active_receivers"] <= count["atomic_nodes"] or
                count["directed_edges"] < count["active_receivers"] or
                (count["directed_edges"] > 0 and count["active_receivers"] == 0)):
            raise ValueError("Native per-structure node/receiver/edge counts are inconsistent")
        totals["structures"] += 1
        if totals["structures"] > declared_training_structures:
            raise ValueError("Neighbor counts exceed the complete declared training partition")
        for key in fields:
            totals[key] += count[key]
    result = dict(version=1, kind="native_neighbor_counts_v1", provider=provider, partition="train",
                  cutoff=cutoff, dtype=dtype, source_sha256=source_sha256, manifest_sha256=manifest_sha256,
                  training_fingerprint=training_fingerprint, declared_training_structures=declared_training_structures,
                  **totals)
    neighbor_normalization(result, provider=provider, cutoff=cutoff)
    return result


def neighbor_normalization(statistics, *, provider, cutoff):
    if provider not in ("mace", "nequip"):
        raise ValueError("Native neighbor normalization is defined for MACE and NequIP")
    if (not isinstance(statistics, dict) or type(statistics.get("version")) is not int or statistics["version"] != 1 or
            statistics.get("kind") != "native_neighbor_counts_v1" or statistics.get("provider") != provider or
            statistics.get("partition") != "train" or statistics.get("dtype") not in ("float32", "float64")):
        raise ValueError("Fresh construction requires provider-specific training neighbor statistics")
    radius = statistics.get("cutoff")
    if (type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0 or
            not math.isclose(radius, cutoff, rel_tol=1e-12, abs_tol=0.)):
        raise ValueError("Training neighbor statistics have a different native cutoff")
    for field in ("source_sha256", "manifest_sha256", "training_fingerprint"):
        if not isinstance(statistics.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", statistics[field]):
            raise ValueError("Training neighbor statistics require source/manifest/training fingerprints")
    fields = ("structures", "declared_training_structures", "atomic_nodes", "active_receivers", "directed_edges")
    if any(type(statistics.get(field)) is not int or statistics[field] < 1 for field in fields):
        raise ValueError("Training neighbor counts must be positive integers")
    if (statistics["structures"] != statistics["declared_training_structures"] or
            statistics["atomic_nodes"] < statistics["structures"] or
            statistics["active_receivers"] > statistics["atomic_nodes"] or
            statistics["directed_edges"] < statistics["active_receivers"]):
        raise ValueError("Neighbor counts must cover the complete declared training partition")
    denominator = statistics["active_receivers"] if provider == "mace" else statistics["atomic_nodes"]
    return statistics["directed_edges"] / denominator


def _constant_shape(value, fill):
    shape = getattr(value, "shape", None)
    if shape is None:
        if isinstance(value, (list, tuple)):
            return [_constant_shape(item, fill) for item in value]
        if type(value) in (int, float):
            return float(fill)
        raise ValueError("Fitted constructor statistics require array/scalar shape information")
    def build(dimensions):
        if not dimensions:
            return float(fill)
        if type(dimensions[0]) is not int or dimensions[0] < 1:
            raise ValueError("Fitted statistic dimensions must be positive integers")
        return [build(dimensions[1:]) for _ in range(dimensions[0])]
    return build(tuple(shape))


def mace_constructor_config(extracted, statistics):
    if not isinstance(extracted, dict) or "error" in extracted:
        raise ValueError("Original MACE constructor extraction failed")
    required = {"r_max", "num_elements", "atomic_numbers", "atomic_energies", "atomic_inter_scale", "atomic_inter_shift"}
    if not required <= set(extracted):
        raise ValueError("Original MACE constructor configuration is incomplete")
    result = dict(extracted)
    result["avg_num_neighbors"] = neighbor_normalization(statistics, provider="mace", cutoff=extracted["r_max"])
    result["atomic_energies"] = _constant_shape(extracted["atomic_energies"], 0.)
    result["atomic_inter_scale"] = _constant_shape(extracted["atomic_inter_scale"], 1.)
    result["atomic_inter_shift"] = _constant_shape(extracted["atomic_inter_shift"], 0.)
    return result


def nequip_constructor_config(blueprint, statistics, *, seed):
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("Fresh NequIP requires a nonnegative 64-bit initialization seed")
    if not isinstance(blueprint, dict):
        raise ValueError("NequIP blueprint must be a mapping")
    module = blueprint.get("training_module")
    recipe = module.get("model") if isinstance(module, dict) else blueprint
    skipped = []
    seen = set()
    while isinstance(recipe, dict) and recipe.get("_target_") in ("nequip.model.modify", "nequip.model.modify_utils.modify"):
        if id(recipe) in seen:
            raise ValueError("Recursive NequIP model recipe")
        seen.add(id(recipe))
        modifiers = recipe.get("modifiers")
        if not isinstance(modifiers, list):
            raise ValueError("NequIP modifier list is required")
        for modifier in modifiers:
            if (not isinstance(modifier, dict) or set(modifier) != {"modifier"} or
                    modifier["modifier"] not in ("enable_OpenEquivariance", "enable_CuEquivariance")):
                raise ValueError("Fresh eager NequIP cannot discard an unknown or persistent modifier")
            skipped.append(modifier["modifier"])
        recipe = recipe.get("model")
    if not isinstance(recipe, dict) or recipe.get("_target_") != "nequip.model.NequIPGNNModel":
        raise ValueError("NequIP blueprint must expose its original NequIPGNNModel constructor; no checkpoint-loader fallback")
    result = copy.deepcopy(recipe)
    result.pop("_target_")
    if "r_max" not in result or not isinstance(result.get("type_names"), list) or not result["type_names"]:
        raise ValueError("Original NequIP blueprint lacks cutoff or type vocabulary")
    result["avg_num_neighbors"] = neighbor_normalization(statistics, provider="nequip", cutoff=result["r_max"])
    result.update(seed=seed, compile_mode="eager", per_type_energy_shifts=0., per_type_energy_scales=1.)
    return result, {"skipped_nonpersistent_modifiers_for_eager": skipped,
                    "source_constructor": "nequip.model.NequIPGNNModel"}
