"""Deterministic group splits, or strict preservation of released author splits."""

from __future__ import annotations

import hashlib
import math
import re


PARTITIONS = ("train", "validation", "test")


def validate_manifest(manifest, *, source_sha256, source_count):
    if not isinstance(source_count, int) or isinstance(source_count, bool) or source_count < 1:
        raise ValueError("source_count must be a positive integer")
    if (not isinstance(manifest, dict) or manifest.get("version") != 1 or
            isinstance(manifest.get("version"), bool)):
        raise ValueError("Unsupported split manifest version")
    if not isinstance(source_sha256, str) or not re.fullmatch("[0-9a-f]{64}", source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA256 digest")
    if manifest.get("source_sha256") != source_sha256 or manifest.get("source_count") != source_count:
        raise ValueError("Split manifest source fingerprint/count mismatch")
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != source_count:
        raise ValueError("Split manifest must identify every source record")
    identifiers, assignments = set(), {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Split record must be a mapping")
        identifier, group = record.get("id"), record.get("group")
        if (not isinstance(identifier, str) or not identifier or identifier in identifiers or
                not isinstance(group, str) or not group):
            raise ValueError("Split IDs must be unique strings; groups must be nonempty strings")
        identifiers.add(identifier)
    partitions = manifest.get("partitions")
    if not isinstance(partitions, dict) or set(partitions) != set(PARTITIONS):
        raise ValueError("Require train, validation and test partitions")
    seen = set()
    for role in PARTITIONS:
        indices = partitions[role]
        if not isinstance(indices, list) or not indices:
            raise ValueError(f"{role} partition must be a nonempty index list")
        for index in indices:
            if (not isinstance(index, int) or isinstance(index, bool) or
                    not 0 <= index < source_count or index in seen):
                raise ValueError("Split indices must cover each record exactly once")
            seen.add(index)
            group = records[index]["group"]
            if group in assignments and assignments[group] != role:
                raise ValueError(f"Group leakage across partitions: {group}")
            assignments[group] = role
    if seen != set(range(source_count)):
        raise ValueError("Split indices must cover each record exactly once")
    if manifest.get("counts") != {role: len(partitions[role]) for role in PARTITIONS}:
        raise ValueError("Split manifest counts disagree with partition indices")
    return manifest


def create_manifest(records, *, source_sha256, seed=0, ratios=(.8, .1, .1), official=None):
    """Bind groups/IDs and source hash; training seeds never affect this function.

    `official` maps every record ID to its released train/validation/test role.
    Otherwise group counts determine target fractions; variable group sizes mean
    record fractions can differ. Persist actual counts instead of claiming exact 80/10/10.
    """
    records = [{"id": record["id"], "group": record["group"]} for record in records]
    if any(not isinstance(record["id"], str) or not record["id"] or
           not isinstance(record["group"], str) or not record["group"] for record in records):
        raise ValueError("Split IDs and groups must be nonempty strings")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("Split seed must be an integer")
    groups = {record["group"] for record in records}
    if official is None:
        if (len(ratios) != 3 or any(isinstance(r, bool) or not isinstance(r, (int, float))
                                  or not math.isfinite(r) or r <= 0 for r in ratios)
                or not math.isclose(sum(ratios), 1., abs_tol=1e-12)):
            raise ValueError("Three positive split ratios must sum to one")
        if len(groups) < 3:
            raise ValueError("Need at least three groups for nonempty train/validation/test")
        ordered = sorted(groups, key=lambda group: (
            hashlib.sha256(f"{seed}\0{group}".encode("utf-8")).hexdigest(), group))
        training = min(max(1, int(len(groups) * ratios[0])), len(groups) - 2)
        validation = min(max(1, int(len(groups) * ratios[1])), len(groups) - training - 1)
        assignments = {group: "train" if i < training else
                       "validation" if i < training + validation else "test"
                       for i, group in enumerate(ordered)}
        roles = [assignments[record["group"]] for record in records]
        protocol = {"kind": "group_hash_order_v1", "split_seed": seed,
                    "requested_group_ratios": list(ratios)}
    else:
        if set(official) != {record["id"] for record in records}:
            raise ValueError("Official assignments must identify exactly the source record IDs")
        roles = [official[record["id"]] for record in records]
        if any(role not in PARTITIONS for role in roles):
            raise ValueError("Unknown official partition")
        protocol = {"kind": "released_author_partitions"}
    partitions = {role: [index for index, assigned in enumerate(roles) if assigned == role]
                  for role in PARTITIONS}
    manifest = {"version": 1, "source_sha256": source_sha256, "source_count": len(records),
                "records": records, "partitions": partitions, "protocol": protocol,
                "counts": {role: len(indices) for role, indices in partitions.items()}}
    return validate_manifest(manifest, source_sha256=source_sha256, source_count=len(records))
