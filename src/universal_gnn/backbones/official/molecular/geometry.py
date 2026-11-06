"""All directed radius neighbors, independent of the nonperiodic placeholder cell."""

import math

import torch


def nonperiodic_edges(batch, cutoff):
    if (batch.num_graphs < 1 or bool(batch.pbc.any()) or isinstance(cutoff, bool)
            or not math.isfinite(cutoff) or cutoff <= 0):
        raise ValueError("Molecular radius input requires nonempty fully nonperiodic structures and a finite positive cutoff")
    if not bool(torch.isfinite(batch.positions).all()):
        raise ValueError("Molecular input positions must be finite")
    sources, destinations = [], []
    with torch.no_grad():
        for graph in range(batch.num_graphs):
            start, end = int(batch.ptr[graph]), int(batch.ptr[graph + 1])
            positions = batch.positions[start:end].detach().double()
            distance = (positions[:, None] - positions[None, :]).norm(dim=-1)
            diagonal = torch.eye(end - start, dtype=torch.bool, device=positions.device)
            if bool(((distance < 1e-8) & ~diagonal).any()):
                raise ValueError("Coincident atoms in molecular input")
            order = torch.argsort(distance, dim=1, stable=True)
            selected = ((distance < cutoff) & ~diagonal).gather(1, order)
            centers = torch.arange(end - start, device=positions.device)[:, None].expand_as(order)
            sources.append(centers[selected] + start)
            destinations.append(order[selected] + start)
    src, dst = torch.cat(sources), torch.cat(destinations)
    vectors = batch.positions[dst] - batch.positions[src]
    return src, dst, vectors
