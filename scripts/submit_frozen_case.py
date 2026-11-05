"""Plan/submit one original frozen ablation after its independent CUDA gate."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--preparation", required=True)
    parser.add_argument("--independent-gate", required=True)
    parser.add_argument("--definitions", default="runs/frozen-definition-control-1288/definitions/definitions.json")
    parser.add_argument("--primary-matrix", default="runs/arxiv-v1/definition-947/matrix.json")
    parser.add_argument("--post-hours", type=int, default=72)
    parser.add_argument("--verify-hours", type=int, default=4)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--plan-output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Frozen planning/submission must run through Slurm")
    if args.plan_output is not None and (not args.check_only or args.plan_output.exists() or args.plan_output.is_symlink()):
        parser.error("--plan-output must be fresh and belongs only to --check-only")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.frozen_backbones.submission import build_frozen_submission_plan, dispatch_frozen_case
    function = build_frozen_submission_plan if args.check_only else dispatch_frozen_case
    settings = dict(definitions=args.definitions, primary_matrix=args.primary_matrix)
    result = function(settings, args.case, args.preparation, args.independent_gate,
        post_seconds=args.post_hours * 3600, verify_seconds=args.verify_hours * 3600)
    if args.plan_output is not None:
        with args.plan_output.open("x", encoding="utf8") as stream:json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result["status"], case_id=args.case, check_only=args.check_only)))


if __name__ == "__main__":main()
