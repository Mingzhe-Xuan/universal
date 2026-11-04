"""Run each capacity attempt in a disposable process; never retry unknown failures."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temporary, path)


def _positive(value, name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def run_preflight(config, output, *, probe, phase="train", python=None, timeout=3600,
                  worker_module="universal_gnn.benchmarks.probe_worker"):
    """Return a capacity report, preserving the caller's config and initialization.

    A pass means only that the supplied probe fits. Dataset coverage, validation and
    matched initialization comparisons remain separate experiment requirements.
    """
    initial_batch = _positive(config.get("batch_size", 32), "batch_size")
    if phase not in {"train", "sample"}:
        raise ValueError("phase must be train or sample")
    if not str(config.get("device", "cpu")).startswith("cuda"):
        raise ValueError("CUDA capacity preflight requires an explicit CUDA device")
    if not isinstance(probe, dict) or not probe.get("indices"):
        raise ValueError("probe.indices must explicitly identify training records")
    indices = probe["indices"]
    if any(not isinstance(i, int) or isinstance(i, bool) or i < 0 for i in indices):
        raise ValueError("probe indices must be nonnegative integers")
    if len(set(indices)) != len(indices):
        raise ValueError("probe indices must be unique")
    _positive(probe.get("measure_batches", 100), "measure_batches")
    _positive(probe.get("warmup_batches", 2), "warmup_batches")
    if config.get("max_atoms") is not None:
        raise ValueError("Capacity probes do not allow max_atoms to silently reduce the tested batch")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Never reuse success files from another experiment or an interrupted invocation.
    if any(output.iterdir()):
        raise ValueError("Preflight output directory must be empty")
    report = {"version": 1, "phase": phase, "status": "running", "passed": False,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "initial_batch_size": initial_batch, "final_batch_size": None,
              "config": copy.deepcopy(config), "probe": copy.deepcopy(probe), "attempts": [],
              "interpretation": "capacity of supplied probe; not proof of full-data coverage"}
    write_json(output / "report.json", report)
    batch_size = initial_batch
    while True:
        attempt_dir = output / f"attempt-{len(report['attempts']) + 1:02d}-b{batch_size}"
        attempt_dir.mkdir()
        candidate = copy.deepcopy(config)
        candidate["batch_size"] = batch_size
        request = {"config": candidate, "probe": probe, "phase": phase}
        write_json(attempt_dir / "request.json", request)
        command = [str(python or sys.executable), "-m", worker_module,
                   str(attempt_dir / "request.json"), str(attempt_dir / "result.json")]
        attempt = {"batch_size": batch_size, "directory": str(attempt_dir), "status": "process_error"}
        with (attempt_dir / "stdout.log").open("w", encoding="utf-8") as stdout, \
                (attempt_dir / "stderr.log").open("w", encoding="utf-8") as stderr:
            try:
                process = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=timeout, check=False)
                attempt["returncode"] = process.returncode
            except subprocess.TimeoutExpired:
                attempt["status"] = "timeout"
        result_path = attempt_dir / "result.json"
        if result_path.exists():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
                valid = (isinstance(result, dict) and result.get("version") == 1 and
                         result.get("batch_size") == batch_size and result.get("phase") == phase)
                if not valid:
                    raise ValueError("Worker result identity mismatch")
                attempt["worker"] = result
                if attempt.get("returncode") == 0 and result.get("status") == "passed":
                    from .resolution import resolved_candidate

                    accepted = resolved_candidate(candidate, result)
                    attempt["status"] = "passed"
                elif (attempt.get("returncode") == 42 and result.get("status") == "cuda_oom"
                      and result.get("error_type") == "cuda_out_of_memory"):
                    attempt["status"] = "cuda_oom"
                elif attempt["status"] != "timeout":
                    attempt["status"] = "failed"
            except (OSError, ValueError, TypeError) as error:
                attempt["result_error"] = str(error)
                if attempt["status"] != "timeout":
                    attempt["status"] = "invalid_result"
        report["attempts"].append(attempt)
        if attempt["status"] == "passed":
            report.update(status="passed", passed=True, final_batch_size=batch_size,
                          effective_batch_size=batch_size, gradient_accumulation_steps=1)
            write_json(output / "config.resolved.json", accepted)
        elif attempt["status"] != "cuda_oom" or batch_size == 1:
            report["status"] = "failed"
        write_json(output / "report.json", report)
        if report["status"] != "running":
            return report
        batch_size = max(1, batch_size // 2)


def main():
    parser = argparse.ArgumentParser(description="Isolated CUDA batch capacity preflight; run through Slurm")
    parser.add_argument("config", type=Path)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=["train", "sample"], default="train")
    parser.add_argument("--timeout", type=float, default=3600)
    args = parser.parse_args()
    from universal_gnn.engine.configuration import load_config

    report = run_preflight(load_config(args.config), args.output,
                           probe=json.loads(args.probe.read_text(encoding="utf-8")),
                           phase=args.phase, timeout=args.timeout)
    print(json.dumps({key: report[key] for key in ("status", "final_batch_size", "phase")}))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
