"""Select a validation-only threshold and assess saved complete CPU predictions."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--prediction-sha256", required=True)
    parser.add_argument("--prediction-bytes", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Complete classification assessment must run through Slurm")
    from universal_gnn.benchmarks.classification_assessment.runtime import assess_threshold

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise RuntimeError("Classification assessment requires a clean tracked source checkout")
    result = assess_threshold(args.report, args.predictions, args.output,
        prediction_sha256=args.prediction_sha256, prediction_bytes=args.prediction_bytes)
    if (subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != commit or
            subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip()):
        (args.output / "report.json").unlink()
        raise RuntimeError("Source checkout changed during classification assessment")
    paths = ["src/universal_gnn/benchmarks/classification_assessment/selection.py",
             "src/universal_gnn/benchmarks/classification_assessment/runtime.py",
             "src/universal_gnn/engine/evaluation/metrics.py",
             "src/universal_gnn/benchmarks/prediction_assessment/contracts.py",
             "src/universal_gnn/benchmarks/prediction_assessment/streaming.py",
             "src/universal_gnn/benchmarks/prediction_assessment/rescoring.py",
             "scripts/evaluate_classification_threshold.py"]
    result["execution"] = dict(git_commit=commit, source_checkout_clean=True,
        slurm_job_id=os.environ["SLURM_JOB_ID"], device="cpu",
        source_sha256={path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths})
    (args.output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps(dict(status=result["status"], test_structures=result["test_structures"], output=str(args.output))))


if __name__ == "__main__":
    main()
