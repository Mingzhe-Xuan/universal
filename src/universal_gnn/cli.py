from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Universal GNN output-driven tasks")
    sub = parser.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train")
    train.add_argument("config", type=Path)
    train.add_argument("--output", type=Path, required=True)
    infer = sub.add_parser("infer")
    infer.add_argument("checkpoint", type=Path)
    infer.add_argument("dataset")
    infer.add_argument("--output", type=Path, required=True)
    infer.add_argument("--device", default="cpu")
    infer.add_argument("--limit", type=int)
    arguments = parser.parse_args()
    if arguments.command == "train":
        from universal_gnn.engine.training import run_training

        config = json.loads(arguments.config.read_text(encoding="utf-8"))
        report = run_training(config, arguments.output)
        print(json.dumps({"passed": report["passed"], "structures": len(report["structures"]),
                          "initial_loss": report["initial_loss"], "final_loss": report["final_loss"]}))
    elif arguments.command == "infer":
        from universal_gnn.engine.inference import run_inference

        result = run_inference(arguments.checkpoint, arguments.dataset, arguments.output,
                               device=arguments.device, limit=arguments.limit)
        print(json.dumps({"structures": len(result["structures"]), "output": str(arguments.output)}))


if __name__ == "__main__":
    main()
