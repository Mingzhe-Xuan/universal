"""Inspect complete inputs and write the full primary matrix through Slurm; never launch training."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=30)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Full input hashing/identity inspection must run through Slurm")
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output already exists; use a new full-matrix definition directory")
    from universal_gnn.benchmarks.experiments import registry, recipes

    repository = Path(__file__).resolve().parents[1]
    inputs = registry.inspect_registry(repository)
    matrix = recipes.build_matrix(inputs, epochs=args.epochs, learning_rate=args.learning_rate, patience=args.patience,
                                  run_root=str(args.output.parent / "cases"))
    matrix["preparation_execution"] = dict(
        git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip(),
        slurm_job_id=os.environ["SLURM_JOB_ID"], node=os.environ.get("SLURMD_NODENAME"),
        source_sha256={str(Path(path).resolve().relative_to(repository)):hashlib.sha256(Path(path).read_bytes()).hexdigest()
                       for path in (__file__, registry.__file__, recipes.__file__)})
    manifest = recipes.write_matrix(matrix, args.output)
    print(json.dumps(dict(status=matrix["status"], matrix=str(manifest), cases=len(matrix["cases"]),
                         completed_training_runs=matrix["completed_training_runs"], registry_sha256=matrix["registry_sha256"])))


if __name__ == "__main__":
    main()
