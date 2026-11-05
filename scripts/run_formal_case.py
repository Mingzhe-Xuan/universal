"""Check or run one full predictive case from its accepted complete-data preparation."""

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
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--budget-seconds", type=float, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--gate-output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Formal preparation checks and training must run through Slurm")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.execution import check_preparation, run_formal_case

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen matrix SHA256 differs")
    if args.gate_output and not args.check_only:
        parser.error("--gate-output belongs to --check-only")
    if args.gate_output and args.gate_output.exists():
        parser.error("Gate output must be new")
    execute = check_preparation if args.check_only else run_formal_case
    result = execute(matrix, args.case, args.preparation, budget_seconds=args.budget_seconds)
    if args.gate_output:
        with args.gate_output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result["status"], case_id=args.case, check_only=args.check_only)))


if __name__ == "__main__":
    main()
