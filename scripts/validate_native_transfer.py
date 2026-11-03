"""Real-artifact head-mode transfer, streamed inference and old checkpoint replay."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

import torch

from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.engine.component_views import native_component_views
from universal_gnn.engine.inference import run_inference
from universal_gnn.engine.training import build_model, load_checkpoint
from universal_gnn.engine.warm_start import initialize_components
from validate_native_heads import configuration


def native_parts(model):
    b = model.backbone
    return native_component_views(b, b.native_task_contract().head_paths)


def snapshot(view):
    return {k: v.detach().clone() for k, v in view.state_dict().items()}


def same(expected, actual):
    assert expected.keys() == actual.keys()
    for key in expected: torch.testing.assert_close(expected[key], actual[key], rtol=0, atol=0)


def save(model, config, path):
    torch.save({"format_version": 2, "config": config, "state_dict": model.state_dict(),
                "official_backbone": model.backbone.official_artifact}, path)


def transfer_summary(report):
    return {"optimizer_rebuilt": report["optimizer_rebuilt"],
            "native_head_state_excluded_from_backbone": report["native_head_state_excluded_from_backbone"],
            "loaded": {name: {"parameters": v["parameters"], "state_key_count": len(v["keys"]),
                               "state_keys_sha256": hashlib.sha256(json.dumps(v["keys"]).encode()).hexdigest()}
                       for name, v in report["loaded"].items()}}


def validate(args):
    load_o3()
    native_config = configuration(args.model)
    source = Path(f"runs/native-heads/{args.model}/resume/checkpoint.pt")
    if source.exists():
        native = load_checkpoint(source)
        native_config = torch.load(source, map_location="cpu", weights_only=True)["config"]
    else:
        assert args.model == "equiformer"
        native = build_model(native_config).float().eval()
        source = args.output / "native.pt"
        save(native, native_config, source)
    reset_config = copy.deepcopy(native_config)
    reset_config.pop("resolved_components", None)
    reset_config["prediction"] = {"version": 1, "head_mode": "reset", "readout": {
        "name": "node_mlp" if native_config["task"]["kind"] == "forcefield" else "graph_mlp",
        "pooling": "sum" if native_config["task"]["kind"] == "forcefield" or args.model == "equiformer" else "mean",
        "hidden_features": [8]}}
    reset = build_model(reset_config).float().eval()
    original_head = snapshot(native_parts(reset)["readout"])
    new_head = snapshot(reset.energy_model.readout if hasattr(reset, "energy_model") else reset.readout)
    forward = initialize_components(reset, source, ["backbone"])
    same(snapshot(native_parts(native)["backbone"]), native_parts(reset)["backbone"].state_dict())
    same(original_head, native_parts(reset)["readout"].state_dict())
    same(new_head, (reset.energy_model.readout if hasattr(reset, "energy_model") else reset.readout).state_dict())
    # Make the reset checkpoint's unused original head observably different.
    # These are transfer probes, never labeled training data.
    with torch.no_grad():
        for p in native_parts(reset)["readout"].parameters(): p.add_(.5)
        for p in native_parts(reset)["backbone"].parameters(): p.add_(1e-4)
    reset_path = args.output / "reset.pt"; save(reset, reset_config, reset_path)
    target = build_model(native_config).float().eval()
    target_head = snapshot(native_parts(target)["readout"])
    backward = initialize_components(target, reset_path, ["backbone"])
    same(snapshot(native_parts(reset)["backbone"]), native_parts(target)["backbone"].state_dict())
    same(target_head, native_parts(target)["readout"].state_dict())
    override = copy.deepcopy(native_config)
    override["optimization"].update(train_backbone=False, train_readout=False)
    inferred = run_inference(source, native_config["dataset"]["path"], args.output / "predictions.jsonl",
                             config_override=override)
    assert inferred["structure_count"] == 10
    assert all(v["trainable_parameters"] == 0 for v in inferred["components"].values())
    previous = None
    old = {"cgcnn": "runs/prediction-cgcnn-real2-771/linear-frozen",
           "mace": "runs/mace-real-force-only-764/continuous"}.get(args.model)
    if old:
        old = Path(old); saved = torch.load(old / "checkpoint.pt", map_location="cpu", weights_only=True)
        assert "head_mode" not in saved["config"].get("prediction", {})
        actual = run_inference(old / "checkpoint.pt", saved["config"]["dataset"]["path"], args.output / "previous.json")
        expected = json.loads((old / "report.json").read_text())["predictions"]
        errors = {}
        for key in expected:
            a, b = torch.tensor(actual["predictions"][key]), torch.tensor(expected[key])
            torch.testing.assert_close(a, b, rtol=1e-5, atol=1e-6)
            errors[key] = float((a - b).abs().max())
        previous = {"source": str(old), "max_errors": errors}
    result = {"passed": True, "model": args.model, "slurm_job_id": os.environ["SLURM_JOB_ID"],
              "native_to_reset_body_exact": True, "reset_to_native_body_exact": True,
              "target_heads_unchanged": True, "native_frozen_streamed_inference": 10,
              "forward_transfer": transfer_summary(forward), "backward_transfer": transfer_summary(backward),
              "previous_checkpoint": previous}
    (args.output / "validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"model": args.model, "passed": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"): raise SystemExit("Submit through Slurm")
    args.output.mkdir(parents=True, exist_ok=True)
    validate(args)
