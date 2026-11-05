"""Prepare one complete frozen predictive pair through Slurm."""

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
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=7200)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Full predictive preparation must run through Slurm")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.preparation import prepare_predictive_pair

    matrix = json.loads(args.matrix.read_text(encoding="utf8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen matrix SHA256 differs")
    report = prepare_predictive_pair(matrix, args.pair, args.output, timeout=args.timeout)
    print(json.dumps({key: report[key] for key in ("status", "pair_id", "common_batch_size")}))


if __name__ == "__main__":
    main()
