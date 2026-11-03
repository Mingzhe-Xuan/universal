"""Validate original MACE fine-tuning on only real force labels; execute through Slurm."""

import argparse
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import traceback

import torch

from universal_gnn.data.formats import save_structures
from universal_gnn.engine.configuration import load_config
from universal_gnn.engine.inference import run_inference
from universal_gnn.engine.training import build_model, dataset, load_checkpoint, run_training


def validate(args):
    source = load_config("configs/forcefield.json")
    source["task"]["supervised_outputs"] = ["forces"]
    source["structures"] = 10
    structures = dataset(source)
    force_only = [replace(s, targets={"forces": s.targets["forces"]}) for s in structures]
    assert len(force_only) == 10 and all(set(s.targets) == {"forces"} for s in force_only)
    data_path = args.output / "real-force-labels.json"
    save_structures(data_path, force_only, metadata={"labels": ["forces"], "source": source["dataset"]["path"],
                                                  "operation": "retain original geometry and forces; omit E/S"})
    config = load_config("configs/mace_force_only.yaml")
    config.update(epochs=args.epochs, batch_size=5, checkpoint_every=1)
    config["dataset"]["path"] = str(data_path)
    torch.manual_seed(config["seed"])
    original = build_model(config).float()
    initial = {name: value.detach().clone() for name, value in original.backbone.model.named_parameters()}
    report = run_training(config, args.output / "continuous")
    run_training({**config, "epochs": 1}, args.output / "first")
    resumed = run_training(config, args.output / "resumed", resume=args.output / "first/checkpoint.pt")
    model = load_checkpoint(args.output / "continuous/checkpoint.pt")
    restored = load_checkpoint(args.output / "resumed/checkpoint.pt")
    for name, value in model.state_dict().items():
        torch.testing.assert_close(value, restored.state_dict()[name], rtol=1e-5, atol=1e-6)
    delta = math.sqrt(sum(float((value.detach() - initial[name]).square().sum())
                          for name, value in model.backbone.model.named_parameters()))
    assert report["supervised_outputs"] == ["forces"] and delta > 0
    assert report["final_loss"] < report["initial_loss"] and max(report["backbone_gradient_norms"]) > 0
    assert resumed["resume"]["kind"] == "full" and resumed["resume"]["completed_epochs_before"] == 1
    checkpoint = torch.load(args.output / "continuous/checkpoint.pt", map_location="cpu", weights_only=True)
    assert set(checkpoint["scales"]) == {"forces"} and checkpoint["official_backbone"]
    predictions = run_inference(args.output / "continuous/checkpoint.pt", str(data_path), args.output / "predictions.jsonl")
    assert predictions["structure_count"] == 10
    records = [json.loads(line) for line in (args.output / "predictions.jsonl").read_text().splitlines()]
    assert records[-1]["type"] == "completed" and len(records[1:-1]) == 10
    validation = {"passed": True, "slurm_job_id": os.environ.get("SLURM_JOB_ID"), "model": "official MACE",
                  "labels_present": ["forces"], "supervised_outputs": report["supervised_outputs"],
                  "initial_loss": report["initial_loss"], "final_loss": report["final_loss"],
                  "backbone_parameter_delta_norm": delta, "official_load": model.backbone.load_report,
                  "full_resume": True, "predicted_structures": 10, "structures": report["structures"],
                  "execution": report["execution"],
                  "interpretation": "real-force-only execution acceptance; energy offset is not calibrated"}
    (args.output / "validation.json").write_text(json.dumps(validation, indent=2))
    print(json.dumps({key: validation[key] for key in ["passed", "slurm_job_id", "initial_loss", "final_loss",
                                                     "backbone_parameter_delta_norm"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    try:
        validate(arguments)
    except Exception as error:
        (arguments.output / "failure.json").write_text(json.dumps({"error": repr(error), "traceback": traceback.format_exc()}, indent=2))
        raise
