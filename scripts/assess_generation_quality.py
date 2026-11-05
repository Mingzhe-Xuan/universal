"""Independently re-score saved generation samples without loading a GNN."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--matrix-sha256")
    parser.add_argument("--case")
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--training-report", type=Path)
    parser.add_argument("--quality-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Generation assessment must run through Slurm")
    if args.diagnostic:
        if not args.training_report or not args.quality_report or args.matrix or args.case or args.matrix_sha256:
            parser.error("Diagnostic mode needs only --training-report and --quality-report")
    elif not args.matrix or not args.matrix_sha256 or not args.case or args.training_report or args.quality_report:
        parser.error("Formal mode requires --matrix, --matrix-sha256 and --case")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.generation.assessment import assess_generation_case, assess_saved_quality

    if args.diagnostic:
        result = assess_saved_quality(args.training_report, args.quality_report, args.output, diagnostic=True)
    else:
        matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
        if canonical_digest(matrix) != args.matrix_sha256:
            parser.error("Frozen matrix SHA256 differs")
        result = assess_generation_case(matrix, args.case, args.output)
    print(json.dumps(dict(status=result["status"], scope=result["scope"],
                          samples_rescored=result["samples_rescored"], output=str(args.output))))


if __name__ == "__main__":
    main()
