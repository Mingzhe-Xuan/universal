"""Prepare complete GMTNet rank3/4 data with immutable primary dielectric anchors."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--piezo-source", type=Path, default=Path("data/downloads/gmtnet-jarvis-diele-piezo.pkl"))
    parser.add_argument("--elastic-source", type=Path, required=True)
    parser.add_argument("--dielectric-data", type=Path, default=Path("data/arxiv-v1/gmtnet-dielectric/structures.jsonl"))
    parser.add_argument("--dielectric-split", type=Path, default=Path("data/arxiv-v1/gmtnet-dielectric/split.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Full supplemental preparation must run through Slurm")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.supplemental_tensors import prepare_supplemental_tensors

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        parser.error("Use a clean fixed Git source checkout")
    result = prepare_supplemental_tensors(args.piezo_source, args.elastic_source, args.dielectric_data,
                                         args.dielectric_split, args.output, execution={
                                             "git_commit": commit, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                                             "python": sys.version, "source_checkout": str(Path.cwd().resolve())})
    print(result["status"], result["datasets_prepared"])


if __name__ == "__main__":
    main()
