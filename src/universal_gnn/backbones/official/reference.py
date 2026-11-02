"""Independent upstream data APIs and forwards for published-checkpoint acceptance."""

import copy
import csv
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

import torch

from universal_gnn.contracts import StructureBatch
from .base import default_dtype


def ase_atoms(structure):
    from ase import Atoms

    atoms = Atoms(numbers=structure.numbers.numpy(), positions=structure.positions.numpy(),
                  cell=structure.cell.numpy(), pbc=structure.pbc.numpy())
    if "atomic_tags" in structure.metadata:
        atoms.set_tags(structure.metadata["atomic_tags"])
    return atoms


def pymatgen_structure(structure):
    from pymatgen.core import Structure

    return Structure(structure.cell.numpy(), structure.numbers.tolist(), structure.positions.numpy(),
                     coords_are_cartesian=True)


def assert_same(actual, expected):
    actual, expected = actual.detach().cpu(), torch.as_tensor(expected).detach().cpu()
    torch.testing.assert_close(actual, expected, rtol=3e-5, atol=3e-6)
    return float((actual - expected).abs().max()) if actual.numel() else 0.


def cgcnn_reference(backbone, structures, config):
    from cgcnn.data import CIFData, collate_pool, Structure

    original = copy.deepcopy(backbone.model).eval()
    captures = []
    handle = original.convs[-1].register_forward_hook(lambda module, inputs, output: captures.append(output.detach()))
    try:
        with tempfile.TemporaryDirectory(prefix="ugnn-reference-cgcnn-") as directory:
            root = Path(directory)
            (root / "atom_init.json").write_bytes(backbone.official_artifact["files"]["atom_init"])
            with (root / "id_prop.csv").open("w", newline="") as stream:
                writer = csv.writer(stream)
                for index, structure in enumerate(structures):
                    writer.writerow([index, float(torch.as_tensor(structure.targets[config["task"]["property"]]).flatten()[0])])
            crystals = [pymatgen_structure(structure) for structure in structures]
            reference_data = CIFData(directory, **{key: backbone.settings[key] for key in
                                      ("max_num_nbr", "radius", "dmin", "step")})
            # Only file I/O is adapted: the original CIFData graph/basis implementation runs unchanged.
            # This avoids lossy CIF coordinate serialization while using the exact real input geometry.
            with patch.object(Structure, "from_file", side_effect=lambda path: crystals[int(Path(path).stem)]):
                with default_dtype(torch.float32):
                    loaded = {row[2]: row for row in reference_data}
            inputs, labels, ids = collate_pool([loaded[str(index)] for index in range(len(structures))])
            inputs = [value.to(next(original.parameters())) if index < 2 else value
                      for index, value in enumerate(inputs)]
            reference_prediction = original(*inputs).detach()
    finally:
        handle.remove()
    batch = StructureBatch.from_structures(list(structures))
    native_prediction, native_nodes = backbone.native_forward(batch)
    return {"reference": "unmodified CGCNN CIFData/collate_pool/model; in-memory file-I/O adapter",
            "structures": len(structures), "max_feature_error": assert_same(native_nodes, captures[0]),
            "max_prediction_error": assert_same(native_prediction, reference_prediction)}


def megnet_reference(backbone, structures, config):
    original = copy.deepcopy(backbone.model).eval()
    errors, prediction_errors = [], []
    for structure in structures:
        captured = []
        handle = original.model.blocks[-1].register_forward_hook(
            lambda module, inputs, output: captured.append((output[1].detach(), output[2].detach())))
        try:
            reference_prediction = original.predict_structure(pymatgen_structure(structure))
        finally:
            handle.remove()
        nodes, state = captured[0]
        reference_nodes = torch.cat((nodes, state.reshape(1, -1).expand(len(nodes), -1)), dim=-1)
        batch = StructureBatch.from_structures([structure])
        native_prediction, native_nodes = backbone.native_forward(batch)
        errors.append(assert_same(native_nodes, reference_nodes))
        prediction_errors.append(assert_same(native_prediction.reshape(-1), reference_prediction.reshape(-1)))
    return {"reference": "official MatGL TransformedTargetModel.predict_structure",
            "structures": len(structures), "max_feature_error": max(errors), "max_prediction_error": max(prediction_errors)}


