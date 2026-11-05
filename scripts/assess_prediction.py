"""CPU Slurm post-processing and independent saved-output prediction assessment."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["post", "verify", "rescore"])
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--matrix-sha256")
    parser.add_argument("--case")
    parser.add_argument("--postprocessing", type=Path)
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--allow-legacy-classification", action="store_true")
    parser.add_argument("--training-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Prediction assessment must run through Slurm")
    if args.stage == "rescore":
        if (not args.diagnostic or not args.training_report or args.matrix or args.matrix_sha256 or
                args.case or args.postprocessing):
            parser.error("Saved-only diagnostic re-score requires --diagnostic and --training-report only")
    elif (not args.matrix or not args.matrix_sha256 or not args.case or args.diagnostic or args.training_report or args.allow_legacy_classification or
            (args.stage == "verify") != (args.postprocessing is not None)):
        parser.error("Formal post/verify requires --matrix, --matrix-sha256, --case; verify also needs --postprocessing")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.prediction_assessment import rescore_saved
    if args.stage == "rescore":
        from universal_gnn.benchmarks.prediction_assessment.numerics import forbid_models
        with forbid_models():
            result = rescore_saved(args.training_report, args.output, allow_legacy_classification=args.allow_legacy_classification)
    else:
        from universal_gnn.benchmarks.execution.gates import canonical_digest
        from universal_gnn.benchmarks.prediction_assessment.runtime import postprocess_case, verify_case
        matrix = json.loads(args.matrix.read_text(encoding="utf8"))
        if canonical_digest(matrix) != args.matrix_sha256:
            parser.error("Frozen original matrix fingerprint differs")
        result = (postprocess_case(matrix, args.case, args.output) if args.stage == "post" else
                  verify_case(matrix, args.case, args.postprocessing, args.output))
    print(json.dumps(dict(status=result["status"], scope=result["scope"], output=str(args.output))))


if __name__ == "__main__":
    main()
