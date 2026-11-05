"""Check a completed full pair preparation, then submit its formal Slurm stages."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--matrix-sha256", required=True)
    parser.add_argument("--pair", required=True)
    parser.add_argument("--preparation", required=True, type=Path)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--plan-output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Pair gate/submission must run through Slurm")
    if args.plan_output and (not args.check_only or args.plan_output.exists()):
        parser.error("--plan-output requires --check-only and a new output file")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.submission import build_submission_plan, dispatch_pair

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen matrix SHA256 differs")
    execute = build_submission_plan if args.check_only else dispatch_pair
    result = execute(matrix, args.pair, args.preparation, matrix_path=args.matrix)
    if args.plan_output:
        with args.plan_output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result["status"], pair_id=args.pair, check_only=args.check_only)))


if __name__ == "__main__":
    main()
