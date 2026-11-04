"""Evaluate original public heads on full frozen matching-task test partitions."""

import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--provider", choices=("cgcnn", "alignn", "mace", "nequip"), required=True)
    parser.add_argument("--matrix-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Native baseline evaluation must run through Slurm")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.experiments.registry import canonical_digest
    from universal_gnn.benchmarks.native_heads import evaluate_native_baseline

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if canonical_digest(matrix) != args.matrix_sha256:
        parser.error("Frozen matrix SHA256 differs")
    report = evaluate_native_baseline(matrix, args.provider, args.output)
    print(json.dumps(dict(status=report["status"], provider=report["provider"], metrics=report["heldout"]["metrics"])))


if __name__ == "__main__":
    main()
