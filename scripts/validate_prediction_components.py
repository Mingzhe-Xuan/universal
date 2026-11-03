"""Real original-provider prediction component acceptance; execute only through Slurm."""

import argparse
import copy
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import traceback

import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.data.formats import save_structures
from universal_gnn.data.geometry import strain_batch
from universal_gnn.engine.batching import model_dtype
from universal_gnn.engine.inference import run_inference
from universal_gnn.engine.optimization import component_audit, components
from universal_gnn.engine.training import build_model, dataset, load_checkpoint, run_training
from validate_official import independent_reference


def base_config(model, entry):
    from universal_gnn.backbones.official.profiles import PROFILES

    backbone = {"name": model, "implementation": "official", "source": PROFILES[model]["source"]}
    if model == "mace":
        backbone["checkpoint"] = "models/official/mace/small.model"
    else:
        backbone.update(checkpoint="models/official/cgcnn/band-gap.pth.tar",
                        atom_init="models/official/cgcnn/atom_init.json")
    task = {k: v for k, v in entry["task"].items() if k not in {"route", "adapter_version"}}
    data = {k: v for k, v in entry["dataset"].items() if k != "sha256"}
    expected = entry["dataset"].get("sha256")
    if expected and hashlib.sha256(Path(data["path"]).read_bytes()).hexdigest() != expected:
        raise ValueError("Acceptance dataset source hash differs")
    return {"schema_version": 1, "seed": 123, "backbone": backbone, "task": task, "dataset": data,
            "structures": "all", "epochs": 4, "batch_size": 5, "dtype": "float32", "device": "cpu",
            "checkpoint_every": 1, "learning_rate": 1e-4,
            "prediction": {"version": 1, "readout": {"name": "linear", "pooling": "mean"}},
            "optimization": {"train_backbone": True, "train_readout": True}}


def state(module):
    return {key: value.detach().cpu().clone() for key, value in module.state_dict().items()}


def delta(before, module):
    return math.sqrt(sum(float((value.detach().cpu().double() - before[key].double()).square().sum())
                         for key, value in module.state_dict().items()))


def train_case(config, output):
    torch.manual_seed(config["seed"])
    initial = build_model(config).to(dtype=model_dtype(config))
    before = {name: state(module) for name, module in components(initial).items()}
    native_width = getattr(initial, "energy_model", initial).native_spec.feature_dim
    report = run_training(config, output)
    trained = load_checkpoint(output / "checkpoint.pt")
    differences = {name: delta(before[name], module) for name, module in components(trained).items()}
    frozen = not config["optimization"]["train_backbone"]
    assert report["selected_structures"] == 10 and report["checkpoint_reload"]
    assert report["final_loss"] < report["segment_initial_loss"]
    assert differences["readout"] > 0
    assert (differences["backbone"] == 0) if frozen else (differences["backbone"] > 0)
    assert (max(report["backbone_gradient_norms"]) == 0) if frozen else (max(report["backbone_gradient_norms"]) > 0)
    assert all(math.isfinite(x) and x > 0 for x in report["gradient_norms"])
    assert "adapter" not in components(trained)
    saved = torch.load(output / "checkpoint.pt", map_location="cpu", weights_only=True)
    assert saved["components"]["version"] == 1 and saved["official_backbone"]
    root = getattr(trained, "energy_model", trained)
    if config["prediction"]["readout"]["name"] != "response":
        assert root.readout.core.network[0].in_features == native_width
    validation = {"passed": True, "native_feature_dim": native_width, "component_delta_norms": differences,
                  "all_frozen_backbone_state_exact": frozen, "config": saved["config"],
                  "structures": report["structures"], "initial_loss": report["segment_initial_loss"],
                  "final_loss": report["final_loss"], "gradient_norms": report["gradient_norms"],
                  "backbone_gradient_norms": report["backbone_gradient_norms"],
                  "components": component_audit(trained), "official_load": trained.backbone.load_report,
                  "checkpoint_components": saved["components"], "execution": report["execution"]}
    return trained, validation


def force_diagnostics(model, config):
    source = dataset(config)
    original = source[0]
    positions = original.positions.clone(); positions[0, 0] += .013
    probe = StructureBatch.from_structures([replace(original, positions=positions)])
    model.train()
    values = model(probe, create_graph=True)
    values["forces"].square().sum().backward()
    assert all(p.grad is None for p in model.backbone.parameters())
    gradients = [p.grad for p in model.energy_model.readout.parameters() if p.grad is not None]
    assert gradients and all(bool(torch.isfinite(g).all()) for g in gradients)
    head_norm = math.sqrt(sum(float(g.square().sum()) for g in gradients))
    assert head_norm > 0
    step = .002
    change = torch.zeros_like(probe.positions); change[0, 0] = step
    numeric_force = -(model.energy_model(probe.with_geometry(probe.positions + change, probe.cell))[0] -
                      model.energy_model(probe.with_geometry(probe.positions - change, probe.cell))[0]) / (2 * step)
    strain = torch.zeros_like(probe.cell); strain[0, 0, 0] = step
    numeric_stress = (model.energy_model(strain_batch(probe, strain))[0] -
                      model.energy_model(strain_batch(probe, -strain))[0]) / (2 * step)
    numeric_stress = numeric_stress / torch.linalg.det(probe.cell[0]).abs() * 160.21766208
    torch.testing.assert_close(values["forces"][0, 0], numeric_force.squeeze(), rtol=.02, atol=.002)
    torch.testing.assert_close(values["stress"][0, 0, 0], numeric_stress.squeeze(), rtol=.02, atol=.002)
    torch.testing.assert_close(values["forces"].sum(0), torch.zeros(3), rtol=0, atol=2e-5)
    return {"mixed_head_gradient_norm": head_norm, "force_finite_difference_abs_error":
            float((values["forces"][0, 0] - numeric_force.squeeze()).abs().detach()),
            "stress_finite_difference_abs_error":
            float((values["stress"][0, 0, 0] - numeric_stress.squeeze()).abs().detach()),
            "step": step, "rtol": .02, "atol": .002, "dtype": "float32"}


