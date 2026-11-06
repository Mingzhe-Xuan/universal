"""Original ALIGNN containers, atom descriptors and triplets on nonperiodic edges."""

import torch

from .geometry import nonperiodic_edges


def molecular_input(backbone, batch):
    from ase.data import chemical_symbols
    from jarvis.core.specie import get_node_attributes
    from alignn.torch_graph_builder import TorchGraph, _line_graph_edges, batch_torch_graph_pairs, torch_bond_cosines

    if backbone.configuration.get("use_lattice_prop", False):
        raise ValueError("Molecular input cannot invent original ALIGNN lattice-property features")
    src, dst, vectors = nonperiodic_edges(batch, backbone.input_profile["cutoff"])
    pairs = []
    for graph in range(batch.num_graphs):
        start, end = int(batch.ptr[graph]), int(batch.ptr[graph + 1])
        selected = (src >= start) & (src < end)
        a, b, r = src[selected] - start, dst[selected] - start, vectors[selected]
        images = batch.positions.new_zeros((len(a), 3))
        attributes = [list(get_node_attributes(chemical_symbols[int(z)], atom_features=backbone.configuration.get("atom_features", "cgcnn")))
                      for z in batch.numbers[start:end]]
        parent = TorchGraph(num_nodes=end - start, src=a, dst=b,
            ndata={"atom_features": batch.positions.new_tensor(attributes), "Z": batch.numbers[start:end]},
            edata={"r": r, "images": images})
        three_body = backbone.configuration.get("three_body_cutoff")
        three_body = backbone.input_profile["cutoff"] if three_body is None else three_body
        with torch.no_grad():
            allowed = r.norm(dim=-1) <= three_body
            left, right = _line_graph_edges(a, b, end - start, allowed=allowed)
        line = TorchGraph(num_nodes=len(a), src=left, dst=right,
            ndata={"r": r, "images": images}, edata={"h": torch_bond_cosines(r[left], r[right])})
        pairs.append((parent, line))
    parent, line = batch_torch_graph_pairs(pairs)
    return parent, line, batch.cell
