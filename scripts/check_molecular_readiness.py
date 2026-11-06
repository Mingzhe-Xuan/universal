"""Join complete molecular CUDA preparation with the original900-frame CPU reference."""

import argparse
import json

from universal_gnn.benchmarks.molecular.readiness.runtime import check_molecular_readiness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["cgcnn", "alignn", "mace", "nequip", "custom_knn_gcn"], required=True)
    for name in ["capacity", "capacity-terminal", "parity", "parity-terminal", "output"]:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    report = check_molecular_readiness(args.model, args.capacity, args.capacity_terminal,
        args.parity, args.parity_terminal, args.output)
    print(json.dumps({key: report[key] for key in ["status", "preparation_gate_passed", "formal_training_ready"]}))


if __name__ == "__main__":
    main()
