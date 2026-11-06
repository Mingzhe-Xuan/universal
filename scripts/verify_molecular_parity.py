"""Compare all900 frozen molecular training structures with the original networks."""

import argparse
import json

from universal_gnn.benchmarks.molecular.parity.runtime import verify_molecular_parity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["cgcnn", "alignn", "mace", "nequip", "custom_knn_gcn"], required=True)
    parser.add_argument("--graph-scan", required=True)
    parser.add_argument("--graph-report-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = verify_molecular_parity(args.model, args.graph_scan, args.graph_report_sha256, args.output)
    print(json.dumps({key: report[key] for key in ["status", "model", "training_structures", "formal_training_ready"]}))


if __name__ == "__main__":
    main()
