"""Fixed development pool; test labels and training RNG never select validation."""

import hashlib

from universal_gnn.data.splits import create_manifest


VALIDATION_NAMESPACE = "ugnn-rmd17-ethanol-split01-validation-v1"


def parse_indices(text, *, source_count, expected_count=1000):
    lines = text.splitlines()
    if (type(source_count) is not int or source_count <= 0 or type(expected_count) is not int or expected_count <= 0
            or len(lines) != expected_count
            or any(not line.strip().isascii() or not line.strip().isdigit() for line in lines)):
        raise ValueError("Official rMD17 CSV must contain exactly the declared integer indices")
    values = [int(line) for line in lines]
    if len(set(values)) != expected_count or min(values) < 0 or max(values) >= source_count:
        raise ValueError("Official rMD17 indices must be unique and in range")
    return values


def frame_id(index):
    if type(index) is not int or index < 0:
        raise ValueError("Source frame index must be a nonnegative integer")
    return f"rmd17:ethanol:{index:06d}"


def build_manifest(records, *, source_sha256, official_train, official_test):
    count = len(records)
    for values in (official_train, official_test):
        if (not isinstance(values, list) or len(values) != 1000 or len(set(values)) != 1000
                or any(type(i) is not int or not 0 <= i < count for i in values)):
            raise ValueError("Require both complete original 1000-index lists")
    if set(official_train) & set(official_test):
        raise ValueError("Official rMD17 development and test indices overlap")
    if any(row["id"] != frame_id(i) for i, row in enumerate(records)):
        raise ValueError("rMD17 source frame IDs or ordering changed")
    ranked = sorted(official_train, key=lambda i: (
        hashlib.sha256((VALIDATION_NAMESPACE + "\0" + records[i]["id"]).encode()).hexdigest(), records[i]["id"]))
    validation, development = set(ranked[:100]), set(official_train)
    assignments = {row["id"]: "validation" if i in validation else "train" if i in development else "test"
                   for i, row in enumerate(records)}
    manifest = create_manifest(records, source_sha256=source_sha256, seed=0, official=assignments)
    if manifest["counts"] != dict(train=900, validation=100, test=count - 1000):
        raise ValueError("rMD17 declared development/test coverage differs")
    manifest["protocol"] = dict(kind="rmd17_official_development_pool_v1", official_split=1, split_seed=0,
        validation_namespace=VALIDATION_NAMESPACE, validation_selection="100 lowest ID hashes inside author training1000 only",
        author_development_count=1000, original_test_count=1000, training_rng_used=False,
        grouping="exact source Cartesian geometry; MD trajectory independence not claimed",
        temporal_independence_claimed=False,
        warning="Single correlated ethanol trajectory. Full heldout pool is not independent-trajectory or new-molecule generalization.")
    manifest["evaluation_cohorts"] = {"official_test_01": list(official_test)}
    manifest["official_development_indices"] = list(official_train)
    return manifest
