"""Export eight full-data frozen-backbone ablations after complete source checks."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-matrix", type=Path, default=Path("runs/arxiv-v1/definition-947/matrix.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Complete frozen definition/source audits must run through Slurm")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.execution.gates import compatible_sources, read_json
    from universal_gnn.benchmarks.frozen_backbones import write_frozen_definitions
    commit = compatible_sources([])
    result = write_frozen_definitions(read_json(args.primary_matrix), args.output)
    print(json.dumps(dict(status="defined_not_preflighted", git_commit=commit, slurm_job_id=os.environ["SLURM_JOB_ID"],
        frozen_defined_cases=len(result["cases"]), formal_training_runs=0, output=str(args.output))))


if __name__ == "__main__": main()
