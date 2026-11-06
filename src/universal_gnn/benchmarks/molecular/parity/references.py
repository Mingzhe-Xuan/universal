"""Original learned networks; independently constructed nonperiodic inputs."""

import copy
import hashlib
import json
from unittest.mock import patch

from .contracts import comparison_dtypes, edge_permutation


def comparison(actual, expected, provider, output):
    import torch

    actual = actual.detach().cpu()
    expected = torch.as_tensor(expected).detach().cpu()
    comparison_dtypes(output, str(actual.dtype), str(expected.dtype))
    if not bool(torch.isfinite(actual).all() and torch.isfinite(expected).all()):
        raise FloatingPointError("Original-model comparison contains nonfinite values")
    rtol, atol = (2e-5, 2e-6) if provider == "mace" else (3e-5, 3e-6)
    # An original head can accumulate in float64 while its learned network uses
    # float32. Promote only comparison operands; keep output values/hashes intact.
    torch.testing.assert_close(actual.double(), expected.double(), rtol=rtol, atol=atol)
    def digest(value):
        description = json.dumps([str(value.dtype), list(value.shape)], separators=(",", ":")).encode()
        return hashlib.sha256(description + value.contiguous().numpy().tobytes()).hexdigest()
    return dict(shape=list(actual.shape), max_absolute_error=float((actual.double()-expected.double()).abs().max()),
                actual_sha256=digest(actual), reference_sha256=digest(expected), rtol=rtol, atol=atol,
                actual_dtype=str(actual.dtype), reference_dtype=str(expected.dtype))


def ase_edges(structure, cutoff):
    import numpy as np
    from ase.neighborlist import primitive_neighbor_list

    xyz = structure.positions.detach().cpu().numpy()
    src, dst = primitive_neighbor_list("ij", [False]*3, np.eye(3), xyz, cutoff, self_interaction=False)
    coordinates = xyz.astype(np.float64)
    order = sorted(range(len(src)), key=lambda k: (int(src[k]), float(np.linalg.norm(coordinates[dst[k]]-coordinates[src[k]])), int(dst[k])))
    return src[order], dst[order]


