"""Original ALIGNN 2.0 pure-Torch model, config, graph and line-graph builders."""

from importlib.metadata import version
import io
import json
from pathlib import Path
import zipfile

import torch

from .base import OfficialBackbone, artifact_files, capture_features, default_dtype


class OfficialALIGNN(OfficialBackbone):
    def __init__(self, checkpoint=None, *, context_dim=0, source=None, _artifact=None):
        if _artifact is not None:
            artifact = artifact_files("alignn", {}, artifact=_artifact)
        elif checkpoint is not None and Path(checkpoint).is_dir():
            artifact = artifact_files("alignn", {name: Path(checkpoint) / name for name in ("config.json", "best_model.pt")},
                                      source=source)
        else:
            artifact = artifact_files("alignn", {"archive": checkpoint}, source=source)
        if "archive" in artifact["files"]:
            with zipfile.ZipFile(io.BytesIO(artifact["files"]["archive"])) as archive:
                def read(name):
                    matches = [member for member in archive.namelist() if member == name or member.endswith("/" + name)]
                    if len(matches) != 1:
                        raise ValueError(f"Expected one {name} in ALIGNN archive")
                    return archive.read(matches[0])

                configuration = json.loads(read("config.json"))
                weights = read("best_model.pt")
        else:
            configuration = json.loads(artifact["files"]["config.json"])
            weights = artifact["files"]["best_model.pt"]
        settings = configuration["model"]
        if settings["name"] == "alignn_atomwise_pure":
            from alignn.models.alignn_atomwise_pure import ALIGNNAtomWisePure, ALIGNNAtomWisePureConfig

            model = ALIGNNAtomWisePure(ALIGNNAtomWisePureConfig(**settings))
        elif settings["name"] == "alignn_atomwise_pure_smooth":
            from alignn.models.alignn_atomwise_pure_smooth import ALIGNNAtomWisePureSmooth, ALIGNNAtomWisePureSmoothConfig

            model = ALIGNNAtomWisePureSmooth(ALIGNNAtomWisePureSmoothConfig(**settings))
        else:
            raise ValueError("Official ALIGNN provider requires the published pure-Torch model configuration")
        state = torch.load(io.BytesIO(weights), map_location="cpu", weights_only=True)
        state = state.get("model", state.get("state_dict", state))
        if state and all(key.startswith("module.") for key in state):
            state = {key.removeprefix("module."): value for key, value in state.items()}
        model.load_state_dict(state, strict=True)
        if configuration.get("neighbor_strategy", "pure_torch") != "pure_torch":
            raise ValueError("This ALIGNN provider preserves the official pure_torch graph strategy")
        super().__init__(model, f"{settings['hidden_features']}x0e", "invariant", configuration["cutoff"], artifact,
                         context_dim=context_dim, version=version("alignn"))
        self.configuration = configuration
        self.gradient_capabilities = {"positions": True, "strain": True, "mixed": True}
        self.unused_parameter_prefixes = ("model.fc", "model.fc_atomwise", "model.fc_additional_output")
        self.feature_path = (f"gcn_layers.{len(model.gcn_layers) - 1}" if len(model.gcn_layers) else
                             f"alignn_layers.{len(model.alignn_layers) - 1}" if len(model.alignn_layers) else "atom_embedding")

    def native_input(self, batch):
        from ase.data import chemical_symbols
        from jarvis.core.atoms import Atoms
        from alignn.torch_graph_builder import build_pure_torch_graph, batch_torch_graph_pairs

        if not bool(batch.pbc.all()):
            raise ValueError("This official ALIGNN crystal graph requires 3D periodic structures")
        pairs = []
        with default_dtype(batch.positions.dtype):
            for i in range(batch.num_graphs):
                start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
                atoms = Atoms(lattice_mat=batch.cell[i].detach().cpu().numpy(),
                              coords=batch.positions[start:end].detach().cpu().numpy(), cartesian=True,
                              elements=[chemical_symbols[int(z)] for z in batch.numbers[start:end]])
                pairs.append(build_pure_torch_graph(atoms=atoms, two_body_cutoff=self.cutoff,
                    three_body_cutoff=self.configuration.get("three_body_cutoff", 3.5),
                    max_neighbors=self.configuration.get("max_neighbors", 12),
                    atom_features=self.configuration.get("atom_features", "cgcnn"),
                    use_lattice_prop=self.configuration.get("use_lattice_prop", False),
                    positions=batch.positions[start:end], lattice=batch.cell[i], device=batch.positions.device))
        graph, line_graph = batch_torch_graph_pairs(pairs)
        return graph, line_graph, batch.cell

    def native_forward(self, batch):
        captured = []
        target = self.model.get_submodule(self.feature_path)
        handle = target.register_forward_hook(lambda module, inputs, output: captured.append(
            output if self.feature_path == "atom_embedding" else output[0]))
        try:
            prediction = self.model(self.native_input(batch))
        finally:
            handle.remove()
        return prediction, captured[0]

    def encode(self, batch, context=None):
        nodes = capture_features(lambda: self.model(self.native_input(batch)), self.model.get_submodule(self.feature_path),
                                 lambda value: value if self.feature_path == "atom_embedding" else value[0])
        return self.output(nodes, batch, context)
