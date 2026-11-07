"""Inventory explicit committed adapter/plugin source boundaries on CPU Slurm."""

import argparse
import json
import os
import re

from universal_gnn.benchmarks.code_footprint.runtime import write_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=".")
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[1-9][0-9]*", os.environ.get("SLURM_JOB_ID", "")):
        parser.error("Run the complete source inventory through CPU Slurm")
    result = write_inventory(args.repository, args.commit, args.output)
    print(json.dumps(dict(measured_commit=result["measured_commit"], groups=len(result["groups"]), **result["totals"])))


if __name__ == "__main__":
    main()
