"""Slurm-only exact afterany terminal telemetry, never model execution."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["gate", "stage"])
    parser.add_argument("--pair")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stage-output", type=Path)
    parser.add_argument("--definitions", default="runs/tensor-definition-control-1231/definitions/definitions.json")
    parser.add_argument("--primary-matrix", default="runs/arxiv-v1/definition-947/matrix.json")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Terminal telemetry must run through Slurm")
    if ((args.kind == "gate" and (not args.pair or args.receipt or args.stage_output)) or
            (args.kind == "stage" and (args.pair or not args.receipt or not args.stage_output))):
        parser.error("gate requires only --pair; stage requires only --receipt and --stage-output")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from universal_gnn.benchmarks.supplemental_tensors.telemetry import record_gate_terminal, record_stage_terminal
    result = (record_gate_terminal(dict(definitions=args.definitions, primary_matrix=args.primary_matrix), args.pair)
              if args.kind == "gate" else record_stage_terminal(args.receipt, args.stage_output))
    print(json.dumps(dict(status=result["status"], successful=result.get("successful"), job=result["entry"]["job"])))


if __name__ == "__main__":
    main()
