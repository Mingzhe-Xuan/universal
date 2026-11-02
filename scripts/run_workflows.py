"""Ten real structures per model: calculator, dynamics, Gamma spectra, abTEM STEM."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import traceback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--checkpoints", type=Path, default=Path("runs/dfpt-tasks"))
    parser.add_argument("--output", type=Path, default=Path("runs/workflows"))
    parser.add_argument("--skip-microscopy", action="store_true")
    args = parser.parse_args()
    if args.model == "mace":
        wanted = Path(os.environ.get("UGNN_MACE_PYTHON", "/home/xmz/.venvs/universal-mace/bin/python"))
        if Path(sys.executable).absolute() != wanted.absolute():
            os.execv(str(wanted), [str(wanted), *sys.argv])
    import numpy as np
    import torch
    from universal_gnn.contracts import StructureBatch
    from universal_gnn.engine.training import dataset, execution_record, load_checkpoint
    from universal_gnn.workflows.calculator import molecular_dynamics, relax
    from universal_gnn.workflows.spectroscopy import (broaden, dielectric_raman, mode_responses,
                                                    neutron_weights, normal_modes)

    destination = args.output / args.model
    destination.mkdir(parents=True, exist_ok=True)
    models = {task: load_checkpoint(args.checkpoints / f"{args.model}--{task}" / "checkpoint.pt")
              for task in ["forcefield", "born_charge", "dielectric_dfpt"]}
    saved = torch.load(args.checkpoints / f"{args.model}--forcefield" / "checkpoint.pt", weights_only=True)
    structures = dataset(saved["config"], 10)
    report = {"model": args.model, "execution": execution_record(models["forcefield"]),
              "checkpoint_root": str(args.checkpoints), "scope": "ten-structure execution; not physical accuracy",
              "phonons": "Gamma, primitive supplied cell; no BZ integration or acoustic sum-rule projection",
              "versions": {name: importlib.metadata.version(name) for name in ["ase", "periodictable"]},
              "structures": [], "passed": False}
    try:
        for index, structure in enumerate(structures):
            _, relaxation = relax(models["forcefield"], structure, steps=3)
            frames, md = molecular_dynamics(models["forcefield"], structure, steps=2)
            modes = normal_modes(models["forcefield"], structure)
            batch = StructureBatch.from_structures([structure])
            born = models["born_charge"](batch, create_graph=False).detach()
            ir = mode_responses(modes, born)
            raman, tensors = dielectric_raman(models["dielectric_dfpt"], structure, modes)
            neutron = neutron_weights(modes, structure.numbers)
            grid = torch.linspace(1, 1200, 200, dtype=modes.frequencies_cm.dtype)
            spectra = {name: broaden(modes.frequencies_cm, activity, grid).cpu().tolist()
                       for name, activity in [("ir", ir), ("raman", raman), ("neutron", neutron)]}
            if not all(np.isfinite(value).all() for value in spectra.values()):
                raise FloatingPointError("Nonfinite spectra")
            record = {"id": structure.identifier, "provenance": structure.metadata,
                      "relaxation": relaxation, "md": md,
                      "frequencies_cm_signed": modes.frequencies_cm.cpu().tolist(),
                      "excluded_modes_le_1cm": int((modes.frequencies_cm <= 1).sum()),
                      "grid_cm": grid.tolist(), "lorentzian_HWHM_cm": 5., "spectra": spectra,
                      "intensity_units": "relative; Gamma neutron weighting uses barn/amu",
                      "raman_mode_tensors": tensors.cpu().tolist()}
            if not args.skip_microscopy:
                from universal_gnn.workflows.microscopy import frozen_phonon_stem

                image, settings = frozen_phonon_stem(frames[-2:], gpts=96)
                np.save(destination / f"stem-{index}.npy", image)
                record["microscopy"] = {**settings, "image": f"stem-{index}.npy",
                                         "min": float(image.min()), "max": float(image.max())}
            report["structures"].append(record)
            (destination / "report.json").write_text(json.dumps(report, indent=2))
        report["passed"] = len(report["structures"]) == 10
    except Exception as error:
        report["error"] = repr(error)
        report["traceback"] = traceback.format_exc()
        raise
    finally:
        (destination / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"model": args.model, "count": len(report["structures"]), "passed": report["passed"]}))


if __name__ == "__main__":
    main()
