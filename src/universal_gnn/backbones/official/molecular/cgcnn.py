"""Original dense CGCNN inputs with explicit valid edges, never fake padding messages."""

from contextlib import contextmanager

import numpy as np
import torch

from .geometry import nonperiodic_edges


class MolecularCGCNNInput(tuple):
    def __new__(cls, values, valid_mask):
        result = super().__new__(cls, values)
        result.valid_mask = valid_mask
        return result


def molecular_input(backbone, batch):
    src, dst, _ = nonperiodic_edges(batch, backbone.input_profile["cutoff"])
    device, dtype = batch.positions.device, batch.positions.dtype
    n = len(batch.numbers)
    degrees = torch.bincount(src, minlength=n)
    width = int(degrees.max())
    slots = torch.arange(len(src), device=device) - torch.repeat_interleave(degrees.cumsum(0) - degrees, degrees)
    index = torch.zeros((n, width), dtype=torch.long, device=device)
    valid = torch.zeros((n, width), dtype=torch.bool, device=device)
    index[src, slots], valid[src, slots] = dst, True
    centers = torch.as_tensor(backbone.gaussian.filter, device=device, dtype=torch.float64)
    distance = (batch.positions[dst].double() - batch.positions[src].double()).norm(dim=-1)
    radial = torch.exp(-(distance[:, None] - centers).square() / backbone.gaussian.var ** 2).to(dtype)
    edges = batch.positions.new_zeros((n, width, len(centers)))
    edges[src, slots] = radial
    original = np.vstack([backbone.atom_initializer.get_atom_fea(int(z)) for z in batch.numbers])
    atoms = torch.tensor(original, dtype=torch.float32).to(device=device, dtype=dtype)
    mappings = [torch.arange(int(batch.ptr[i]), int(batch.ptr[i + 1]), device=device) for i in range(batch.num_graphs)]
    return MolecularCGCNNInput((atoms, edges, index, mappings), valid)


@contextmanager
def valid_neighbor_messages(model, inputs):
    """Keep original forwards/modules; padding is absent from edge BN and aggregation."""
    mask = inputs.valid_mask
    handles, empty_modes = [], []
    try:
        if mask.numel() == 0:
            # No real edge observation exists: do not update BatchNorm's edge statistics/counter.
            for conv in model.convs:
                empty_modes.append((conv.bn1, conv.bn1.training))
                conv.bn1.training = False
        elif not bool(mask.all()):
            flattened = mask.reshape(-1)
            indices = flattened.nonzero(as_tuple=False).flatten()

            def select(module, arguments):
                value = arguments[0]
                if value.shape[0] != flattened.numel():
                    raise ValueError("CGCNN valid-edge mask and original BatchNorm input differ")
                return (value.index_select(0, indices),)

            def restore(module, arguments, value):
                return value.new_zeros((flattened.numel(), value.shape[-1])).index_copy(0, indices, value)

            def mask_gate(module, arguments, value):
                return value.masked_fill(~mask[:, :, None], 0.)

            for conv in model.convs:
                handles.append(conv.bn1.register_forward_pre_hook(select))
                handles.append(conv.bn1.register_forward_hook(restore))
                handles.append(conv.sigmoid.register_forward_hook(mask_gate))
        yield
    finally:
        for handle in reversed(handles):
            handle.remove()
        for module, training in empty_modes:
            module.training = training