def validate(args):
    manifest = json.loads(Path("data/acceptance/manifest.json").read_text())["tasks"]
    output = args.output; output.mkdir(parents=True, exist_ok=True)
    base = base_config(args.model, manifest["bandgap"])
    torch.manual_seed(base["seed"])
    original = build_model(base).float().eval()
    parity = independent_reference(original.backbone, dataset(base), base)
    cases = {}
    for name in ("linear", "graph_mlp"):
        for frozen in (False, True):
            config = copy.deepcopy(base)
            head = config["prediction"]["readout"]; head["name"] = name
            if name == "graph_mlp": head.update(hidden_features=[32, 16], activation="silu")
            config["optimization"]["train_backbone"] = not frozen
            config["learning_rate"] = .001 if frozen else .0001
            key = name + ("-frozen" if frozen else "-full")
            _, cases[key] = train_case(config, output / key)
    if args.model == "cgcnn":
        config = base_config(args.model, manifest["phonon_dos"])
        config["prediction"]["readout"].update(name="graph_mlp", hidden_features=[32])
        config["optimization"]["train_backbone"] = False
        config["learning_rate"] = .001
        _, cases["spectrum-200"] = train_case(config, output / "spectrum-200")
    else:
        config = base_config(args.model, manifest["dielectric_dfpt"])
        config["prediction"]["readout"].update(name="response", feature_processing={
            "name": "equivariant", "profile": "small_response", "basis_version": 2})
        config["optimization"]["train_backbone"] = False
        config["learning_rate"] = .001
        model, cases["dielectric-response"] = train_case(config, output / "dielectric-response")
        from universal_gnn.contracts.e3nn_compat import load_o3

        b = StructureBatch.from_structures([dataset(config)[0]])
        rotation = load_o3().rand_matrix(dtype=b.positions.dtype)
        value = model(b, create_graph=True)
        rotated = model(b.with_geometry(b.positions @ rotation.T, b.cell @ rotation.T))
        expected = torch.einsum("ia,bac,jc->bij", rotation, value, rotation)
        torch.testing.assert_close(rotated, expected, rtol=2e-4, atol=2e-5)
        value.square().sum().backward()
        assert any(p.grad is not None and p.grad.norm() > 0 for p in model.readout.parameters())
        cases["dielectric-response"]["rotation_max_error"] = float((rotated - expected).abs().max().detach())
        config = base_config(args.model, manifest["forcefield"])
        config["task"]["supervised_outputs"] = ["forces"]
        only_forces = [replace(s, targets={"forces": s.targets["forces"]}) for s in dataset(config)]
        source_path = output / "real-force-only.json"
        save_structures(source_path, only_forces)
        config["dataset"] = {"path": str(source_path)}
        config["prediction"]["readout"].update(name="node_mlp", pooling="sum", hidden_features=[32], activation="silu")
        config["optimization"]["train_backbone"] = False
        config["learning_rate"] = .001
        model, cases["force-only-frozen"] = train_case(config, output / "force-only-frozen")
        cases["force-only-frozen"]["derivatives"] = force_diagnostics(model, config)
        run_training({**config, "epochs": 1}, output / "force-prefix")
        report = run_training(config, output / "force-resumed", resume=output / "force-prefix/checkpoint.pt")
        resumed = load_checkpoint(output / "force-resumed/checkpoint.pt")
        for key, value in model.state_dict().items():
            torch.testing.assert_close(value, resumed.state_dict()[key], rtol=1e-5, atol=1e-6)
        assert report["resume"]["kind"] == "full"
        override = copy.deepcopy(report["config"])
        override["optimization"] = {"train_backbone": False, "train_readout": False}
        inferred = run_inference(output / "force-resumed/checkpoint.pt", source_path, output / "forces.jsonl",
                                 config_override=override)
        assert inferred["structure_count"] == 10
        cases["force-only-frozen"]["full_resume_and_all_frozen_inference"] = True
    validation = {"passed": True, "model": args.model, "slurm_job_id": os.environ["SLURM_JOB_ID"],
                  "independent_native_reference": parity, "cases": cases,
                  "interpretation": "ten-structure execution acceptance; no held-out accuracy claim"}
    (output / "validation.json").write_text(json.dumps(validation, indent=2))
    print(json.dumps({"model": args.model, "cases": len(cases), "passed": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["cgcnn", "mace"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise SystemExit("Submit this acceptance harness through Slurm")
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        validate(args)
    except Exception as error:
        (args.output / "failure.json").write_text(json.dumps({"error": repr(error), "traceback": traceback.format_exc()}, indent=2))
        raise
