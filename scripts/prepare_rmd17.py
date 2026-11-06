"""Convert complete pinned author rMD17 ethanol and its declared split in Slurm."""

import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Complete rMD17 preparation requires Slurm")
    from universal_gnn.data.preparation.rmd17 import prepare_rmd17

    repository = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(repository), "status", "--porcelain"], text=True).strip():
        parser.error("Use a clean pinned source checkout")
    report = prepare_rmd17(args.raw, args.output, execution=dict(git_commit=commit, slurm_job_id=os.environ["SLURM_JOB_ID"]))
    print(json.dumps({key: report[key] for key in ("status", "source_records", "split_counts", "dataset_sha256", "elapsed_seconds")}))


if __name__ == "__main__":
    main()
