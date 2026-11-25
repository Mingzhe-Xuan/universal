"""Freeze a label-independent subset inside each already-separated QM9 partition."""

import hashlib
import json
import os
from pathlib import Path

from universal_gnn.data.splits.manifest import validate_manifest
from .conversion import write_json
from .source import CLEAN_COUNT, UNITS, digest

SUBSET_COUNTS = dict(train=10000, validation=1000, test=1000)


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def select_indices(manifest, counts=SUBSET_COUNTS):
    """Select complete original-SMILES groups without consulting target values."""
    if set(counts) != {"train", "validation", "test"} or any(type(n) is not int or n < 1 for n in counts.values()):
        raise ValueError("Require three positive subset counts")
    validate_manifest(manifest, source_sha256=manifest["source_sha256"], source_count=manifest["source_count"])
    selected = {}
    for role, budget in counts.items():
        groups = {}
        for i in manifest["partitions"][role]:
            groups.setdefault(manifest["records"][i]["group"], []).append(i)
        order = sorted(groups, key=lambda g: (hashlib.sha256(("ugnn-qm9-hl12k-v1\0" + role + "\0" + g).encode()).hexdigest(), g))
        chosen = []
        for group in order:
            members = groups[group]
            if len(members) <= budget - len(chosen):
                chosen.extend(members)
            if len(chosen) == budget:
                break
        if len(chosen) != budget:
            raise ValueError("Cannot meet exact subset count while retaining complete SMILES groups")
        selected[role] = sorted(chosen)
    return selected


def prepare_subset(parent_directory, output):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("QM9 subset creation/checks require CPU Slurm")
    parent_directory, output = Path(parent_directory), Path(output)
    parent = json.loads((parent_directory / "report.json").read_bytes())
    if parent.get("status") != "passed" or parent.get("clean_count") != CLEAN_COUNT or parent.get("units") != UNITS:
        raise ValueError("Require the complete accepted clean parent QM9 source")
    data = parent["dataset"]
    manifest = json.loads(Path(data["split_manifest"]).read_bytes())
    if digest(data["path"]) != data["sha256"] or canonical(manifest) != data["split_manifest_sha256"]:
        raise ValueError("Parent QM9 source/split changed")
    selected = select_indices(manifest)
    roles = {i: role for role, indices in selected.items() for i in indices}
    output.mkdir(parents=True, exist_ok=False)
    records, partitions, original = [], {role: [] for role in selected}, []
    with Path(data["path"]).open("rb") as source, (output / "structures.jsonl").open("xb") as target:
        for index, line in enumerate(source):
            if index not in roles:
                continue
            row = json.loads(line)
            if row["id"] != manifest["records"][index]["id"] or row["metadata"]["smiles"] != manifest["records"][index]["group"]:
                raise ValueError("Parent QM9 row identity differs from manifest")
            partitions[roles[index]].append(len(records))
            records.append(manifest["records"][index])
            original.append(index)
            target.write(line)
    if len(records) != sum(SUBSET_COUNTS.values()):
        raise ValueError("Incomplete QM9 subset")
    source_sha = digest(output / "structures.jsonl")
    split = dict(version=1, source_sha256=source_sha, source_count=len(records), records=records,
                 partitions=partitions, counts={k: len(v) for k,v in partitions.items()},
                 protocol=dict(kind="qm9_parent_partition_group_hash_subset_v1", parent_source_sha256=data["sha256"],
                               parent_split_sha256=data["split_manifest_sha256"], training_seed_used=False,
                               selected_parent_indices=original, interpretation="12k subset; original partition membership and row bytes retained"))
    validate_manifest(split, source_sha256=source_sha, source_count=len(records))
    write_json(output / "split.json", split)
    report = dict(status="passed", kind="qm9_partition_subset", selected_count=len(records), clean_count=len(records),
                  parent_clean_count=CLEAN_COUNT, parent_dataset=data, parent_report_sha256=digest(parent_directory / "report.json"),
                  units=UNITS, split_counts=split["counts"], selected_parent_indices=selected,
                  dataset=dict(path=str(output / "structures.jsonl"), sha256=source_sha,
                               split_manifest=str(output / "split.json"), split_manifest_sha256=canonical(split)),
                  slurm_job_id=os.environ["SLURM_JOB_ID"], original_row_bytes_preserved=True,
                  interpretation="HOMO/LUMO 10k/1k/1k subset, not a full-QM9 benchmark")
    write_json(output / "report.json", report)
    return report
