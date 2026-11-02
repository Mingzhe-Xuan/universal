"""Diagnose upstream force repeatability and JIT warmup; execute only through Slurm."""

import copy
import json
from pathlib import Path

import torch

from universal_gnn.backbones.official.reference import ase_atoms
from universal_gnn.contracts import StructureBatch
from universal_gnn.engine.configuration import load_config
from universal_gnn.engine.training import build_model, dataset


def main():
    from nequip.ase import NequIPCalculator
    from nequip.data.transforms import ChemicalSpeciesToAtomTypeMapper, NeighborListTransform

    config = load_config("configs/bandgap.yaml")
    config.update(structures=10, dtype="float32")
    config["backbone"] = {"name": "nequip", "checkpoint": "models/official/nequip/NequIP-OAM-S-0.2.nequip.zip"}
    backbone = build_model(config).float().eval().backbone
    original = copy.deepcopy(backbone.model).eval()
    for name, value in backbone.model.state_dict().items():
        torch.testing.assert_close(original.state_dict()[name], value, rtol=0, atol=0)
    calculator = NequIPCalculator(model=original, device="cpu", transforms=[
        ChemicalSpeciesToAtomTypeMapper(original.type_names), NeighborListTransform(backbone.cutoff)])
    records = []
    for optimized in (True, False):
        with torch.jit.optimized_execution(optimized):
            for structure in dataset(config):
                forces, native_forces = [], []
                for repeat in range(3):
                    calculator.reset()
                    atoms = ase_atoms(structure)
                    atoms.calc = calculator
                    forces.append(torch.as_tensor(atoms.get_forces()).clone())
                    prediction, _ = backbone.native_forward(StructureBatch.from_structures([structure]))
                    native_forces.append(prediction["forces"].detach().clone())
                record = {"id": structure.identifier, "optimized": optimized,
                          "reference_repeat_error": float((forces[-1] - forces[0]).abs().max()),
                          "native_repeat_error": float((native_forces[-1] - native_forces[0]).abs().max()),
                          "parity_errors": [float((a-b).abs().max()) for a,b in zip(forces, native_forces)]}
                records.append(record)
                print(json.dumps(record), flush=True)
    Path("runs/nequip-parity-diagnostic.json").write_text(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
