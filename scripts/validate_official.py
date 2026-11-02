"""Published checkpoint parity and ten-real-structure fine-tuning; run through Slurm."""

import argparse
import copy
import json
import math
import os
from pathlib import Path
import traceback

import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.engine.batching import model_dtype
from universal_gnn.engine.configuration import load_config
from universal_gnn.engine.training import build_model, dataset, load_checkpoint, run_training


def independent_reference(backbone, structures, config):
    if config["backbone"]["name"] != "mace":
        raise NotImplementedError("Independent reference validation for this provider is still being implemented")
    from ase import Atoms
    from mace.calculators import MACECalculator

    calculator = MACECalculator(models=[copy.deepcopy(backbone.model)], device="cpu", default_dtype=config["dtype"])
    errors, energy_errors = [], []
    for structure in structures:
        atoms = Atoms(numbers=structure.numbers.numpy(), positions=structure.positions.numpy(),
                      cell=structure.cell.numpy(), pbc=structure.pbc.numpy())
        reference = torch.as_tensor(calculator.get_descriptors(atoms, invariants_only=False))
        batch = StructureBatch.from_structures([structure]).to("cpu", model_dtype(config))
        features = backbone.encode(batch).nodes.detach().cpu()
        torch.testing.assert_close(features, reference, rtol=2e-5, atol=2e-6)
        errors.append(float((features - reference).abs().max()))
        atoms.calc = calculator
        reference_energy = float(atoms.get_potential_energy())
        native_energy = float(backbone.native_forward(batch)["energy"].detach().sum())
        if not math.isclose(reference_energy, native_energy, rel_tol=2e-5, abs_tol=2e-5):
            raise AssertionError((reference_energy, native_energy))
        energy_errors.append(abs(reference_energy - native_energy))
    return {"reference": "official MACECalculator.get_descriptors and ASE potential energy",
            "structures": len(structures), "max_feature_error": max(errors), "max_energy_error": max(energy_errors)}


def validate(args):
    config = load_config(args.config)
    config.update(structures=10, epochs=args.epochs, batch_size=args.batch_size, dtype=args.dtype,
                  learning_rate=args.learning_rate, device="cpu", checkpoint_every=1)
    config["backbone"] = {"name": args.model, "implementation": "official", "checkpoint": str(args.checkpoint),
                          "source": args.source}
    if args.atom_init:
        config["backbone"]["atom_init"] = str(args.atom_init)
    torch.manual_seed(config.get("seed", 123))
    model = build_model(config).to(dtype=model_dtype(config)).eval()
    structures = dataset(config)
    original_parameters = {name: value.detach().clone() for name, value in model.backbone.model.named_parameters()}
    parity = independent_reference(model.backbone, structures, config)
    # A perturbed copy is only a derivative diagnostic; training keeps all ten original records.
    from dataclasses import replace

    probe = StructureBatch.from_structures([structures[0]]).to("cpu", model_dtype(config))
    positions = probe.positions.detach().clone()
    positions[0, 0] += .013
    positions.requires_grad_(True)
    probe = replace(probe, positions=positions)
    objective = model.backbone.encode(probe).nodes.square().mean()
    first = torch.autograd.grad(objective, positions, create_graph=True)[0]
    second = torch.autograd.grad(first.square().sum(), positions)[0]
    if not bool(torch.isfinite(first).all() and torch.isfinite(second).all()):
        raise AssertionError("Official feature gradients are not finite")
    del objective, first, second, model
    report = run_training(config, args.output)
    trained = load_checkpoint(args.output / "checkpoint.pt")
    difference = math.sqrt(sum(float((parameter.detach() - original_parameters[name]).square().sum())
                               for name, parameter in trained.backbone.model.named_parameters()))
    if report["selected_structures"] != 10 or difference <= 0 or max(report["backbone_gradient_norms"]) <= 0:
        raise AssertionError("Ten-structure fine-tuning did not update the official backbone")
    if report["final_loss"] >= report["segment_initial_loss"]:
        raise AssertionError("Ten-structure execution acceptance requires decreased training loss")
    saved = torch.load(args.output / "checkpoint.pt", map_location="cpu", weights_only=True)
    saved["config"]["backbone"]["checkpoint"] = str(args.output / "intentionally-absent-source")
    if "atom_init" in saved["config"]["backbone"]:
        saved["config"]["backbone"]["atom_init"] = str(args.output / "intentionally-absent-atom-init")
    isolated_path = args.output / "self-contained.pt"
    torch.save(saved, isolated_path)
    restored = load_checkpoint(isolated_path)
    for name, value in trained.state_dict().items():
        torch.testing.assert_close(value, restored.state_dict()[name], rtol=0, atol=0)
    validation = {"model": args.model, "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
                  "official_load": trained.backbone.load_report, "independent_parity": parity,
                  "ten_real_structures": report["structures"], "backbone_parameter_delta_norm": difference,
                  "initial_loss": report["segment_initial_loss"], "final_loss": report["final_loss"],
                  "first_second_input_derivatives_finite": True, "self_contained_reload": True,
                  "passed": True, "interpretation": "execution/fine-tuning acceptance, not held-out accuracy"}
    (args.output / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    print(json.dumps({key: validation[key] for key in ("model", "slurm_job_id", "initial_loss", "final_loss", "passed")}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/bandgap.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--atom-init", type=Path)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--dtype", choices=["float32", "float64"], default="float32")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        validate(args)
    except Exception as error:
        (args.output / "failure.json").write_text(json.dumps({"error": repr(error), "traceback": traceback.format_exc(),
                    "slurm_job_id": os.environ.get("SLURM_JOB_ID")}, indent=2), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
