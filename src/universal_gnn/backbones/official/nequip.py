"""Original eager NequIP package, original type mapper and neighbor transforms."""

from importlib.metadata import version
from pathlib import Path
import tempfile
import re

import torch

from .base import OfficialBackbone, ReferenceValue, artifact_files, capture_features, default_dtype, select_packaged_model
from universal_gnn.backbones.initialization import initialize_original, validate_initialization


def _respect_nonperiodic_axes(data, pbc):
    # Some matscipy versions return nonzero image offsets on nonperiodic axes;
    # NequIP consumes those offsets even though its positions remain unwrapped.
    shifts = data.get("edge_cell_shift")
    if shifts is not None and not bool(pbc.all()):
        data["edge_cell_shift"] = torch.where(pbc.to(device=shifts.device).reshape(1, 3),
                                               shifts, torch.zeros_like(shifts))
    return data


def packaged_constructor_layout(model):
    from universal_gnn.contracts.e3nn_compat import load_o3

    layers = []
    for path, module in model.named_modules():
        match = re.search(r"(?:^|\.)layer([0-9]+)_convnet$", path)
        if match is not None:
            layers.append((int(match[1]), path, module))
    layers.sort(key=lambda value: value[0])
    if not layers or [value[0] for value in layers] != list(range(len(layers))):
        raise ValueError("Original NequIP package lacks a unique contiguous ConvNetLayer layout")
    parent = layers[0][1].rsplit(".", 1)[0] if "." in layers[0][1] else ""
    prefix = parent + "." if parent else ""
    if any(path != prefix + f"layer{index}_convnet" for index, path, _ in layers):
        raise ValueError("Original NequIP package has ambiguous convolution parents")
    spharm = model.get_submodule(prefix + "spharm")
    embedding = model.get_submodule(prefix + "type_embed")
    irreps = load_o3().Irreps(embedding.irreps_out["node_features"])
    if any(irrep.l != 0 or irrep.p != 1 for _, irrep in irreps):
        raise ValueError("Original NequIP type embedding must contain only even scalars")
    return dict(irreps_edge_sh=str(spharm.irreps_out["edge_attrs"]),
                type_embed_num_features=irreps.dim,
                feature_irreps_hidden=[str(module.feature_irreps_hidden) for _, _, module in layers])


class OfficialNequIP(OfficialBackbone):
    def __init__(self, checkpoint=None, *, feature_module="per_atom_energy_readout", model_key=None,
                 context_dim=0, source=None, _artifact=None, initialization="pretrained", architecture=None,
                 neighbor_statistics=None):
        from nequip.model import ModelFromPackage

        validate_initialization(initialization)
        if initialization == "pretrained" and neighbor_statistics is not None:
            raise ValueError("Pretrained NequIP retains its original normalization; neighbor_statistics is scratch-only")
        files = {"package": checkpoint}
        if architecture is not None:
            files["blueprint"] = architecture
        artifact = artifact_files("nequip", files, artifact=_artifact, source=source)
        temporary = tempfile.TemporaryDirectory(prefix="ugnn-nequip-")
        path = Path(temporary.name) / "model.nequip.zip"
        path.write_bytes(artifact["files"]["package"])
        model, selected = select_packaged_model(ModelFromPackage(str(path), compile_mode="eager"), model_key)
        report = None
        if initialization == "scratch":
            import yaml
            from nequip.model import FullNequIPGNNModel
            from nequip.utils.global_state import set_global_state
            from lightning.pytorch.utilities.seed import isolate_rng
            from universal_gnn.backbones.blueprints import nequip_full_constructor_config

            if "blueprint" not in artifact["files"]:
                raise ValueError("Fresh NequIP requires its author architecture blueprint; supply backbone.architecture")
            reference = model
            layout = packaged_constructor_layout(reference)
            config, recipe_report = nequip_full_constructor_config(yaml.safe_load(artifact["files"]["blueprint"]),
                                                                   neighbor_statistics, seed=torch.initial_seed(), layout=layout)
            with default_dtype(torch.get_default_dtype()), isolate_rng(include_cuda=torch.cuda.is_initialized()):
                set_global_state()
                model = FullNequIPGNNModel(**config)
            if (list(model.type_names) != list(reference.type_names) or
                    float(model.metadata["r_max"]) != float(reference.metadata["r_max"])):
                raise ValueError("Fresh NequIP constructor changed the original type vocabulary or cutoff")
            if packaged_constructor_layout(model) != layout:
                raise ValueError("Fresh NequIP constructor changed the original irreps or embedding layout")
            report = initialize_original(model, reference.state_dict(), mode="scratch")
            report.update(recipe_report, neighbor_statistics=neighbor_statistics)
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
                         artifact, context_dim=context_dim, version=version("nequip"), initialization=initialization)
        if report is not None:
            self.validate_native_neighbor_graph(neighbor_statistics)
            self.load_report.update(report)
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
                values.append(_respect_nonperiodic_axes(neighbors(mapper(data)), batch.pbc[i]))
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
