"""Freeze separate full-data rank3/4 configs; does not construct a GNN or submit jobs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-matrix", type=Path, default=Path("runs/arxiv-v1/definition-947/matrix.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Complete supplemental source audit must run through Slurm")
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output must be fresh")
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        parser.error("Use a clean fixed Git source checkout")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.supplemental_tensors.experiments import write_tensor_definitions
    definitions = write_tensor_definitions(json.loads(args.primary_matrix.read_text(encoding="utf8")), args.output)
    print(json.dumps(dict(defined_cases=len(definitions["cases"]), training_seeds=definitions["training_seeds"],
                         formal_training_runs=0, output=str(args.output))))


if __name__ == "__main__":
    main()
