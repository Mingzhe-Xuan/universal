"""Bind task-local evidence to the exact retained successful Slurm request."""

from pathlib import Path
import re
import shlex

from ...execution.gates import file_sha, read_json
from ...execution.runner import duration_seconds
from ...supplemental_tensors.telemetry import checked_fields, source_pinned


class Evidence:
    def __init__(self):
        self.sha256 = {}

    def path(self, path):
        path = Path(path)
        root = (Path.cwd() / "runs").resolve()
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or resolved == root:
            raise ValueError("Molecular preparation evidence must remain inside task runs")
        return path

    def bind(self, path, expected=None):
        path = self.path(path)
        digest = file_sha(path)
        previous = self.sha256.get(str(path))
        if (expected is not None and digest != expected) or (previous is not None and digest != previous):
            raise ValueError("Bound molecular evidence bytes changed")
        self.sha256[str(path)] = digest
        return path

    def read(self, path, expected=None):
        return read_json(self.bind(path, expected))

    def unchanged(self):
        for path, expected in self.sha256.copy().items():
            self.bind(path, expected)


def successful_parent(evidence, terminal_path, report_path):
    terminal = evidence.read(terminal_path)
    if (not re.fullmatch(r"[0-9a-f]{64}", terminal.get("receipt_sha256", ""))
            or not re.fullmatch(r"[0-9a-f]{64}", terminal.get("request_sha256", ""))):
        raise ValueError("Retained parent must bind the exact original receipt and request bytes")
    entry = evidence.read(terminal["receipt"], terminal.get("receipt_sha256"))
    report = evidence.read(report_path)
    if (terminal.get("status") != "retained" or terminal.get("successful") is not True
            or type(terminal.get("exit")) is not int or terminal.get("exit") != 0 or terminal.get("entry") != entry
            or entry.get("state") != "submitted" or type(entry.get("formal_training_runs")) is not int or entry.get("formal_training_runs") != 0
            or terminal.get("request_sha256") != entry.get("request_sha256")
            or report.get("slurm_job_id") != entry.get("job") or report.get("git_commit") != entry.get("git_commit")
            or report.get("source_checkout") != entry.get("source_checkout")
            or not re.fullmatch(r"[1-9][0-9]*", terminal.get("observer_slurm_job", ""))
            or terminal["observer_slurm_job"] == entry.get("job")):
        raise ValueError("Require the exact successful retained parent and its receipt/report identity")
    evidence.bind(entry["request_path"], entry["request_sha256"])
    artifacts = terminal.get("artifact_sha256", {})
    if artifacts.get(str(report_path)) != file_sha(report_path):
        raise ValueError("Parent terminal does not bind the exact successful report bytes")
    for path, digest in artifacts.items():
        evidence.bind(path, digest)
    fields = dict(token.split("=", 1) for token in shlex.split(terminal.get("raw", "")) if "=" in token)
    if fields != terminal.get("fields") or fields.get("JobState") != "COMPLETED" or fields.get("ExitCode") != "0:0":
        raise ValueError("Retained terminal does not prove completed0:0")
    argv = entry.get("sbatch_argv", [])
    flags = dict(token.split("=", 1) for token in argv if token.startswith("--") and "=" in token)
    if (not argv or argv[0] != "sbatch" or "--no-requeue" not in argv
            or flags.get("--partition") != "compute" or flags.get("--nodelist") != "node42"
            or flags.get("--chdir") != entry["source_checkout"] or flags.get("--comment") != entry.get("submission_token")
            or not re.fullmatch(r"[0-9a-f]{40}", entry.get("git_commit", ""))
            or entry.get("source_checkout") != "/home/xmz/universal/runs/source-checkouts/" + entry["git_commit"]
            or Path(entry.get("output", "")).resolve() != Path(report_path).parent.resolve()):
        raise ValueError("Original request source/token/output/resources differ")
    cpus = int(flags["--cpus-per-task"])
    memory = flags["--mem"]
    gres = flags.get("--gres", "gpu:0")
    if not re.fullmatch(r"[1-9][0-9]*G", memory) or not re.fullmatch(r"gpu:[0-9]+", gres):
        raise ValueError("Unsupported original memory/GPU request")
    checked_fields(fields, job=entry["job"], name=flags["--job-name"], source=entry["source_checkout"],
        cpus=cpus, memory=int(memory[:-1]), seconds=duration_seconds(flags["--time"]),
        gpus=int(gres.split(":")[1]), token=entry["submission_token"], nice=int(flags["--nice"]))
    source_pinned(entry)
    return entry
