"""Published MACE model with original AtomicData construction and original forward."""

from importlib.metadata import version
import io
import re

import torch

from .base import OfficialBackbone, artifact_files
from universal_gnn.backbones.initialization import initialize_original, validate_initialization


def canonical_scratch_blueprint(model, reference):
    """Account for structural contraction flags absent from older complete-module artifacts."""
    state, actual = reference.state_dict(), model.state_dict()
    migrated = []
    parameters = dict(reference.named_parameters())
    for key in sorted(set(actual) - set(state)):
        match = re.fullmatch(r"(products\.[0-9]+\.symmetric_contractions\.contractions\.[0-9]+\.)weights_(max|[0-9]+)_zeroed", key)
        if match is None:
            raise ValueError(f"Unknown fresh MACE state entry absent from original artifact: {key}")
        parameter_key = match[1] + ("weights_max" if match[2] == "max" else "weights." + match[2])
        flag = actual[key]
        # These flags describe empty contraction paths, never fitted values. The registered
        # legacy artifact has only nonempty paths; any different migration is unsupported.
        if (flag.dtype != torch.bool or flag.shape != torch.Size([]) or bool(flag) or
                parameter_key not in parameters or parameters[parameter_key].numel() == 0 or
                parameter_key not in actual or actual[parameter_key].shape != parameters[parameter_key].shape):
            raise ValueError(f"Unsupported legacy MACE contraction flag migration: {key}")
        state[key] = flag.detach().clone()
        migrated.append(key)
    return state, migrated


class OfficialMACE(OfficialBackbone):
    def __init__(self, checkpoint=None, *, context_dim=0, source=None, _artifact=None,
                 initialization="pretrained", neighbor_statistics=None):
        validate_initialization(initialization)
        if initialization == "pretrained" and neighbor_statistics is not None:
            raise ValueError("Pretrained MACE retains its original normalization; neighbor_statistics is scratch-only")
        artifact = artifact_files("mace", {"model": checkpoint}, artifact=_artifact, source=source)
        # MACE releases complete Python modules as its trainable .model artifact.
        model = torch.load(io.BytesIO(artifact["files"]["model"]), map_location="cpu", weights_only=False)
        report = None
        if initialization == "scratch":
            from mace.tools.scripts_utils import extract_config_mace_model
            from universal_gnn.backbones.blueprints import mace_constructor_config

            if type(model).__name__ != "ScaleShiftMACE" or getattr(model, "embedding_specs", None) is not None:
                raise ValueError("Fresh official MACE currently requires the original ScaleShiftMACE without auxiliary embeddings")
            reference = model
            config = mace_constructor_config(extract_config_mace_model(reference), neighbor_statistics)
            with torch.random.fork_rng(devices=[]):
                model = type(reference)(**config)
            blueprint, migrations = canonical_scratch_blueprint(model, reference)
            report = initialize_original(model, blueprint, mode="scratch")
            report["structural_state_migrations"] = migrations
            report["neighbor_statistics"] = neighbor_statistics
        from universal_gnn.contracts.e3nn_compat import load_o3

        o3 = load_o3()
        irreps = o3.Irreps("")
        for product in model.products:
            irreps += product.linear.irreps_out
        super().__init__(model, str(irreps), "equivariant", float(model.r_max), artifact,
                         context_dim=context_dim, version=version("mace-torch"), initialization=initialization)
        if report is not None:
            self.validate_native_neighbor_graph(neighbor_statistics)
            self.load_report.update(report)
        self.gradient_capabilities = {"positions": True, "strain": True, "mixed": True}
        self.unused_parameter_prefixes = ("model.readouts",)

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
