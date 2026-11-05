"""Attach CPU post/verify stages to an already-dispatched predictive pair."""

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
    parser.add_argument("--dispatch-job", required=True)
    parser.add_argument("--post-hours", type=int, default=72)
    parser.add_argument("--verify-hours", type=int, default=4)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--plan-output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Assessment launch resolution must run through Slurm")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.execution.gates import canonical_digest
    from universal_gnn.benchmarks.prediction_assessment.submission import build_post_plan, dispatch_post_pair
    from universal_gnn.benchmarks.preflight import write_json
    matrix = json.loads(args.matrix.read_text(encoding="utf8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen original matrix fingerprint differs")
    options = dict(matrix_path=args.matrix, dispatch_job=args.dispatch_job,
                   post_seconds=args.post_hours * 3600, verify_seconds=args.verify_hours * 3600)
    if args.check_only:
        result = build_post_plan(matrix, args.pair, **options)
        if args.plan_output:
            with args.plan_output.open("x", encoding="utf8"):
                pass
            write_json(args.plan_output, result)
    else:
        if args.plan_output:
            parser.error("--plan-output is for --check-only")
        result = dispatch_post_pair(matrix, args.pair, **options)
    print(json.dumps(dict(status=result["status"], pair_id=args.pair, formal_training_runs_submitted=0)))


if __name__ == "__main__":
    main()
