"""Submit a closed supplemental tensor pair after successful independent gates."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True)
    parser.add_argument("--preparation", required=True)
    parser.add_argument("--independent-gate", required=True)
    parser.add_argument("--definitions", default="runs/tensor-definition-control-1231/definitions/definitions.json")
    parser.add_argument("--primary-matrix", default="runs/arxiv-v1/definition-947/matrix.json")
    parser.add_argument("--post-hours", type=int, default=72)
    parser.add_argument("--verify-hours", type=int, default=4)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--plan-output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Supplemental pair planning/submission must run through Slurm")
    if args.plan_output is not None and (not args.check_only or args.plan_output.exists() or args.plan_output.is_symlink()):
        parser.error("--plan-output must be fresh and belongs only to --check-only")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.supplemental_tensors.submission import build_tensor_submission_plan, dispatch_tensor_pair
    options = dict(post_seconds=args.post_hours * 3600, verify_seconds=args.verify_hours * 3600)
    settings = dict(definitions=args.definitions, primary_matrix=args.primary_matrix)
    function = build_tensor_submission_plan if args.check_only else dispatch_tensor_pair
    result = function(settings, args.pair, args.preparation, args.independent_gate, **options)
    if args.plan_output is not None:
        with args.plan_output.open("x", encoding="utf8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result["status"], pair=args.pair, check_only=args.check_only)))


if __name__ == "__main__":
    main()
