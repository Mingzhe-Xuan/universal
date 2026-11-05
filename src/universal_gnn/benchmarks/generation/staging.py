"""Training readiness and mandatory trained-model quality are separate claims."""

import getpass
import math
import os
from pathlib import Path
import shlex
import subprocess

from ..execution.gates import _check_prepared_spec, check_preparation, read_json
from ..execution.runner import duration_seconds
from ..execution.slurm import running_gpu_allocation
from .execution import generation_case


def active_generation_case(matrix, identifier):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Staged generation checks/execution require Slurm")
    spec = generation_case(matrix, identifier)
    scope = read_json(Path(__file__).resolve().parents[4] / "configs/arxiv_v1_scope.json")
    if (scope.get("training_seeds") != [123] or scope.get("supplemental_training_seeds") != [123] or
            scope.get("base_matrix_sha256") != spec["matrix_sha256"] or
            identifier not in scope.get("active_case_ids", []) or spec["case"]["seed"] != 123):
        raise ValueError("Require an active original single-seed generation case")
    return spec


def check_generation_training_preparation(matrix, identifier, preparation, *, budget_seconds):
    spec = active_generation_case(matrix, identifier)
    return _check_prepared_spec(matrix, spec, preparation, budget_seconds=budget_seconds,
                                generation_training_only=True)


def revalidate_gate(matrix, identifier, gate):
    active_generation_case(matrix, identifier)
    if gate.get("training_readiness_only"):
        fresh = check_generation_training_preparation(matrix, identifier, gate["preparation"],
                                                       budget_seconds=gate["budget_seconds"])
    else:
        fresh = check_preparation(matrix, identifier, gate["preparation"],
                                  budget_seconds=gate["budget_seconds"], allow_generation=True)
    if {k: v for k, v in fresh.items() if k != "git_commit"} != {k: v for k, v in gate.items() if k != "git_commit"}:
        raise ValueError("Saved generation readiness differs from the complete original evidence")
    return fresh


def declared_quality_budget(requested):
    """Check a finite allocation without inventing an unavailable runtime estimate."""
    if type(requested) not in (int, float) or not math.isfinite(requested) or requested <= 0:
        raise ValueError("Require a finite positive declared quality budget")
    job = os.environ.get("SLURM_JOB_ID")
    if not job:
        raise RuntimeError("Quality requires a running Slurm GPU allocation")
    detail = subprocess.check_output(["scontrol", "show", "job", "-o", job], text=True)
    fields = dict(token.split("=", 1) for token in shlex.split(detail) if "=" in token)
    running_gpu_allocation(fields, job_id=job, user=getpass.getuser())
    remaining = requested if fields.get("TimeLimit") == "UNLIMITED" else (
        duration_seconds(fields["TimeLimit"]) - duration_seconds(fields["RunTime"]))
    if remaining <= 0:
        raise RuntimeError("The declared quality allocation has no remaining wall time")
    return min(requested, remaining)


def run_staged_generation_case(matrix, identifier, preparation, *, budget_seconds):
    spec = active_generation_case(matrix, identifier)
    root = Path(spec["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing generation case")
    gate = check_generation_training_preparation(matrix, identifier, preparation, budget_seconds=budget_seconds)
    from .execution import _run_generation_with_gate

    return _run_generation_with_gate(identifier, gate, budget_seconds=budget_seconds)


def run_staged_generation_quality(matrix, identifier, *, budget_seconds):
    active_generation_case(matrix, identifier)
    from .execution import _run_generation_case_quality

    return _run_generation_case_quality(matrix, identifier, budget_seconds=budget_seconds, staged=True)


def assess_staged_generation_case(matrix, identifier, output):
    spec = active_generation_case(matrix, identifier)
    root = Path(spec["case"]["run_directory"])
    gate = read_json(root / "generation-gate.json")
    revalidate_gate(matrix, identifier, gate)
    status = read_json(root / "formal-status.json")
    quality_path = Path(status["quality"])
    if not quality_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Quality belongs outside the selected generation case")
    quality = read_json(quality_path)
    from .sampling_failures import sampling_policy

    policy = sampling_policy()
    if status.get("sampling_failure_policy") != policy or quality.get("sampling_failure_policy") != policy:
        raise ValueError("Quality must bind the same explicit sampling failure policy")
    from .assessment import assess_generation_case
    from ..prediction_assessment.numerics import forbid_models

    with forbid_models():
        return assess_generation_case(matrix, identifier, output)
