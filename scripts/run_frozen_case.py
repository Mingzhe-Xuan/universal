"""Separate frozen full training, CPU post-processing and no-model verification."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["train", "post", "verify"])
    parser.add_argument("--definitions", default="runs/frozen-definition-control-1288/definitions/definitions.json")
    parser.add_argument("--primary-matrix", default="runs/arxiv-v1/definition-947/matrix.json")
    parser.add_argument("--case", required=True)
    parser.add_argument("--preparation")
    parser.add_argument("--independent-gate")
    parser.add_argument("--budget-seconds", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--postprocessing", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Frozen training and assessment must run through Slurm")
    if args.stage == "train":
        if (not args.preparation or not args.independent_gate or args.budget_seconds is None or
                args.output is not None or args.postprocessing is not None):
            parser.error("Training requires preparation, independent-gate and budget-seconds; output is fixed")
    elif (args.output is None or args.preparation or args.independent_gate or args.budget_seconds is not None or
          (args.stage == "verify") != (args.postprocessing is not None)):
        parser.error("Post/verify requires fresh --output; only verify accepts and requires --postprocessing")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.frozen_backbones.execution import (
        run_frozen_case, postprocess_frozen_case, verify_frozen_case)
    settings = dict(definitions=args.definitions, primary_matrix=args.primary_matrix)
    if args.stage == "train":
        result = run_frozen_case(settings, args.case, args.preparation, args.independent_gate,
                                 budget_seconds=args.budget_seconds)
    elif args.stage == "post":
        result = postprocess_frozen_case(settings, args.case, args.output)
    else:
        result = verify_frozen_case(settings, args.case, args.postprocessing, args.output)
    print(json.dumps(dict(status=result["status"], case_id=args.case, stage=args.stage)))


if __name__ == "__main__":
    main()
