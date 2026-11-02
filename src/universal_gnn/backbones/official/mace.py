"""Published MACE model with original AtomicData construction and original forward."""

from importlib.metadata import version
import io

import torch

from .base import OfficialBackbone, artifact_files


class OfficialMACE(OfficialBackbone):
    def __init__(self, checkpoint=None, *, context_dim=0, source=None, _artifact=None):
        artifact = artifact_files("mace", {"model": checkpoint}, artifact=_artifact, source=source)
        # MACE releases complete Python modules as its trainable .model artifact.
        model = torch.load(io.BytesIO(artifact["files"]["model"]), map_location="cpu", weights_only=False)
        from universal_gnn.contracts.e3nn_compat import load_o3

        o3 = load_o3()
        irreps = o3.Irreps("")
        for product in model.products:
            irreps += product.linear.irreps_out
        super().__init__(model, str(irreps), "equivariant", float(model.r_max), artifact,
                         context_dim=context_dim, version=version("mace-torch"))

    def native_input(self, batch):
        from ase import Atoms
        from mace.data import AtomicData
        from mace.data.utils import config_from_atoms
        from mace.tools import AtomicNumberTable, torch_geometric

        table = AtomicNumberTable([int(z) for z in self.model.atomic_numbers])
        values = []
        for i in range(batch.num_graphs):
            start, end = int(batch.ptr[i]), int(batch.ptr[i + 1])
            atoms = Atoms(numbers=batch.numbers[start:end].detach().cpu().numpy(),
                          positions=batch.positions[start:end].detach().cpu().numpy(),
                          cell=batch.cell[i].detach().cpu().numpy(), pbc=batch.pbc[i].cpu().numpy())
            values.append(AtomicData.from_config(config_from_atoms(atoms), z_table=table, cutoff=self.cutoff,
                                                 heads=getattr(self.model, "heads", None)))
        graph = torch_geometric.Batch.from_data_list(values).to(batch.positions.device)
        data = graph.to_dict()
        for name, value in list(data.items()):
            if isinstance(value, torch.Tensor) and value.is_floating_point():
                data[name] = value.to(batch.positions.dtype)
        # Restore live geometry after the official discrete neighbor-list construction.
        data["positions"] = batch.positions
        data["cell"] = batch.cell.reshape(-1, 3)
        edge_batch = batch.batch[data["edge_index"][0]]
        data["shifts"] = torch.einsum("ei,eij->ej", data["unit_shifts"], batch.cell[edge_batch])
        return data

    def native_forward(self, batch):
        return self.model(self.native_input(batch), training=self.training,
                          compute_force=False, compute_virials=False, compute_stress=False)

    def encode(self, batch, context=None):
        return self.output(self.native_forward(batch)["node_feats"], batch, context)
