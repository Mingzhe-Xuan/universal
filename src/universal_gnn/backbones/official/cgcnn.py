"""Original CGCNN layers and original element/Gaussian preprocessing values."""

import io
from pathlib import Path
import tempfile

import numpy as np
import torch

from .base import OfficialBackbone, ReferenceValue, artifact_files, capture_features


class OfficialCGCNN(OfficialBackbone):
    def __init__(self, checkpoint=None, *, atom_init=None, preprocessing=None,
                 context_dim=0, source=None, _artifact=None):
        from cgcnn.model import CrystalGraphConvNet
        from cgcnn.data import AtomCustomJSONInitializer, GaussianDistance

        artifact = artifact_files("cgcnn", {"checkpoint": checkpoint, "atom_init": atom_init},
                                  artifact=_artifact, source=source)
        saved = torch.load(io.BytesIO(artifact["files"]["checkpoint"]), map_location="cpu", weights_only=False)
        state = saved["state_dict"]
        arguments = saved.get("args", {})
        arguments = arguments if isinstance(arguments, dict) else vars(arguments)
        atom_width = int(state["embedding.weight"].shape[0])
        count = len({key.split(".")[1] for key in state if key.startswith("convs.")})
        hidden = int(state["conv_to_fc.weight"].shape[0])
        depth = 1 + len({key.split(".")[1] for key in state if key.startswith("fcs.")})
        feature_width = int(state["embedding.weight"].shape[1])
        edge_width = int(state["convs.0.fc_full.weight"].shape[1]) - 2 * atom_width
        model = CrystalGraphConvNet(feature_width, edge_width, atom_fea_len=atom_width, n_conv=count,
                                    h_fea_len=hidden, n_h=depth,
                                    classification=arguments.get("task", "regression") == "classification")
        model.load_state_dict(state, strict=True)
        settings = artifact.get("preprocessing", preprocessing or {})
        settings = {"radius": 8., "max_num_nbr": 12, "dmin": 0., "step": .2, **settings}
        artifact["preprocessing"] = settings
        super().__init__(model, f"{atom_width}x0e", "invariant", settings["radius"], artifact,
                         context_dim=context_dim, version="txie-93/cgcnn")
        self.unused_parameter_prefixes = ("model.conv_to_fc", "model.fcs", "model.fc_out")
        self.forcefield_requires_eval_training = True
        self.forcefield_training_mode_reason = "mixes structures in train-mode BatchNorm"
        self.settings = settings
        self.gaussian = GaussianDistance(dmin=settings["dmin"], dmax=settings["radius"], step=settings["step"])
        if len(self.gaussian.filter) != edge_width:
            raise ValueError("CGCNN Gaussian basis does not match the checkpoint; provide original preprocessing")
        with tempfile.TemporaryDirectory(prefix="ugnn-cgcnn-") as directory:
            path = Path(directory) / "atom_init.json"
            path.write_bytes(artifact["files"]["atom_init"])
            self.atom_initializer = AtomCustomJSONInitializer(str(path))

    def native_input(self, batch):
        from pymatgen.core import Structure as PymatgenStructure

        if not bool(batch.pbc.all()):
            raise ValueError("Official CGCNN CIF preprocessing requires 3D periodic structures")
        width = self.settings["max_num_nbr"]
        atom_features, edge_features, neighbor_indices, mappings = [], [], [], []
        for i in range(batch.num_graphs):
            start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
            crystal = PymatgenStructure(batch.cell[i].detach().cpu().numpy(),
                                       batch.numbers[start:end].cpu().tolist(),
                                       batch.positions[start:end].detach().cpu().numpy(),
                                       coords_are_cartesian=True)
            neighbors = [sorted(row, key=lambda neighbor: neighbor[1]) for row in
                         crystal.get_all_neighbors(self.cutoff, include_index=True)]
            indices = np.zeros((end - start, width), dtype=np.int64)
            distances = np.full((end - start, width), self.cutoff + 1., dtype=np.float64)
            images = np.zeros((end - start, width, 3), dtype=np.float64)
            valid = np.zeros((end - start, width), dtype=bool)
            for j, row in enumerate(neighbors):
                for k, neighbor in enumerate(row[:width]):
                    indices[j, k], distances[j, k] = int(neighbor[2]), float(neighbor[1])
                    images[j, k], valid[j, k] = neighbor.image, True
            device, dtype = batch.positions.device, batch.positions.dtype
            index = torch.as_tensor(indices, device=device)
            mask = torch.as_tensor(valid, device=device)
            row = torch.arange(end - start, device=device)[:, None].expand(-1, width)
            shift = torch.as_tensor(images[valid], device=device, dtype=dtype)
            displacement = (batch.positions[start:end][index[mask]] - batch.positions[start:end][row[mask]]
                            + shift @ batch.cell[i])
            live_distance = batch.positions.new_full((end - start, width), self.cutoff + 1.)
            live_distance = live_distance.masked_scatter(mask, displacement.norm(dim=-1))
            centers = torch.as_tensor(self.gaussian.filter, device=device, dtype=torch.float64)
            live = torch.exp(-(live_distance.double()[..., None] - centers).square() / self.gaussian.var ** 2).to(dtype)
            reference = torch.tensor(self.gaussian.expand(distances), dtype=torch.float32).to(device=device, dtype=dtype)
            edge_features.append(ReferenceValue.apply(reference, live))
            node_reference = np.vstack([self.atom_initializer.get_atom_fea(int(z)) for z in batch.numbers[start:end]])
            atom_features.append(torch.tensor(node_reference, dtype=torch.float32).to(device=device, dtype=dtype))
            neighbor_indices.append(index + start)
            mappings.append(torch.arange(start, end, device=device))
        return torch.cat(atom_features), torch.cat(edge_features), torch.cat(neighbor_indices), mappings

    def native_forward(self, batch):
        captured = []
        handle = self.model.convs[-1].register_forward_hook(lambda module, inputs, output: captured.append(output))
        try:
            prediction = self.model(*self.native_input(batch))
        finally:
            handle.remove()
        return prediction, captured[0]

    def encode(self, batch, context=None):
        nodes = capture_features(lambda: self.model(*self.native_input(batch)), self.model.convs[-1], lambda value: value)
        return self.output(nodes, batch, context)
