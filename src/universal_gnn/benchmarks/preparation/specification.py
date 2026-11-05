"""Metadata checks shared by all original predictive task/seed preparation pairs."""

import copy
from dataclasses import replace
import getpass
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from ..execution.gates import case_spec, compatible_sources, file_sha, canonical_digest
from ..execution.runner import duration_seconds
from ..execution.slurm import running_gpu_allocation
from universal_gnn.data.splits import validate_manifest


def predictive_spec(matrix, pair_id):
    cases = [case for case in matrix["cases"] if case["pair_id"] == pair_id]
    if len(cases) != 2 or {c["initialization"] for c in cases} != {"pretrained", "scratch"}:
        raise ValueError("Select one complete predictive initialization pair")
    specs = [case_spec(matrix, case["id"]) for case in cases]
    first = specs[0]
    case = first["case"]
    return dict(pair_id=pair_id, cases=[s["case"] for s in specs], configs=first["configs"],
                task=case["task"], model=case["model"], seed=case["seed"], counts=first["counts"],
                source_structures=first["source_structures"], matrix_sha256=first["matrix_sha256"])


def runtime_context(spec):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Full predictive preparation must run through Slurm")
    environments = {"cgcnn": "universal-official", "alignn": "universal-official",
                    "mace": "universal-mace", "nequip": "universal"}
    if Path(sys.prefix).name != environments[spec["model"]]:
        raise RuntimeError("Use the original provider Python environment")
    commit = compatible_sources([])
    raw = subprocess.check_output(["scontrol", "show", "job", "-o", os.environ["SLURM_JOB_ID"]], text=True)
    fields = dict(token.split("=", 1) for token in shlex.split(raw) if "=" in token)
    allocation = running_gpu_allocation(fields, job_id=os.environ["SLURM_JOB_ID"], user=getpass.getuser())
    if fields.get("TimeLimit") == "UNLIMITED":
        raise RuntimeError("Full preparation requires a finite Slurm allocation")
    remaining = duration_seconds(fields["TimeLimit"]) - duration_seconds(fields["RunTime"])
    if remaining <= 0:
        raise RuntimeError("No Slurm preparation wall time remains")
    return dict(git_commit=commit, source_checkout=str(Path.cwd().resolve()), python=sys.executable,
                slurm_job_id=os.environ["SLURM_JOB_ID"], allocation=allocation,
                remaining_allocation_seconds=remaining)


def full_manifest(spec):
    config = spec["configs"]["pretrained"]
    manifest = json.loads(Path(config["dataset"]["split_manifest"]).read_text(encoding="utf8"))
    validate_manifest(manifest, source_sha256=config["dataset"]["sha256"], source_count=spec["source_structures"])
    if (manifest["counts"] != spec["counts"] or
            canonical_digest(manifest) != config["dataset"]["split_manifest_sha256"] or
            file_sha(config["dataset"]["path"]) != config["dataset"]["sha256"]):
        raise ValueError("Full source or frozen partition identity differs")
    return manifest


def reference_examples(structures, config):
    examples = [structures[0], structures[1]]
    reference = copy.deepcopy(config)
    if config["backbone"]["name"] == "cgcnn":
        reference["task"]["property"] = "_unused_reference_csv_slot"
        examples = [replace(item, targets={"_unused_reference_csv_slot": 0.}) for item in examples]
    return examples, reference


def physical_indices(probe, count):
    values = probe.get("worst_indices")
    if (count < 2 or not isinstance(values, list) or not values or
            any(type(i) is not int or not 0 <= i < count for i in values)):
        raise ValueError("Require valid full-scan worst training indices")
    selected = list(dict.fromkeys(values))[:2]
    if len(selected) == 1:
        selected.append(next(i for i in range(count) if i != selected[0]))
    return selected