def alignn_reference(backbone, structures, config):
    from ase.data import chemical_symbols
    from jarvis.core.atoms import Atoms
    from alignn.graphs import Graph
    from alignn.torch_graph_builder import batch_torch_graph_pairs

    original = copy.deepcopy(backbone.model).eval()
    settings = backbone.configuration
    pairs = []
    for structure in structures:
        atoms = Atoms(lattice_mat=structure.cell.numpy(), coords=structure.positions.numpy(), cartesian=True,
                      elements=[chemical_symbols[int(z)] for z in structure.numbers])
        pairs.append(Graph.atom_dgl_multigraph(atoms=atoms, neighbor_strategy=settings["neighbor_strategy"],
                     cutoff=settings["cutoff"], max_neighbors=settings.get("max_neighbors", 12),
                     atom_features=settings.get("atom_features", "cgcnn"), compute_line_graph=True,
                     use_canonize=settings.get("use_canonize", True),
                     use_lattice_prop=settings.get("use_lattice_prop", False),
                     dtype=config["dtype"], three_body_cutoff=settings.get("three_body_cutoff", 3.5)))
    graph, line_graph = batch_torch_graph_pairs(pairs)
    batch = StructureBatch.from_structures(list(structures))
    captured = []
    handle = original.get_submodule(backbone.feature_path).register_forward_hook(
        lambda module, inputs, output: captured.append(output if backbone.feature_path == "atom_embedding" else output[0]))
    try:
        reference_prediction = original((graph, line_graph, batch.cell))
    finally:
        handle.remove()
    native_prediction, native_nodes = backbone.native_forward(batch)
    return {"reference": "official Graph.atom_dgl_multigraph and original ALIGNN forward",
            "structures": len(structures), "max_feature_error": assert_same(native_nodes, captured[0]),
            "max_prediction_error": assert_same(native_prediction["out"], reference_prediction["out"])}


def nequip_reference(backbone, structures, config):
    from nequip.ase import NequIPCalculator
    from nequip.data.transforms import ChemicalSpeciesToAtomTypeMapper, NeighborListTransform

    original = copy.deepcopy(backbone.model).eval()
    calculator = NequIPCalculator(model=original, device="cpu", transforms=[
        ChemicalSpeciesToAtomTypeMapper(original.type_names), NeighborListTransform(float(original.metadata["r_max"]))])
    errors, energy_errors, force_errors = [], [], []
    for structure in structures:
        captured = []
        handle = original.get_submodule(backbone.feature_path).register_forward_pre_hook(
            lambda module, inputs: captured.append(inputs[0]["node_features"].detach()))
        atoms = ase_atoms(structure)
        atoms.calc = calculator
        try:
            with default_dtype(structure.positions.dtype):
                reference_energy = float(atoms.get_potential_energy())
                reference_forces = atoms.get_forces()
        finally:
            handle.remove()
        batch = StructureBatch.from_structures([structure])
        native_prediction, native_nodes = backbone.native_forward(batch)
        errors.append(assert_same(native_nodes, captured[0]))
        energy_errors.append(assert_same(native_prediction["total_energy"].reshape(-1),
                                         native_prediction["total_energy"].new_tensor([reference_energy])))
        force_errors.append(assert_same(native_prediction["forces"], reference_forces))
    return {"reference": "official NequIPCalculator with original type and neighbor transforms",
            "structures": len(structures), "max_feature_error": max(errors),
            "max_energy_error": max(energy_errors), "max_force_error": max(force_errors)}


def equiformer_reference(backbone, structures, config):
    from nets.graph_attention_transformer_oc20 import GraphAttentionTransformerOC20
    from ocpmodels.preprocessing import AtomsToGraphs
    from torch_geometric.data import Batch

    saved = torch.load(io.BytesIO(backbone.official_artifact["files"]["checkpoint"]),
                       map_location="cpu", weights_only=False)
    original = GraphAttentionTransformerOC20(None, None, 1, **saved["config"]["model_attributes"])
    state = saved["state_dict"]
    while all(key.startswith("module.") for key in state):
        state = {key[7:]: value for key, value in state.items()}
    original.load_state_dict(state, strict=True)
    original.to(next(backbone.model.parameters())).eval()
    converter = AtomsToGraphs(max_neigh=original.max_neighbors, radius=original.max_radius,
                               r_energy=False, r_forces=False, r_distances=False, r_edges=not original.otf_graph)
    graphs = []
    with default_dtype(next(original.parameters()).dtype):
        for structure in structures:
            atoms = ase_atoms(structure)
            graph = converter.convert(atoms)
            graph.tags = torch.tensor(atoms.get_tags())
            graphs.append(graph)
    reference_batch = Batch.from_data_list(graphs)
    captured = []
    handle = original.head.register_forward_pre_hook(lambda module, inputs: captured.append(inputs[0].detach()))
    try:
        reference_prediction = original(reference_batch).detach()
    finally:
        handle.remove()
    batch = StructureBatch.from_structures(list(structures))
    native_prediction, native_nodes = backbone.native_forward(batch)
    return {"reference": "original V1 constructor/config/state, original OCP AtomsToGraphs and full forward",
            "structures": len(structures), "max_feature_error": assert_same(native_nodes, captured[0]),
            "max_prediction_error": assert_same(native_prediction, reference_prediction)}


def compare_reference(backbone, structures, config):
    functions = {"cgcnn": cgcnn_reference, "megnet": megnet_reference, "alignn": alignn_reference,
                 "nequip": nequip_reference, "equiformer": equiformer_reference}
    return functions[config["backbone"]["name"]](backbone, structures, config)
