"""Export the unchanged single-seed arXiv input definitions through CPU Slurm."""

import argparse
import json

from universal_gnn.benchmarks.experiments.bundle import export_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=".")
    parser.add_argument("--matrix", default="runs/arxiv-v1/definition-947/matrix.json")
    parser.add_argument("--scope", default="configs/arxiv_v1_scope.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(export_inputs(args.repository, args.matrix, args.scope, args.output)))


if __name__ == "__main__":
    main()
