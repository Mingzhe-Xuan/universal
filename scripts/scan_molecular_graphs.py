"""Construct every accepted molecular native input through Slurm; never evaluate a GNN."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["cgcnn", "alignn", "mace", "nequip", "custom_knn_gcn"], required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("All molecular native graph construction requires Slurm")
    from universal_gnn.benchmarks.molecular.graphs import scan_molecular_graphs

    result = scan_molecular_graphs(args.model, args.output, device=args.device)
    print(json.dumps({key: result[key] for key in ("status", "model", "device", "source_structures", "training_structures", "numerical_capacity_acceptance", "formal_training_runs")}))


if __name__ == "__main__":
    main()
