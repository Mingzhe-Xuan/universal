from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _legacy_main(argv):
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
    arguments = parser.parse_args(argv)
    if arguments.command == "train":
        from universal_gnn.engine.training import run_training
        from universal_gnn.engine.configuration import load_config

        config = load_config(arguments.config)
        report = run_training(config, arguments.output)
        print(json.dumps({"passed": report["passed"], "structures": len(report["structures"]),
                          "initial_loss": report["initial_loss"], "final_loss": report["final_loss"]}))
    elif arguments.command == "infer":
        from universal_gnn.engine.inference import run_inference

        result = run_inference(arguments.checkpoint, arguments.dataset, arguments.output,
                               device=arguments.device, limit=arguments.limit)
        print(json.dumps({"structures": len(result["structures"]), "output": str(arguments.output)}))


def _flag_parser():
    parser = argparse.ArgumentParser(description="Universal GNN tasks: select model, data and task")
    parser.add_argument("--mode", choices=["train", "infer"], required=True)
    parser.add_argument("--model", help="Built-in backbone name or plugin:/directory")
    parser.add_argument("--dataset", help="Structure file or plugin:/directory")
    parser.add_argument("--resume", type=Path, help="Training continuation / inference checkpoint")
    parser.add_argument("--task", help="Property name, forcefield, or generation")
    parser.add_argument("--config", type=Path, help="YAML or JSON configuration")
    parser.add_argument("--logging", type=Path, help="Directory for logs, resolved config and report")
    parser.add_argument("--save", type=Path, help="Training checkpoint file")
    parser.add_argument("--results", type=Path, help="Inference JSON file")
    parser.add_argument("--device")
    parser.add_argument("--epochs", type=int, help="Total target epochs, including completed epochs on resume")
    parser.add_argument("--limit", type=int, help="Maximum structures for inference")
    return parser


def _prepare(arguments):
    import torch
    from universal_gnn.engine.configuration import load_config, resolve_config
    from universal_gnn.engine.runtime import check_model_config, checkpoint_config

    train = arguments.mode == "train"
    if train:
        if arguments.save is None:
            raise ValueError("--save is required for training")
        if arguments.results is not None or arguments.limit is not None:
            raise ValueError("--results and --limit are inference-only options")
    else:
        if arguments.resume is None or arguments.results is None:
            raise ValueError("Inference requires --resume and --results")
        if arguments.save is not None or arguments.epochs is not None:
            raise ValueError("--save and --epochs are training-only options")
        if arguments.limit is not None and arguments.limit < 1:
            raise ValueError("--limit must be positive")
    saved = torch.load(arguments.resume, map_location="cpu", weights_only=True) if arguments.resume else None
    base = checkpoint_config(saved) if saved is not None else None
    config = resolve_config(load_config(arguments.config) if arguments.config else {}, base=base,
                            model=arguments.model, dataset=arguments.dataset, task=arguments.task,
                            device=arguments.device, epochs=arguments.epochs, training=train)
    if base is not None:
        check_model_config(base, config)
    destination = arguments.save if train else arguments.results
    if destination.is_dir():
        raise ValueError("--save/--results must name a file, not an existing directory")
    directory = arguments.logging or destination.parent / (destination.stem + ".logs")
    if directory.is_file():
        raise ValueError("--logging must name a directory")
    inputs = [p.resolve() for p in [arguments.config, arguments.resume] if p is not None]
    if not str(config["dataset"]["path"]).startswith("plugin:"):
        inputs.append(Path(config["dataset"]["path"]).resolve())
    forbidden = [p for p in inputs if not (train and arguments.resume and p == arguments.resume.resolve())]
    if destination.resolve() in forbidden or any((directory / name).resolve() in inputs for name in
                                               ["report.json", "config.resolved.json", "run.log", "events.jsonl"]):
        raise ValueError("Output paths would overwrite an input file")
    return config, directory, saved


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in {"train", "infer"}:
        _legacy_main(argv)
        return
    parser = _flag_parser()
    arguments = parser.parse_args(argv)
    try:
        config, directory, saved = _prepare(arguments)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    from universal_gnn.engine.runtime import RunLog

    log = RunLog(directory)
    (directory / "config.resolved.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    log("started", mode=arguments.mode, config=config,
        resume=str(arguments.resume) if arguments.resume else None)
    if arguments.mode == "train" and saved is not None and "training_state" not in saved:
        message = "Checkpoint has no optimizer state; starting a weights-only warm start"
        log("warm_start", message=message)
        print(message, file=sys.stderr)
    try:
        if arguments.mode == "train":
            from universal_gnn.engine.training import run_training

            report = run_training(config, directory, resume=arguments.resume, checkpoint_path=arguments.save,
                                  event_callback=log)
            summary = {"passed": report["passed"], "structures": len(report["structures"]),
                       "completed_epochs": report["completed_epochs"], "checkpoint": str(arguments.save),
                       "logging": str(directory)}
        else:
            from universal_gnn.engine.inference import run_inference

            result = run_inference(arguments.resume, config["dataset"]["path"], arguments.results,
                                   device=config.get("device", "cpu"), limit=arguments.limit,
                                   config_override=config)
            summary = {"structures": len(result["structures"]), "results": str(arguments.results),
                       "logging": str(directory)}
        log("completed", **summary)
        print(json.dumps(summary))
    except Exception as error:
        log("failed", error=repr(error))
        raise


if __name__ == "__main__":
    main()
