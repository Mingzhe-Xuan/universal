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
    arguments = parser.parse_args()
    if arguments.command == "train":
        from universal_gnn.engine.training import run_training

        config = json.loads(arguments.config.read_text(encoding="utf-8"))
        report = run_training(config, arguments.output)
        print(json.dumps({"passed": report["passed"], "structures": len(report["structures"]),
                          "initial_loss": report["initial_loss"], "final_loss": report["final_loss"]}))


if __name__ == "__main__":
    main()
