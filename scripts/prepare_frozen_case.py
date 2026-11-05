"""Prepare/check one original full-data pretrained frozen-backbone ablation."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "check"))
    parser.add_argument("--case", required=True)
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--reference-preparation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-seconds", type=float)
    parser.add_argument("--timeout", type=float, default=7200)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Frozen preparation/checks require Slurm")
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output must be new")
    if args.stage == "prepare" and args.reference_preparation is None:
        parser.error("Prepare requires --reference-preparation")
    if args.stage == "check" and args.preparation is None:
        parser.error("Check requires --preparation")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.frozen_backbones.readiness import prepare_frozen_case, check_frozen_preparation

    if args.stage == "prepare":
        result = prepare_frozen_case(args.case, args.reference_preparation, args.output, timeout=args.timeout)
    else:
        result = check_frozen_preparation(args.case, args.preparation, budget_seconds=args.budget_seconds)
        with args.output.open("x", encoding="utf8") as stream:json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(case_id=args.case, stage=args.stage, status=result["status"])))


if __name__ == "__main__":main()