class OriginalReference:
    """Same-state upstream forward parity, distinct from artifact-loading acceptance."""

    def __init__(self, provider, backbone):
        self.provider, self.backbone = provider, backbone
        self.original = copy.deepcopy(backbone.gnn if provider == "custom_knn_gcn" else backbone.model).eval()
        self.reference = "original package same-state network; independent nonperiodic preprocessing"
        if provider == "mace":
            from mace.calculators import MACECalculator
            self.calculator = MACECalculator(models=[self.original], device="cpu", default_dtype="float32")
            self.reference = "original MACECalculator.get_descriptors, energy and forces"
        elif provider == "nequip":
            from nequip.ase import NequIPCalculator
            from nequip.data.transforms import ChemicalSpeciesToAtomTypeMapper, NeighborListTransform
            self.calculator = NequIPCalculator(model=self.original, device="cpu", transforms=[
                ChemicalSpeciesToAtomTypeMapper(self.original.type_names),
                NeighborListTransform(float(self.original.metadata["r_max"]), NL="ase"), self._verified_neighbor_order])
            self.reference = "original NequIPCalculator/type mapper/NeighborListTransform(NL=ase); exact independently verified pairs reordered to native order, energy/forces/features"
        elif provider == "custom_knn_gcn":
            self.builder = copy.deepcopy(backbone.graph_builder).eval()
            self.reference = "direct directory-plugin GNN and graph builder versus StandardBackbone"
        import torch
        if any(parameter.is_floating_point() and parameter.dtype != torch.float32 for parameter in self.original.parameters()):
            raise ValueError("Original same-state reference model parameters must remain float32")

    def _verified_neighbor_order(self, data):
        import torch

        native = self._native_reference_inputs
        permutation = edge_permutation(data["edge_index"].T.tolist(), native["edge_index"].T.tolist(), len(data["pos"]))
        order = torch.tensor(permutation, dtype=torch.long, device=data["edge_index"].device)
        if (data["edge_cell_shift"].shape != native["edge_cell_shift"].shape
                or bool(data["edge_cell_shift"].any()) or bool(native["edge_cell_shift"].any())):
            raise ValueError("Independent nonperiodic neighbors must retain zero images")
        data["edge_index"] = data["edge_index"].index_select(1, order)
        data["edge_cell_shift"] = data["edge_cell_shift"].index_select(0, order)
        return data

    def state(self):
        from ...native_heads.evaluation import state_digest
        return state_digest(self.original)

    def _cgcnn(self, structure, batch):
        import numpy as np
        import torch

        backbone = self.backbone
        src, dst = ase_edges(structure, backbone.cutoff)
        degree = np.bincount(src, minlength=len(structure.numbers))
        if not np.all(degree == degree[0]) or not int(degree[0]):
            raise ValueError("The full-ethanol original dense reference requires regular nonempty neighborhoods")
        width = int(degree[0]);xyz = structure.positions.detach().cpu().numpy().astype(np.float64)
        distances = np.linalg.norm(xyz[dst]-xyz[src], axis=1).reshape(len(xyz), width)
        parameter = next(self.original.parameters())
        atoms = np.vstack([backbone.atom_initializer.get_atom_fea(int(z)) for z in structure.numbers])
        inputs = (torch.tensor(atoms, dtype=torch.float32).to(parameter),
                  torch.as_tensor(backbone.gaussian.expand(distances)).to(parameter),
                  torch.tensor(dst.reshape(len(xyz), width), dtype=torch.long), [torch.arange(len(xyz))])
        native = backbone.native_input(batch)
        if native.valid_mask.shape != (len(xyz), width) or not bool(native.valid_mask.all()):
            raise ValueError("Original dense ethanol comparison cannot silently omit padded messages")
        captured = []
        handle = self.original.convs[-1].register_forward_hook(lambda module,args,out: captured.append(out.detach()))
        try:
            expected = self.original(*inputs)
        finally:
            handle.remove()
        predicted, nodes = backbone.native_forward(batch)
        return {"node_features": comparison(nodes, captured[0], self.provider, "node_features"),
                "native_head": comparison(predicted, expected, self.provider, "native_head")}

    def _alignn(self, structure, batch):
        import numpy as np
        import torch
        from alignn import torch_graph_builder as upstream
        from ase.data import chemical_symbols
        from jarvis.core.atoms import Atoms
        from universal_gnn.backbones.official.base import default_dtype

        backbone = self.backbone
        src, dst = ase_edges(structure, backbone.cutoff)
        def topology(positions, lattice, cutoff, **kwargs):
            if cutoff != backbone.cutoff:
                raise ValueError("Independent molecular graph cutoff changed")
            a, b = torch.tensor(src, device=positions.device), torch.tensor(dst, device=positions.device)
            return a, b, positions.new_zeros((len(a), 3)), positions[b]-positions[a]
        atoms = Atoms(lattice_mat=np.eye(3), coords=structure.positions.detach().numpy(), cartesian=True,
                      elements=[chemical_symbols[int(z)] for z in structure.numbers])
        with patch.object(upstream, "torch_neighbor_list", topology), default_dtype(torch.float32):
            parent, line = upstream.build_pure_torch_graph(atoms=atoms, two_body_cutoff=backbone.cutoff,
                three_body_cutoff=backbone.configuration.get("three_body_cutoff", 3.5), max_neighbors=None,
                atom_features=backbone.configuration.get("atom_features", "cgcnn"), positions=batch.positions,
                lattice=structure.cell, device="cpu")
        if bool(parent.edata["images"].any()):
            raise ValueError("Independent nonperiodic ALIGNN reference introduced images")
        captured = []
        def capture(module, args, output):
            captured.append((output if backbone.feature_path == "atom_embedding" else output[0]).detach())
        handle = self.original.get_submodule(backbone.feature_path).register_forward_hook(capture)
        try:
            expected = self.original((parent, line, structure.cell[None]))["out"]
        finally:
            handle.remove()
        predicted, nodes = backbone.native_forward(batch)
        return {"node_features": comparison(nodes, captured[0], self.provider, "node_features"),
                "native_head": comparison(predicted["out"], expected, self.provider, "native_head")}

    def _calculator(self, structure, batch):
        import torch
        from ase import Atoms
        from universal_gnn.backbones.official.base import default_dtype

        atoms = Atoms(numbers=structure.numbers.numpy(), positions=structure.positions.numpy(),
                      cell=structure.cell.numpy(), pbc=[False]*3)
        # Always capture a fresh original forward, including repeated geometries.
        self.calculator.reset()
        atoms.calc = self.calculator
        captured, reference_inputs = [], []
        handles = []
        if self.provider == "nequip":
            self._native_reference_inputs = self.backbone.native_input(batch)
            handles.append(self.original.register_forward_pre_hook(lambda module,args:
                reference_inputs.append({k:v.detach().clone() for k,v in args[0].items()})))
            handles.append(self.original.get_submodule(self.backbone.feature_path).register_forward_pre_hook(
                lambda module,args: captured.append(args[0]["node_features"].detach())))
        try:
            with default_dtype(torch.float32):
                energy = float(atoms.get_potential_energy());forces = atoms.get_forces()
                if self.provider == "mace":
                    features = self.calculator.get_descriptors(atoms, invariants_only=False)
                else:
                    features = captured[0]
        finally:
            for handle in reversed(handles):handle.remove()
        if self.provider == "mace":
            batch.positions.requires_grad_(True)
            predicted = self.backbone.native_forward(batch)
            native_energy = predicted["energy"]
            native_forces = -torch.autograd.grad(native_energy.sum(), batch.positions)[0]
            nodes = predicted["node_feats"]
        else:
            native = self.backbone.native_input(batch)
            reference = reference_inputs[0]
            if set(native) != set(reference):
                raise ValueError("Independent NequIP original input keys differ")
            for key, expected in reference.items():
                if key == "edge_cell_shift":
                    if native[key].shape != expected.shape or bool(native[key].any()) or bool(expected.any()):
                        raise ValueError("Original nonperiodic comparison requires zero image shifts")
                else:
                    torch.testing.assert_close(native[key], expected, rtol=0, atol=0)
            predicted, nodes = self.backbone.native_forward(batch)
            native_energy, native_forces = predicted["total_energy"], predicted["forces"]
        return {"node_features": comparison(nodes, features, self.provider, "node_features"),
                "native_energy": comparison(native_energy.reshape(-1), torch.tensor([energy], dtype=torch.float64), self.provider, "native_energy"),
                "native_forces": comparison(native_forces, forces, self.provider, "native_forces")}

    def compare(self, structure):
        import torch
        from universal_gnn.contracts import StructureBatch

        if bool(structure.pbc.any()) or len(structure.numbers) != 9:
            raise ValueError("Use an actual nonperiodic nine-atom ethanol training record")
        batch = StructureBatch.from_structures([structure]).to("cpu", torch.float32)
        if self.provider in {"alignn", "mace", "nequip"}:
            native = self.backbone.native_input(batch)
            shifts = [native[0].edata["images"]] if self.provider == "alignn" else [
                native[key] for key in ["shifts", "unit_shifts", "edge_cell_shift"] if key in native]
            if not shifts or any(bool(value.any()) for value in shifts):
                raise ValueError("Native molecular comparison introduced periodic image shifts")
        if self.provider == "cgcnn":return self._cgcnn(structure, batch)
        if self.provider == "alignn":return self._alignn(structure, batch)
        if self.provider in {"mace", "nequip"}:return self._calculator(structure, batch)
        graph = self.builder(batch)
        if graph.geometry is not batch or bool(graph.cell_shifts.any()):
            raise ValueError("Direct plugin graph changed the supplied nonperiodic geometry")
        expected = self.original(graph, None).nodes
        actual = self.backbone.encode(batch).nodes
        return {"node_features": comparison(actual, expected, self.provider, "node_features")}
