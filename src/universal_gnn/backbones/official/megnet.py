"""The MEGNet authors' MatGL implementation and its published original model files."""

from importlib.metadata import version
import json
from pathlib import Path
import tempfile

import torch

from .base import OfficialBackbone, ReferenceValue, artifact_files, capture_features


class OfficialMEGNet(OfficialBackbone):
    def __init__(self, checkpoint=None, *, context_dim=0, source=None, _artifact=None):
        import matgl
        from matgl.data.transformer import Normalizer

        files = {name: Path(checkpoint) / name for name in ("model.json", "model.pt", "state.pt")} if _artifact is None else {}
        artifact = artifact_files("megnet", files, artifact=_artifact, source=source)
        with tempfile.TemporaryDirectory(prefix="ugnn-megnet-") as directory:
            for name, content in artifact["files"].items():
                (Path(directory) / name).write_bytes(content)
            with torch.serialization.safe_globals([Normalizer]):
                model = matgl.load_model(directory)
        configuration = json.loads(artifact["files"]["model.json"])
        width = configuration["kwargs"]["model"]["init_args"]["hidden_layer_sizes_conv"][-1]
        super().__init__(model, f"{2 * width}x0e", "invariant", model.model.cutoff, artifact,
                         context_dim=context_dim, version=version("matgl"))

    def native_input(self, batch):
        import dgl
        from matgl.ext.pymatgen import Structure2Graph
        from pymatgen.core import Structure as PymatgenStructure

        if not bool(batch.pbc.all()):
            raise ValueError("This official MatGL crystal checkpoint requires 3D periodic structures")
        converter = Structure2Graph(element_types=self.model.model.element_types, cutoff=self.cutoff)
        graphs, states = [], []
        for i in range(batch.num_graphs):
            start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
            crystal = PymatgenStructure(batch.cell[i].detach().cpu().numpy(),
                                       batch.numbers[start:end].cpu().tolist(),
                                       batch.positions[start:end].detach().cpu().numpy(),
                                       coords_are_cartesian=True)
            graph, lattice, state = converter.get_graph(crystal)
            reference_positions = graph.ndata["frac_coords"] @ lattice[0]
            reference_shifts = graph.edata["pbc_offset"] @ lattice[0]
            graph = graph.to(batch.positions.device)
            graph.ndata["pos"] = ReferenceValue.apply(
                reference_positions.to(batch.positions), batch.positions[start:end])
            live_shifts = graph.edata["pbc_offset"].to(batch.cell.dtype) @ batch.cell[i]
            graph.edata["pbc_offshift"] = ReferenceValue.apply(reference_shifts.to(batch.cell), live_shifts)
            graphs.append(graph)
            states.append(state)
        return dgl.batch(graphs), batch.positions.new_tensor(states)

    def native_forward(self, batch):
        captured = []
        handle = self.model.model.blocks[-1].register_forward_hook(
            lambda module, inputs, output: captured.append((output[1], output[2])))
        try:
            graph, state = self.native_input(batch)
            prediction = self.model(graph, state_attr=state)
        finally:
            handle.remove()
        nodes, state = captured[0]
        return prediction, torch.cat((nodes, state[batch.batch]), dim=-1)

    def encode(self, batch, context=None):
        def forward():
            graph, state = self.native_input(batch)
            return self.model(graph, state_attr=state)

        nodes, state = capture_features(forward, self.model.model.blocks[-1], lambda value: (value[1], value[2]))
        nodes = torch.cat((nodes, state[batch.batch]), dim=-1)
        return self.output(nodes, batch, context)
