"""Pure checks for a train-only prior and separate sampling capacity."""

import copy
import json
import math
from pathlib import Path
import re

from ..experiments.registry import canonical_digest
from ..pairing.evidence import verify_capacity_evidence
from .preparation import phase_probes


def validate_prior(prior, training_count):
    if not isinstance(prior, dict) or prior.get("sampling_volume_source") != "train_fit":
        raise ValueError("Formal sampling requires a fitted training-only prior")
    stats = prior.get("statistics", {})
    if (stats.get("version") != 1 or stats.get("kind") != "train_log_volume_per_atom_v1" or
            stats.get("fitted_partition") != "train" or stats.get("structures") != training_count or
            stats.get("unit") != "angstrom^3/atom" or
            not isinstance(stats.get("training_fingerprint"), str) or
            not re.fullmatch("[0-9a-f]{64}", stats["training_fingerprint"])):
        raise ValueError("Prior does not describe the complete bound training partition")
    for name in ("volume_per_atom", "log_volume_per_atom_mean", "log_volume_per_atom_std"):
        value = stats.get(name)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Prior statistics must be finite numeric values")
    if stats["volume_per_atom"] <= 0 or stats["log_volume_per_atom_std"] < 0:
        raise ValueError("Prior volume and variance are invalid")
    if not math.isclose(stats["volume_per_atom"], math.exp(stats["log_volume_per_atom_mean"]), rel_tol=1e-14):
        raise ValueError("Prior volume differs from its training fit")


def checked_generation_config(actual, expected, common, counts, prior):
    from ..execution.gates import checked_config

    validate_prior(prior, counts["train"])
    clean = copy.deepcopy(actual)
    if clean.pop("generation_prior", None) != prior:
        raise ValueError("Resolved generation prior changed")
    volume = clean["task"]["sampling"].pop("volume_per_atom", None)
    if volume != prior["statistics"]["volume_per_atom"]:
        raise ValueError("Sampling volume differs from the training-only fit")
    checked_config(clean, expected, common, counts)


def check_sampling_capacity(preparation, configs, train_resolved, probe, counts, prior, settings):
    root = Path(preparation) / "sample-capacity"
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    inputs = copy.deepcopy(train_resolved)
    for config in inputs.values():
        config["batch_size"] = settings["initial_batch_size"]
    sample_probe = phase_probes(probe, settings)
    if (report.get("configs") != inputs or report.get("phase") != "sample" or
            report.get("input_config_sha256") != {k: canonical_digest(v) for k, v in inputs.items()}):
        raise ValueError("Sampling capacity changed its trained-input configuration or phase")
    evidence = verify_capacity_evidence(root, sample_probe, minimum_batches=settings["measure_batches"])
    common = evidence["common_batch_size"]
    if common > settings["initial_batch_size"]:
        raise ValueError("Sampling batch exceeds its declared initial size")
    for mode in ("pretrained", "scratch"):
        actual = json.loads((root / ("config." + mode + ".resolved.json")).read_text(encoding="utf-8"))
        checked_generation_config(actual, configs[mode], common, counts, prior)
        if (canonical_digest(actual) != report["resolved_config_sha256"][mode] or
                actual["backbone"].get("neighbor_statistics") != train_resolved[mode]["backbone"].get("neighbor_statistics")):
            raise ValueError("Sampling changed native calibration or its final config hash")
    return evidence
