"""Explicit training-only readiness and full trained-model generation evaluation."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--matrix-sha256", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--stage", choices=("check", "train", "quality", "verify"), required=True)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--budget-seconds", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("All generation stages require Slurm")
    if args.stage in {"check", "train"} and args.preparation is None:
        parser.error("Check/train require --preparation")
    if args.stage != "verify" and args.budget_seconds is None:
        parser.error("Check/train/quality require --budget-seconds")
    if args.stage in {"check", "verify"} and args.output is None:
        parser.error("Check/verify require a new --output")
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("Output must be new")
    if args.output is not None and args.stage not in {"check", "verify"}:
        parser.error("--output belongs to check/verify")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.generation.staging import (
        active_generation_case, check_generation_training_preparation, run_staged_generation_case,
        run_staged_generation_quality, assess_staged_generation_case)

    matrix = json.loads(args.matrix.read_text(encoding="utf8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen matrix SHA256 differs")
    active_generation_case(matrix, args.case)
    if args.stage == "check":
        result = check_generation_training_preparation(matrix, args.case, args.preparation, budget_seconds=args.budget_seconds)
        with args.output.open("x", encoding="utf8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    elif args.stage == "train":
        result = run_staged_generation_case(matrix, args.case, args.preparation, budget_seconds=args.budget_seconds)
    elif args.stage == "quality":
        result = run_staged_generation_quality(matrix, args.case, budget_seconds=args.budget_seconds)
    else:
        result = assess_staged_generation_case(matrix, args.case, args.output)
    print(json.dumps(dict(status=result["status"], case_id=args.case, stage=args.stage)))


if __name__ == "__main__":
    main()
