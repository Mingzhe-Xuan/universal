"""Verify immutable source identity before exposing any manifest partition."""

import hashlib
import json
from pathlib import Path

from .manifest import PARTITIONS, validate_manifest


def load_partition(source, settings, *, partition=None):
    from universal_gnn.data.identity import check_expected_digest, validate_dataset_digest

    validate_dataset_digest(settings, actual_sha256=getattr(source, "sha256", None))
    path = settings.get("split_manifest")
    role = settings.get("partition") if partition is None else partition
    if path is None:
        if settings.get("split_manifest_sha256") is not None:
            raise ValueError("dataset.split_manifest_sha256 requires dataset.split_manifest")
        if role is not None:
            raise ValueError("dataset.partition requires dataset.split_manifest")
        return range(len(source)), None, None
    if role not in PARTITIONS:
        raise ValueError("dataset.partition must explicitly select train, validation or test")
    if not hasattr(source, "sha256") or not hasattr(source, "identifiers"):
        raise ValueError("Split manifests currently require an indexed JSONL source")
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(manifest, source_sha256=source.sha256, source_count=len(source))
    if [record["id"] for record in manifest["records"]] != list(source.identifiers):
        raise ValueError("Manifest record IDs do not match source order")
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                                       allow_nan=False).encode("utf-8")).hexdigest()
    check_expected_digest(settings.get("split_manifest_sha256"), digest, "dataset.split_manifest_sha256")
    return manifest["partitions"][role], manifest, digest
