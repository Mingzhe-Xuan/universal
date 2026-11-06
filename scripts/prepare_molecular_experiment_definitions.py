"""Audit the complete frozen molecular source and export nine supplementary configs; Slurm only."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=Path("runs/arxiv-v1/definition-947/matrix.json"))
    parser.add_argument("--data-directory", type=Path, default=Path("data/arxiv-v1/rmd17-ethanol-prepared-4f30bea"))
    parser.add_argument("--raw-directory", type=Path, default=Path("data/arxiv-v1/molecular-rmd17-v4/raw"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Complete molecular source inspection/export requires Slurm")
    from universal_gnn.benchmarks.molecular.definitions import write_molecular_definitions
    from universal_gnn.benchmarks.execution.gates import compatible_sources

    execution = dict(git_commit=compatible_sources([]), slurm_job_id=os.environ["SLURM_JOB_ID"])
    definitions = write_molecular_definitions(json.loads(args.matrix.read_bytes()), args.output,
        data_directory=args.data_directory, raw_directory=args.raw_directory, execution=execution)
    print(json.dumps(dict(status="defined_not_preflighted", cases=len(definitions["cases"]),
                         definitions=str(args.output / "definitions.json"), formal_training_runs=0)))


if __name__ == "__main__":
    main()
