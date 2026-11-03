"""Original-head acceptance on real structures; execute only through Slurm."""

import argparse
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import traceback

import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.engine.optimization import components, FrozenStateGuard, make_optimizer
from universal_gnn.engine.training import build_model, dataset, load_checkpoint, run_training


def configuration(name):
    force = name in {"mace", "nequip"}
    prop = "formation_energy" if name == "megnet" else "oc20_relaxed_energy" if name == "equiformer" else "bandgap"
    cohort = "forcefield" if force else "formation_energy" if name == "megnet" else "bandgap"
    binding = {"formation_energy": "formation_energy_peratom", "bandgap": "optb88vdw_bandgap"}
    return {"schema_version": 1, "seed": 123, "structures": 10, "batch_size": 5,
            "dtype": "float32", "device": "cpu", "epochs": 2, "learning_rate": 1e-5,
            "checkpoint_every": 1, "backbone": {"name": name, "implementation": "official"},
            "dataset": {"path": f"data/acceptance/{cohort}-10.json", "bindings":
                {"forces": {"key": "forces", "unit": "eV/angstrom"}} if force else
                {prop: {"key": binding[prop]}} if prop in binding else {}},
            "task": {"kind": "forcefield", "supervised_outputs": ["forces"]} if force else
                    {"kind": "supervised", "property": prop},
            "prediction": {"version": 1, "head_mode": "native"},
            "optimization": {"train_backbone": False, "train_readout": True}}


def max_error(actual, expected, *, rtol=3e-5, atol=3e-6):
    expected = torch.as_tensor(expected, dtype=actual.dtype).reshape(actual.shape)
    torch.testing.assert_close(actual.detach().cpu(), expected.detach().cpu(), rtol=rtol, atol=atol)
    return float((actual.detach().cpu() - expected.detach().cpu()).abs().max())


def parity(model, structures, config):
    from validate_official import independent_reference

    name = config["backbone"]["name"]
    reference_config = copy.deepcopy(config)
    # Original CGCNN reference's file labels are ignored by its prediction path.
    reference = independent_reference(model.backbone, structures[:2], reference_config)
    errors = []
    for structure in structures[:2]:
        batch = StructureBatch.from_structures([structure])
        if name == "mace":
            from mace.calculators import MACECalculator
            from universal_gnn.backbones.official.reference import ase_atoms

            calc = MACECalculator(models=[copy.deepcopy(model.backbone.model)], device="cpu", default_dtype="float32")
            atoms = ase_atoms(structure); atoms.calc = calc
            actual = model(batch, create_graph=False)
            errors.append({"energy": max_error(actual["total_energy"], [atoms.get_potential_energy()]),
                           "forces": max_error(actual["forces"], atoms.get_forces()),
                           "stress": max_error(actual["stress"], atoms.get_stress(voigt=False) * 160.21766208)})
        elif name == "nequip":
            original, _ = model.backbone.native_forward(batch)
            actual = model(batch, create_graph=False)
            errors.append({"energy": max_error(actual["total_energy"], original["total_energy"]),
                           "forces": max_error(actual["forces"], original["forces"]),
                           "stress": max_error(actual["stress"], original["stress"] * 160.21766208)})
        else:
            original, _ = model.backbone.native_forward(batch)
            if name == "alignn": original = original["out"]
            if name in {"cgcnn", "equiformer"}:
                stats = model.native_contract.normalization
                original = original * stats["std"] + stats["mean"]
            errors.append({"physical_prediction": max_error(model(batch), original)})
    return {"independent_upstream": reference, "ugnn_physical_output_errors": errors}


def check_policies(config, structures):
    results = {}
    for frozen in ("backbone", "readout"):
        c = copy.deepcopy(config)
        c["optimization"] = {"train_backbone": frozen != "backbone", "train_readout": frozen != "readout",
                             "backbone_eval": True}
        m = build_model(c).float().train()
        guard = FrozenStateGuard(m); optimizer = make_optimizer(m, c)
        parts = components(m)
        snapshot = {k: v.detach().clone() for k, v in parts[frozen].state_dict().items()}
        batch = StructureBatch.from_structures(structures[:2])
        positions = batch.positions.detach().clone(); positions[0, 0] += .013
        batch = replace(batch, positions=positions.requires_grad_(True))
        if c["task"]["kind"] == "forcefield":
            objective = m(batch, create_graph=True)["forces"].square().mean()
        else:
            objective = m(batch).square().mean()
        # A gradient diagnostic, not training against fabricated labels.
        objective.backward()
        gradients = {role: sum(float(p.grad.detach().square().sum()) for p in module.parameters()
                                   if p.grad is not None) ** .5 for role, module in parts.items()}
        if gradients[frozen] != 0 or not gradients["readout" if frozen == "backbone" else "backbone"] > 0:
            raise AssertionError((frozen, gradients))
        if not all(p.grad is None or torch.isfinite(p.grad).all() for p in m.parameters()):
            raise AssertionError("Nonfinite native gradient")
        ids = [id(p) for g in optimizer.param_groups for p in g["params"]]
        assert len(ids) == len(set(ids))
        optimizer.step(); guard.verify()
        for key, value in snapshot.items():
            torch.testing.assert_close(value, parts[frozen].state_dict()[key], rtol=0, atol=0)
        results[frozen + "_frozen"] = {"gradient_norms": gradients, "frozen_state_exact": True,
                                       "optimizer_parameters_unique": True}
    return results


def validate(args):
    load_o3()
    config = configuration(args.model)
    torch.manual_seed(123)
    model = build_model(config).float().eval()
    structures = dataset(config)
    report = {"model": args.model, "slurm_job_id": os.environ["SLURM_JOB_ID"],
              "native_task": getattr(model, "energy_model", model).native_contract.to_dict(),
              "config": config, "ids": [s.identifier for s in structures]}
    report["parity"] = parity(model, structures, config)
    del model
    report["policies"] = check_policies(config, structures)
    if args.model != "equiformer":
        result = run_training(config, args.output / "train")
        restored = load_checkpoint(args.output / "train/checkpoint.pt")
        batch = StructureBatch.from_structures(structures[:2])
        before = restored(batch, create_graph=False)
        again = load_checkpoint(args.output / "train/checkpoint.pt")
        after = again(batch, create_graph=False)
        if isinstance(before, dict):
            for key in before: max_error(before[key], after[key], rtol=0, atol=0)
        else: max_error(before, after, rtol=0, atol=0)
        resumed = run_training({**config, "epochs": 3}, args.output / "resume",
                               resume=args.output / "train/checkpoint.pt")
        report["training"] = {"initial_loss": result["segment_initial_loss"], "final_loss": result["final_loss"],
                              "resume_final_loss": resumed["final_loss"], "reload_exact": True,
                              "selected_structures": result["selected_structures"]}
    else:
        report["training"] = {"skipped": "No genuine OC20 IS2RE labels in current cohort; parity/gradient diagnostics only"}
    report["passed"] = True
    (args.output / "validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"model": args.model, "passed": True}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not os.environ.get("SLURM_JOB_ID"): raise SystemExit("Submit through Slurm")
    args.output.mkdir(parents=True, exist_ok=True)
    try: validate(args)
    except Exception as error:
        (args.output / "failure.json").write_text(json.dumps({"error": repr(error), "traceback": traceback.format_exc()}, indent=2))
        raise
