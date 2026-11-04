"""Inspect complete released datasets and original artifacts without a model runtime."""

import hashlib
import json
from pathlib import Path

from universal_gnn.backbones.official.profiles import PROFILES
from universal_gnn.data.splits import validate_manifest

MODELS = ("cgcnn", "alignn", "mace", "nequip")
DATASETS = {
    "jarvis-gap": ("e06ce343c1cc4c727664255dcef8f2ad09f65b1c50546294ae44e7d90793fd58", (60823, 7590, 7580)),
    "gmtnet-dielectric": ("e2f3ec9569e67e31d353bad3f1f05da6856da64e7f34cb0fd59589e3c3edaa77", (3998, 502, 499)),
    "jarvis-phonon-dos": ("d20b16ad37ddbb1bbab534b2e41c9f7f01e07a127b8fb74e133dd7baca86c891", (11394, 1424, 1426)),
    "mlearn-forcefield": ("0ca42ef08e9f627f8f851de6a75bd958bb7632ec73a7fbc09a460baba20fe417", (1309, 93, 164)),
    "perov5": ("df69edd0cec94f6768be338f85513cd34187fd7d45602f67ac7e194afdc6ae29", (11356, 3787, 3785)),
}
NEQUIP_ARCHITECTURE = ("nequip/NequIP-OAM-S_pretrain_config.yaml", "d61e684aa85e3cad83578042fa485df9fb9ab8d8a3f6fe56b8b20564d7f6f076")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def inspect_dataset(repository, name, expected):
    directory = Path(repository) / "data/arxiv-v1" / name
    source, split, audit_path = (directory / filename for filename in ("structures.jsonl", "split.json", "audit.json"))
    expected_sha, counts = expected
    identifiers, seen, source_hash = [], set(), hashlib.sha256()
    with source.open("rb") as stream:
        for line in stream:
            source_hash.update(line)
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{name}: standard JSONL records must be mappings")
            identifier = record.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                raise ValueError(f"{name}: nonunique/missing standard record ID")
            identifiers.append(identifier);seen.add(identifier)
    actual_sha = source_hash.hexdigest()
    if actual_sha != expected_sha or len(identifiers) != sum(counts):
        raise ValueError(f"{name}: full released dataset bytes/count differ from the registered source")
    manifest = json.loads(split.read_text(encoding="utf-8"))
    validate_manifest(manifest, source_sha256=actual_sha, source_count=len(identifiers))
    if [row["id"] for row in manifest["records"]] != identifiers:
        raise ValueError(f"{name}: manifest IDs/order differ from the complete source")
    declared = dict(zip(("train", "validation", "test"), counts))
    if manifest["counts"] != declared:
        raise ValueError(f"{name}: registered full partition sizes changed")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (audit.get("dataset_sha256") != actual_sha or audit.get("split_counts") != declared or
            audit.get("counts", {}).get("written_records") != len(identifiers)):
        raise ValueError(f"{name}: source/partition audit is inconsistent")
    return dict(path=f"data/arxiv-v1/{name}/structures.jsonl", sha256=actual_sha,
                split_manifest=f"data/arxiv-v1/{name}/split.json", split_manifest_sha256=canonical_digest(manifest),
                structures=len(identifiers), split_counts=declared, maximum_atoms=audit.get("maximum_atoms"),
                audit_sha256=digest(audit_path), preparation_execution=audit.get("execution"))


def inspect_registry(repository):
    repository = Path(repository)
    datasets = {name: inspect_dataset(repository, name, expected) for name, expected in DATASETS.items()}
    artifacts = {}
    for model in MODELS:
        profile = PROFILES[model]
        files = dict(profile["files"])
        if model == "nequip":
            files[NEQUIP_ARCHITECTURE[0]] = NEQUIP_ARCHITECTURE[1]
        verified = {}
        for relative, expected in files.items():
            path = repository / "models/official" / relative
            if digest(path) != expected:
                raise ValueError(f"{model}: registered original artifact SHA mismatch: {relative}")
            verified[relative] = dict(sha256=expected, bytes=path.stat().st_size)
        artifacts[model] = dict(source=profile["source"], files=verified)
    return dict(version=1, kind="arxiv_v1_full_inputs", datasets=datasets, artifacts=artifacts,
                interpretation="fixed source/partition/artifact bytes only; no runtime, capacity or scientific acceptance")
