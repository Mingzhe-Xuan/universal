"""Original eager NequIP package, original type mapper and neighbor transforms."""

from importlib.metadata import version
from pathlib import Path
import tempfile

import torch

from .base import OfficialBackbone, ReferenceValue, artifact_files, capture_features, default_dtype, select_packaged_model


class OfficialNequIP(OfficialBackbone):
    def __init__(self, checkpoint=None, *, feature_module="per_atom_energy_readout", model_key=None,
                 context_dim=0, source=None, _artifact=None):
        from nequip.model import ModelFromPackage

        artifact = artifact_files("nequip", {"package": checkpoint}, artifact=_artifact, source=source)
        temporary = tempfile.TemporaryDirectory(prefix="ugnn-nequip-")
        path = Path(temporary.name) / "model.nequip.zip"
        path.write_bytes(artifact["files"]["package"])
        model, selected = select_packaged_model(ModelFromPackage(str(path), compile_mode="eager"), model_key)
        targets = [(name, module) for name, module in model.named_modules()
                   if name == feature_module or name.endswith("." + feature_module)]
        if len(targets) != 1:
            temporary.cleanup()
            raise ValueError(f"Expected one original NequIP feature module {feature_module!r}, found {len(targets)}")
        metadata = model.metadata
        if metadata.get("per_edge_type_cutoff") is not None:
            temporary.cleanup()
            raise ValueError("This provider currently requires the published uniform-cutoff NequIP package")
        feature_path, target = targets[0]
        super().__init__(model, str(target.irreps_in["node_features"]), "equivariant", metadata["r_max"],
                         artifact, context_dim=context_dim, version=version("nequip"))
        self.feature_path, self._temporary = feature_path, temporary
        self.gradient_capabilities = {"positions": True, "strain": True, "mixed": True}
        self.unused_parameter_prefixes = ("model." + feature_path,)
        self.type_names = list(model.type_names)
        self.load_report["selected_model"] = selected

    def native_input(self, batch):
        from ase import Atoms
        from nequip.data import AtomicDataDict, from_ase
        from nequip.data.transforms import ChemicalSpeciesToAtomTypeMapper, NeighborListTransform

        mapper = ChemicalSpeciesToAtomTypeMapper(chemical_symbols=self.type_names)
        neighbors = NeighborListTransform(r_max=self.cutoff)
        values = []
        with default_dtype(batch.positions.dtype):
            for i in range(batch.num_graphs):
                start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
                atoms = Atoms(numbers=batch.numbers[start:end].cpu().numpy(),
                              positions=batch.positions[start:end].detach().cpu().numpy(),
                              cell=batch.cell[i].detach().cpu().numpy(), pbc=batch.pbc[i].cpu().numpy())
                data = from_ase(atoms)
                data["pos"] = ReferenceValue.apply(data["pos"], batch.positions[start:end].to("cpu"))
                data["cell"] = ReferenceValue.apply(data["cell"], batch.cell[i].to("cpu").reshape_as(data["cell"]))
                values.append(neighbors(mapper(data)))
        data = values[0] if len(values) == 1 else AtomicDataDict.batched_from_list(values)
        return AtomicDataDict.to_(data, device=batch.positions.device)

    def native_forward(self, batch):
        captured = []
        target = self.model.get_submodule(self.feature_path)
        handle = target.register_forward_pre_hook(
            lambda module, inputs: captured.append(inputs[0]["node_features"]))
        try:
            prediction = self.model(self.native_input(batch))
        finally:
            handle.remove()
        return prediction, captured[0]

    def encode(self, batch, context=None):
        nodes = capture_features(lambda: self.model(self.native_input(batch)), self.model.get_submodule(self.feature_path),
                                 lambda inputs: inputs[0]["node_features"], before=True)
        return self.output(nodes, batch, context)
