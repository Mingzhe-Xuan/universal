"""Known sampling-domain failures are invalid attempts, never memory qualification."""

from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import re

from ..execution.gates import file_sha, read_json

POLICY_VERSION = "generation_invalid_geometry_attempt_v1"


def image_budget_failure(error_type, message):
    return error_type == "ValueError" and re.fullmatch(
        r"Cell requires [1-9][0-9]* periodic images; check cell/cutoff", message) is not None


def sampling_policy():
    return dict(version=POLICY_VERSION, source_sha256=file_sha(Path(__file__)),
        changed_sampling_arithmetic=False, changed_rng=False, changed_steps=False,
        known_additional_failure="periodic_image_budget_guard", unknown_errors="propagate", cuda_oom="propagate")


@contextmanager
def invalid_geometry_attempts(denoiser_type):
    """Preserve every successful call; adapt only the known graph-budget guard."""
    original = denoiser_type.sample
    @wraps(original)
    def sample(self, *args, **kwargs):
        try:
            return original(self, *args, **kwargs)
        except ValueError as error:
            if not image_budget_failure(type(error).__name__, str(error)):
                raise
            raise FloatingPointError("periodic_image_budget_guard: " + str(error)) from error
    denoiser_type.sample = sample
    try:
        yield
    finally:
        denoiser_type.sample = original


def checked_untrained_sampling_failure(preparation):
    """Bind an actual failed sampler; do not mark it as a passed full preparation."""
    root = Path(preparation) / "sample-capacity"
    path = root / "report.json"
    report = read_json(path)
    if (report.get("status") != "failed" or report.get("passed") is not False or report.get("phase") != "sample" or
            report.get("failed_stage") != "individual" or report.get("failed_initialization") not in {"pretrained", "scratch"}):
        raise ValueError("Require the exact known untrained sampling failure boundary")
    mode = report["failed_initialization"]
    rows = [row for row in report.get("trials", []) if row.get("stage") == "individual" and row.get("initialization") == mode and row.get("passed") is False]
    if len(rows) != 1:
        raise ValueError("Missing exact failed sampling trial")
    trial_path = root / "individual" / mode / "report.json"
    if (Path(rows[0].get("directory", "")).resolve() != trial_path.parent.resolve() or
            file_sha(trial_path) != rows[0].get("report_sha256")):
        raise ValueError("Failed sampling trial bytes/path changed")
    trial = read_json(trial_path)
    attempts = trial.get("attempts", [])
    if trial.get("status") != "failed" or trial.get("passed") is not False or not attempts:
        raise ValueError("Missing failed untrained sampler attempts")
    final = attempts[-1]
    worker = final.get("worker") or {}
    error_type, message = worker.get("error_type"), worker.get("error", "")
    known = image_budget_failure(error_type, message) or (
        error_type == "FloatingPointError" and message in {"Nonfinite node output", "Nonfinite generated structure", "Nonfinite generated geometry"})
    if (final.get("status") != "failed" or worker.get("status") != "failed" or worker.get("phase") != "sample" or
            worker.get("stage") != "sample" or not known):
        raise ValueError("Unknown or memory sampling failures require separate diagnosis")
    return dict(status="unqualified_untrained_sampling_failure", initialization=mode,
        report=str(path), report_sha256=file_sha(path), trial=str(trial_path), trial_sha256=file_sha(trial_path),
        error_type=error_type, error=message, sampling_capacity_passed=False,
        interpretation="Training evidence is checked separately; this remains a failed sampling preparation, not throughput or quality evidence")
