"""Build complete original training graph probes on a Slurm compute node."""

import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Complete graph scanning must run through Slurm")
    from universal_gnn.engine.configuration import load_config
    from universal_gnn.benchmarks.probes.native_scan import scan_training_graphs

    probe = scan_training_graphs(load_config(args.config), args.output)
    print(json.dumps(dict(status="complete", structures=probe["coverage"]["structures"],
                          selected=len(probe["indices"]), output=args.output)))


if __name__ == "__main__":
    main()
