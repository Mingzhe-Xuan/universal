"""Slurm-only actual CUDA graph/capacity/physics for registered molecular groups."""

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from universal_gnn.benchmarks.molecular.contracts import MODELS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=7200)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Molecular CUDA capacity requires Slurm")
    from universal_gnn.benchmarks.molecular.capacity import prepare_molecular_capacity
    result = prepare_molecular_capacity(args.model, args.output, timeout=args.timeout)
    print(json.dumps({key: result[key] for key in ["status", "model", "common_batch_size", "formal_training_ready"]}))


if __name__ == "__main__":
    main()
