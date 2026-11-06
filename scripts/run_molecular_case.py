"""Closed molecular training, planning and independent CPU scientific stages."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["gate", "plan", "submit", "train", "post", "verify"])
    parser.add_argument("--case", required=True)
    parser.add_argument("--preparation")
    parser.add_argument("--preparation-terminal")
    parser.add_argument("--budget-seconds", type=float)
    parser.add_argument("--post-seconds", type=int)
    parser.add_argument("--verify-seconds", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--postprocessing", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Molecular training, planning and scientific assessment require Slurm")
    if args.output and (args.output.exists() or args.output.is_symlink()):
        raise FileExistsError("Refusing to overwrite an existing plan/report/output")
    if args.stage in {"gate", "plan", "submit"} and args.output is None:
        parser.error("Gate/plan/submit requires a fresh --output to retain its complete result")
    from universal_gnn.benchmarks.molecular.formal.gates import check_execution_gate
    from universal_gnn.benchmarks.molecular.formal.runtime import run_molecular_case, postprocess_molecular_case, verify_molecular_case
    from universal_gnn.benchmarks.molecular.formal.submission import build_submission_plan, dispatch_case
    from universal_gnn.benchmarks.preflight import write_json
    if args.stage in {"gate", "plan", "submit", "train"}:
        if not args.preparation or not args.preparation_terminal or args.postprocessing:
            parser.error("Require actual joint --preparation and --preparation-terminal")
        if args.stage in {"plan", "submit"}:
            if args.post_seconds is None or args.verify_seconds is None or args.budget_seconds is not None:
                parser.error("Plan/submit requires explicit CPU post/verify seconds; full training budget is derived")
            action = build_submission_plan if args.stage == "plan" else dispatch_case
            result = action(args.case, args.preparation, args.preparation_terminal,
                post_seconds=args.post_seconds, verify_seconds=args.verify_seconds)
        elif args.stage == "train":
            if args.budget_seconds is None or args.output or args.post_seconds or args.verify_seconds:
                parser.error("Training requires its planned --budget-seconds and fixed output")
            result = run_molecular_case(args.case, args.preparation, args.preparation_terminal, budget_seconds=args.budget_seconds)
        else:
            if args.post_seconds or args.verify_seconds:parser.error("Gate does not accept CPU stage budgets")
            result = check_execution_gate(args.case, args.preparation, args.preparation_terminal, budget_seconds=args.budget_seconds)
    else:
        if not args.output or args.preparation or args.preparation_terminal or args.budget_seconds is not None or args.post_seconds is not None or args.verify_seconds is not None:
            parser.error("Post/verify requires fresh --output without training inputs")
        if (args.stage == "verify") != bool(args.postprocessing):parser.error("Only verify requires --postprocessing")
        result = (postprocess_molecular_case(args.case, args.output) if args.stage == "post"
                  else verify_molecular_case(args.case, args.postprocessing, args.output))
    if args.stage in {"gate", "plan", "submit"} and args.output:
        if args.output.exists() or args.output.is_symlink():raise FileExistsError("Refusing to overwrite a plan/report")
        write_json(args.output, result)
    print(json.dumps(dict(stage=args.stage, case_id=args.case, status=result.get("status", "checked"))))


if __name__ == "__main__":
    main()
