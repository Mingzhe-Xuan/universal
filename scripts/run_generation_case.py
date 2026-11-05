"""Check, train or independently evaluate one frozen full generation case."""

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
    parser.add_argument("--stage", choices=("check", "train", "quality"), required=True)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--budget-seconds", type=float, required=True)
    parser.add_argument("--gate-output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Generation case checks/training/quality must run through Slurm")
    if args.stage in {"check", "train"} and args.preparation is None:
        parser.error("Check/train require --preparation")
    if args.gate_output and args.stage != "check":
        parser.error("--gate-output belongs to --stage check")
    if args.gate_output and args.gate_output.exists():
        parser.error("Gate output must be new")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.execution.gates import check_preparation
    from universal_gnn.benchmarks.generation.execution import generation_case, run_generation_case, run_generation_case_quality

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen matrix SHA256 differs")
    generation_case(matrix, args.case)
    if args.stage == "check":
        result = check_preparation(matrix, args.case, args.preparation, budget_seconds=args.budget_seconds, allow_generation=True)
    elif args.stage == "train":
        result = run_generation_case(matrix, args.case, args.preparation, budget_seconds=args.budget_seconds)
    else:
        result = run_generation_case_quality(matrix, args.case, budget_seconds=args.budget_seconds)
    if args.gate_output:
        with args.gate_output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result["status"], case_id=args.case, stage=args.stage)))


if __name__ == "__main__":
    main()
