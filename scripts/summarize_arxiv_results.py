"""Export evidence-bound48-case single-seed metrics, paired differences and costs."""

import argparse
import json

from universal_gnn.benchmarks.reporting.runtime import write_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="results/paper-completed-20261105/formal-index.json")
    parser.add_argument("--scope", default="configs/arxiv_v1_scope.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = write_summary(args.index, args.scope, args.output)
    print(json.dumps({key: result[key] for key in ["accepted_cases", "missing_cases", "complete_pairs"]}))


if __name__ == "__main__":
    main()
