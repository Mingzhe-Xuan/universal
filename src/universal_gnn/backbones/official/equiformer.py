"""The original Equiformer V1 OC20 implementation and published IS2RE checkpoint."""

import io

import torch

from .base import OfficialBackbone, ReferenceValue, artifact_files, capture_features, default_dtype, attach_periodic_topology


class OfficialEquiformer(OfficialBackbone):
    def __init__(self, checkpoint=None, *, context_dim=0, source=None, _artifact=None):
        from nets.graph_attention_transformer_oc20 import GraphAttentionTransformerOC20

        artifact = artifact_files("equiformer", {"checkpoint": checkpoint}, artifact=_artifact, source=source)
        saved = torch.load(io.BytesIO(artifact["files"]["checkpoint"]), map_location="cpu", weights_only=False)
        configuration = saved["config"]
        if configuration["model"] != "graph_attention_transformer":
            raise ValueError("This official provider requires the published Equiformer V1 OC20 checkpoint")
        settings = configuration["model_attributes"]
        if settings.get("use_attention_head", False):
            raise ValueError("The supported official V1 artifact uses its original feed-forward readout")
        model = GraphAttentionTransformerOC20(num_atoms=None, bond_feat_dim=None, num_targets=1, **settings)
        state = saved["state_dict"]
        while state and all(key.startswith("module.") for key in state):
            state = {key.removeprefix("module."): value for key, value in state.items()}
        model.load_state_dict(state, strict=True)
        super().__init__(model, str(model.irreps_feature), "equivariant", model.max_radius, artifact,
                         context_dim=context_dim, version="atomicarchitects/equiformer-v1-oc20")
        self.configuration = configuration
        self.original_otf_graph = bool(model.otf_graph)
        # Use the original model's precomputed-topology path; live distances remain
        # in _forward_use_pbc. OCP's integer arange bounds cannot carry strain grad.
        if self.original_otf_graph:
            model.otf_graph = False
        self.transformation = "SO3"
        self.unused_parameter_prefixes = ("model.head", "model.head_skip_connect", "model.auxiliary_head")
        self.load_report["symmetry"] = "SO(3); reflection equivariance is not claimed by this pretrained artifact"

    def native_input(self, batch):
        from ase import Atoms
        from ocpmodels.preprocessing import AtomsToGraphs
        from torch_geometric.data import Batch

        if self.model.use_pbc and not bool(batch.pbc.all()):
            raise ValueError("This published Equiformer OC20 artifact uses 3D periodic graphs")
        if bool((batch.numbers >= 84).any()):
            raise ValueError("The original Equiformer OC20 embedding supports atomic numbers below 84")
        converter = AtomsToGraphs(max_neigh=self.model.max_neighbors, radius=self.cutoff,
                                  r_energy=False, r_forces=False, r_distances=False,
                                  r_edges=not self.original_otf_graph, r_fixed=True)
        graphs = []
        with default_dtype(batch.positions.dtype):
            for i in range(batch.num_graphs):
                start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
                atoms = Atoms(numbers=batch.numbers[start:end].cpu().numpy(),
                              positions=batch.positions[start:end].detach().cpu().numpy(),
                              cell=batch.cell[i].detach().cpu().numpy(), pbc=batch.pbc[i].cpu().numpy())
                tags = batch.metadata[i].get("atomic_tags")
                if tags is not None:
                    if len(tags) != end - start or any(tag not in (0, 1, 2) for tag in tags):
                        raise ValueError("Equiformer atomic_tags must give one original OC20 tag (0,1,2) per atom")
                    atoms.set_tags(tags)
                graph = converter.convert(atoms).to(batch.positions.device)
                graph.tags = batch.positions.new_tensor(atoms.get_tags())
                graph.pos = ReferenceValue.apply(graph.pos.to(batch.positions), batch.positions[start:end])
                graph.cell = ReferenceValue.apply(graph.cell.to(batch.cell), batch.cell[i:i + 1])
                graphs.append(graph)
        data = Batch.from_data_list(graphs)
        if self.original_otf_graph:
            from ocpmodels.common.utils import radius_graph_pbc

            attach_periodic_topology(data, radius_graph_pbc, self.cutoff, self.model.max_neighbors)
        return data

    def native_forward(self, batch):
        captured = []
        handle = self.model.head.register_forward_pre_hook(lambda module, inputs: captured.append(inputs[0]))
        try:
            prediction = self.model(self.native_input(batch))
        finally:
            handle.remove()
        return prediction, captured[0]

    def encode(self, batch, context=None):
        nodes = capture_features(lambda: self.model(self.native_input(batch)), self.model.head,
                                 lambda inputs: inputs[0], before=True)
        return self.output(nodes, batch, context)
