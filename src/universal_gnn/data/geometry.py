from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from torch import Tensor

from universal_gnn.contracts import StructureBatch


def scatter_sum(values: Tensor, index: Tensor, size: int) -> Tensor:
    return values.new_zeros((size, *values.shape[1:])).index_add(0, index, values)


def scatter_mean(values: Tensor, index: Tensor, size: int) -> Tensor:
    counts = scatter_sum(values.new_ones((len(values),)), index, size).clamp_min(1)
    return scatter_sum(values, index, size) / counts.reshape(size, *([1] * (values.ndim - 1)))


def smooth_cutoff(distance: Tensor, cutoff: float) -> Tensor:
    x = (distance / cutoff).clamp(0, 1)
    return (1 - x).pow(3) * (1 + 3 * x + 6 * x.square())


@dataclass
class PeriodicGraph:
    src: Tensor
    dst: Tensor
    images: Tensor
    edge_batch: Tensor
    vectors: Tensor
    distances: Tensor
    weights: Tensor
    cutoff: float

    @property
    def edge_index(self) -> Tensor:
        return torch.stack([self.src, self.dst])

    def triplets(self) -> tuple[Tensor, Tensor]:
        first, second = [], []
        for node in torch.unique(self.dst).tolist():
            edges = torch.where(self.dst == node)[0]
            a, b = edges.repeat_interleave(len(edges)), edges.repeat(len(edges))
            keep = a != b
            first.append(a[keep])
            second.append(b[keep])
        if not first:
            return self.src.new_empty(0), self.src.new_empty(0)
        return torch.cat(first), torch.cat(second)


def radius_graph(batch: StructureBatch, cutoff: float, max_images: int = 50000) -> PeriodicGraph:
    if not math.isfinite(cutoff) or cutoff <= 0:
        raise ValueError("Cutoff must be positive and finite")
    device = batch.positions.device
    all_src, all_dst, all_images, graph_ids = [], [], [], []
    with torch.no_grad():
        for graph_id in range(batch.num_graphs):
            start, end = int(batch.ptr[graph_id]), int(batch.ptr[graph_id + 1])
            cell = batch.cell[graph_id].detach()
            inverse = torch.linalg.inv(cell)
            frac = batch.positions[start:end].detach() @ inverse
            wrap = torch.where(batch.pbc[graph_id], torch.floor(frac), 0).long()
            wrapped = batch.positions[start:end].detach() - wrap.to(cell.dtype) @ cell
            bounds = torch.ceil(cutoff * torch.linalg.vector_norm(inverse, dim=0)).long() + 1
            bounds = torch.where(batch.pbc[graph_id], bounds, 0).tolist()
            image_count = math.prod(2 * bound + 1 for bound in bounds)
            if image_count > max_images:
                raise ValueError(f"Cell requires {image_count} periodic images; check cell/cutoff")
            n = end - start
            candidates = torch.cartesian_prod(*(torch.arange(-b, b + 1, device=device)
                                                for b in bounds))
            pairs = wrapped[:, None, :] - wrapped[None, :, :]
            chunk_size = max(1, 1_000_000 // (n * n))
            diagonal = torch.eye(n, dtype=torch.bool, device=device)
            for image in candidates.split(chunk_size):
                shifts = image.to(cell.dtype) @ cell
                vectors = pairs[None] + shifts[:, None, None, :]
                distance = torch.linalg.vector_norm(vectors, dim=-1)
                self_pair = diagonal[None] & (image == 0).all(dim=-1)[:, None, None]
                if bool(((distance < 1e-8) & ~self_pair).any()):
                    raise ValueError("Coincident atoms/images in input geometry")
                selected = (distance < cutoff) & ~self_pair
                image_index, src, dst = torch.where(selected)
                if len(src):
                    all_src.append(src + start)
                    all_dst.append(dst + start)
                    all_images.append(image[image_index] - wrap[src] + wrap[dst])
                    graph_ids.append(torch.full_like(src, graph_id))
    src = torch.cat(all_src) if all_src else torch.empty(0, dtype=torch.long, device=device)
    dst = torch.cat(all_dst) if all_dst else src.clone()
    images = torch.cat(all_images) if all_images else src.new_empty((0, 3))
    edge_batch = torch.cat(graph_ids) if graph_ids else src.clone()
    shift = torch.einsum("ei,eij->ej", images.to(batch.cell.dtype), batch.cell[edge_batch])
    vectors = batch.positions[src] + shift - batch.positions[dst]
    distances = torch.linalg.vector_norm(vectors, dim=-1)
    return PeriodicGraph(src, dst, images, edge_batch, vectors, distances,
                         smooth_cutoff(distances, cutoff), cutoff)


def strain_batch(batch: StructureBatch, strain: Tensor) -> StructureBatch:
    if strain.shape != batch.cell.shape:
        raise ValueError("strain must be [B,3,3]")
    transform = torch.eye(3, device=strain.device, dtype=strain.dtype) + strain
    positions = torch.einsum("ni,nji->nj", batch.positions, transform[batch.batch])
    cell = batch.cell @ transform.transpose(-1, -2)
    return batch.with_geometry(positions, cell)


def gaussian_basis(distance: Tensor, count: int, maximum: float, minimum: float = 0) -> Tensor:
    centers = torch.linspace(minimum, maximum, count, device=distance.device, dtype=distance.dtype)
    width = (maximum - minimum) / max(count - 1, 1)
    return torch.exp(-((distance[..., None] - centers) / width).square())
