"""Known sampling-domain failures are invalid attempts, never memory qualification."""

from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import re
import subprocess

from ..execution.gates import file_sha, read_json
from ..experiments.registry import canonical_digest

POLICY_VERSION = "generation_invalid_geometry_attempt_v1"


def checked_failed_preparation_source(preparation, prepared, scan_commit, provider, *, graph_job):
    """Recover the original failed wrapper's source from its exact saved receipt."""
    if not isinstance(scan_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", scan_commit):
        raise ValueError("Failed preparation needs its executed graph source")
    claim = Path("runs/full-generation-preparations-" + scan_commit[:7] + "-claim")
    receipt_path = claim / "jobs.json"
    receipts = read_json(receipt_path)
    entry = receipts.get("preparations", {}).get(provider, {})
    job = prepared.get("slurm_job_id")
    expected_root = Path("runs/arxiv-v1/full-generation-preparation-" + str(job) + "-" + provider)
    request = claim / (provider + ".sh")
    source = Path("runs/source-checkouts") / scan_commit
    if (not isinstance(job, str) or not re.fullmatch(r"[1-9][0-9]*", job) or entry.get("job") != job or graph_job != job or
            Path(preparation).resolve() != expected_root.resolve() or entry.get("git_commit") != scan_commit or
            entry.get("status") != "submitted_preparation_only" or entry.get("formal_training_runs") != 0 or
            Path(entry.get("source_checkout", "")).resolve() != source.resolve() or
            Path(entry.get("request_path", "")).resolve() != request.resolve() or
            file_sha(request) != entry.get("request_sha256")):
        raise ValueError("Failed parent is not bound to its exact original preparation request")
    if (subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != scan_commit or
            subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()):
        raise ValueError("Original failed preparation source cache changed")
    control = receipts.get("control", {})
    control_job = control.get("job")
    if (not isinstance(control_job, str) or not re.fullmatch(r"[1-9][0-9]*", control_job) or
            control.get("git_commit") != scan_commit or
            Path(control.get("source_checkout", "")).resolve() != source.resolve() or
            file_sha(claim / "control.sh") != control.get("request_sha256")):
        raise ValueError("Failed preparation lacks its original source-bound control request")
    control_path = Path("runs/generation-preparation-control-" + control_job) / "report.json"
    accepted = read_json(control_path)
    if (accepted.get("status") != "passed" or accepted.get("git_commit") != scan_commit or
            accepted.get("slurm_job_id") != control_job or accepted.get("main_test_cases") != 8):
        raise ValueError("Original generation preparation control did not pass")
    return dict(git_commit=scan_commit, receipt=str(receipt_path), receipt_sha256=file_sha(receipt_path),
                request=str(request), request_sha256=file_sha(request), original_job=job,
                control_report=str(control_path), control_report_sha256=file_sha(control_path),
                control_request_sha256=file_sha(claim / "control.sh"),
                interpretation="Original failed parent has no success-only source stamp; exact saved preparation/control requests and executed graph/worker sources provide provenance, without rewriting that parent")


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
    trial = read_json(trial_path)
    if (Path(rows[0].get("directory", "")).resolve() != trial_path.parent.resolve() or
            canonical_digest(trial) != rows[0].get("report_sha256")):
        raise ValueError("Failed sampling trial canonical identity/path changed")
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
