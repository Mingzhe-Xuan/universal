"""Fit a generation cell prior from every declared training structure, through Slurm."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from universal_gnn.data.preparation.jarvis import file_sha256
from universal_gnn.data.splits import validate_manifest
from universal_gnn.engine.generative.protocol import fit_volume_prior


def prepare_prior(source, manifest_path, output):
    source, manifest_path, output = Path(source), Path(manifest_path), Path(output)
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing generation prior receipt")
    dataset_sha = file_sha256(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, source_sha256=dataset_sha, source_count=manifest.get("source_count"))
    manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    indices = set(manifest["partitions"]["train"])
    train_ids = [manifest["records"][index]["id"] for index in manifest["partitions"]["train"]]
    identity = {"source_sha256": dataset_sha, "manifest_sha256": manifest_sha, "train_ids": train_ids}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def training_records():
        seen = 0
        with source.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                if seen >= manifest["source_count"] or record.get("id") != manifest["records"][seen]["id"]:
                    raise ValueError("Generation source identity/order differs from its manifest")
                if seen in indices:
                    yield record
                seen += 1
        if seen != manifest["source_count"]:
            raise ValueError("Generation source count differs from its manifest")

    prior = fit_volume_prior(training_records(), training_fingerprint=fingerprint)
    if prior["structures"] != manifest["counts"]["train"]:
        raise RuntimeError("Prior fitted count differs from the complete training partition")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    from universal_gnn.engine.generative import protocol

    receipt = {"version": 1, "prior": prior, "source": str(source), "source_sha256": dataset_sha,
               "manifest": str(manifest_path), "manifest_sha256": manifest_sha,
               "partition_counts": manifest["counts"], "heldout_structures_used_for_fit": 0,
               "execution": {"git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
                             "slurm_job_id": os.environ.get("SLURM_JOB_ID"), "node": os.environ.get("SLURMD_NODENAME"),
                             "script_sha256": file_sha256(__file__), "protocol_sha256": file_sha256(protocol.__file__)},
               "interpretation": "training-only initial-cell prior; no model training or generation quality result"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Generation prior preparation must run through Slurm")
    print(json.dumps(prepare_prior(args.source, args.manifest, args.output)))


if __name__ == "__main__":
    main()
