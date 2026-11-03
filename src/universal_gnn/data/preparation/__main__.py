import argparse
import json
import os
from pathlib import Path
import subprocess

from .jarvis import prepare_release


def main():
    parser = argparse.ArgumentParser(description="Prepare an entire fixed release; execute through Slurm")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=["bandgap", "phonon_dos", "electron_dos", "dielectric"], required=True)
    parser.add_argument("--source-sha256", help="Required for the GMTNet pickle; pinned downloaded-source SHA256")
    parser.add_argument("--split-seed", type=int, default=0)
    parser.add_argument("--metal-threshold", type=float, default=.01)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Full release preparation must run through Slurm")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    execution = {"git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
                 "slurm_job_id": os.environ["SLURM_JOB_ID"], "node": os.environ.get("SLURMD_NODENAME")}
    if args.kind == "dielectric":
        if not args.source_sha256:
            parser.error("GMTNet pickle requires --source-sha256 from the recorded source receipt")
        from .gmtnet import prepare_gmtnet

        audit = prepare_gmtnet(args.source, args.output, expected_sha256=args.source_sha256,
                              split_seed=args.split_seed, execution=execution)
    else:
        if args.source_sha256:
            parser.error("--source-sha256 currently applies only to the GMTNet pickle")
        audit = prepare_release(args.source, args.output, kind=args.kind,
                                split_seed=args.split_seed, metal_threshold=args.metal_threshold,
                                execution=execution)
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
