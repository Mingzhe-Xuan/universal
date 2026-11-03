"""Generation randomness and training-only statistics, independent of Torch."""

import hashlib
import json
import math
import re


CORRUPTION_MODES = ("per_structure_v1", "per_epoch_structure_v2")


def nonnegative_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def corruption_mode(config):
    mode = config.get("generation_corruption", "per_epoch_structure_v2")
    if mode not in CORRUPTION_MODES:
        raise ValueError("Unknown generation_corruption convention")
    return mode


def corruption_seed(config, identifier, index, *, epoch=None, phase="train", draw=0):
    """Training changes by epoch; each evaluation phase/draw stays reproducible."""
    seed = nonnegative_integer(config.get("seed", 123), "seed")
    index = nonnegative_integer(index, "structure index")
    draw = nonnegative_integer(draw, "evaluation draw")
    if epoch is not None:
        nonnegative_integer(epoch, "epoch")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Generation requires nonempty stable structure IDs")
    if phase not in {"train", "train_evaluation", "validation", "test"}:
        raise ValueError("Unknown generation noise phase")
    if epoch is not None and phase != "train":
        raise ValueError("Only training noise has an epoch")
    if corruption_mode(config) == "per_structure_v1":
        return seed + 1 + index
    if phase == "train" and epoch is None:
        phase = "train_evaluation"
    payload = ["ugnn-generation-noise-v2", seed, identifier, phase, epoch, draw]
    return int.from_bytes(hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).digest()[:8], "big") % (2**63)


def require_corruption_compatible(saved_config, actual_config, *, full_resume):
    actual = corruption_mode(actual_config)
    if full_resume:
        if "generation_corruption" not in saved_config:
            raise ValueError("Unversioned generation objective requires an explicit weights-only warm start")
        if corruption_mode(saved_config) != actual:
            raise ValueError("Full resume requires the same generation corruption objective")
    return actual


def volume_per_atom(record):
    numbers, cell = record.get("numbers"), record.get("cell")
    if (not isinstance(numbers, (list, tuple)) or not numbers or
            any(type(z) is not int or not 1 <= z <= 118 for z in numbers)):
        raise ValueError("Generation prior requires atomic numbers")
    if (not isinstance(cell, (list, tuple)) or len(cell) != 3 or
            any(not isinstance(row, (list, tuple)) or len(row) != 3 for row in cell)):
        raise ValueError("Generation prior requires a 3x3 cell")
    if any(type(value) not in (int, float) or not math.isfinite(value) for row in cell for value in row):
        raise ValueError("Generation prior cell must be finite")
    a, b, c = cell
    determinant = (a[0] * (b[1] * c[2] - b[2] * c[1]) -
                   a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0]))
    if not math.isfinite(determinant) or abs(determinant) <= 1e-9:
        raise ValueError("Generation prior cell must be nonsingular")
    return abs(determinant) / len(numbers)


def fit_volume_prior(training_records, *, training_fingerprint):
    """Geometric mean volume/atom; callers must supply only their training partition."""
    if not isinstance(training_fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", training_fingerprint):
        raise ValueError("Generation prior requires a training fingerprint")
    count, mean, squared = 0, 0., 0.
    for record in training_records:
        value = math.log(volume_per_atom(record))
        count += 1
        delta = value - mean
        mean += delta / count
        squared += delta * (value - mean)
    if not count:
        raise ValueError("Generation prior requires a nonempty training partition")
    return {"version": 1, "kind": "train_log_volume_per_atom_v1", "structures": count,
            "training_fingerprint": training_fingerprint, "volume_per_atom": math.exp(mean),
            "log_volume_per_atom_mean": mean, "log_volume_per_atom_std": math.sqrt(max(0., squared / count)),
            "unit": "angstrom^3/atom", "cell_chart": "cubic initial cell; random fractional positions",
            "fitted_partition": "train"}


def condition_indices(identifiers, *, count, seed):
    """Fixed selection without replacement, independent of source/batch order."""
    nonnegative_integer(seed, "sampling seed")
    nonnegative_integer(count, "sample count")
    if count == 0:
        raise ValueError("sample count must be positive")
    identifiers = list(identifiers)
    if any(not isinstance(identifier, str) or not identifier for identifier in identifiers):
        raise ValueError("Sampling conditions require nonempty stable IDs")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Sampling condition IDs must be unique")
    if count > len(identifiers):
        raise ValueError("Sample count exceeds held-out conditions; no silent truncation or replacement")
    def key(index):
        encoded = json.dumps(["ugnn-generation-conditions-v1", seed, identifiers[index]], separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest(), identifiers[index]
    return sorted(range(len(identifiers)), key=key)[:count]


def wasserstein_1d(left, right):
    """Empirical, equal-weight 1-Wasserstein distance, in the input's units."""
    from bisect import bisect_right

    left, right = sorted(left), sorted(right)
    if not left or not right:
        raise ValueError("Distribution comparison requires two nonempty samples")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in left + right):
        raise ValueError("Distribution samples must be finite real numbers")
    boundaries = sorted(set(left + right))
    result = 0.
    for start, end in zip(boundaries, boundaries[1:]):
        difference = bisect_right(left, start) / len(left) - bisect_right(right, start) / len(right)
        result += abs(difference) * (end - start)
    return result
