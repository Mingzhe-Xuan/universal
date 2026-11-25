"""QM9 data, CPU controls, GPU capacity, full training and independent assessment."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "smoke", "preflight", "train", "assess", "terminal"])
    parser.add_argument("--raw", default="data/qm9/raw")
    parser.add_argument("--data", default="data/qm9/prepared-v1")
    parser.add_argument("--matrix", default="runs/arxiv-v1/definition-947/matrix.json")
    parser.add_argument("--definitions", default="runs/qm9-v1/definition")
    parser.add_argument("--model", choices=["cgcnn", "alignn", "mace", "nequip"])
    parser.add_argument("--case")
    parser.add_argument("--output")
    parser.add_argument("--preparation")
    parser.add_argument("--smoke")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("QM9 numerical work, full conversion and terminal checks require Slurm")
    from universal_gnn.data.preparation.qm9.conversion import write_json
    try:
        if args.stage == "prepare":
            from universal_gnn.data.preparation.qm9 import prepare_qm9
            from universal_gnn.benchmarks.qm9.definitions import define
            prepare_qm9(args.raw, args.data)
            result = define(args.matrix, args.data, args.definitions)
        elif args.stage == "terminal":
            from universal_gnn.benchmarks.qm9.submission import record_terminal
            result = record_terminal(args.receipt)
        elif args.stage == "assess":
            from universal_gnn.benchmarks.qm9.assessment import assess
            result = assess(args.definitions, args.case)
        else:
            from universal_gnn.benchmarks.qm9.runtime import smoke, preflight, train
            if args.stage == "smoke":
                result = smoke(args.definitions, args.model, args.output)
            elif args.stage == "preflight":
                result = preflight(args.definitions, args.model, args.output, args.smoke)
            else:
                result = train(args.definitions, args.case, args.preparation)
    except Exception as error:
        if args.output:
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=True)
            write_json(output / "failure.json", dict(status="failed", stage=args.stage, error_type=type(error).__name__, error=str(error)))
        raise
    print(json.dumps(dict(stage=args.stage, status=result.get("status", "defined"))))


if __name__ == "__main__":
    main()
