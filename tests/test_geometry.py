import torch

from universal_gnn.contracts import Structure, StructureBatch
from universal_gnn.data.geometry import radius_graph, strain_batch


def example(cell=None, positions=None):
    cell = torch.eye(3, dtype=torch.float64) * 2 if cell is None else cell
    positions = torch.zeros((1, 3), dtype=torch.float64) if positions is None else positions
    return Structure(torch.full((len(positions),), 14, dtype=torch.long), positions, cell,
                     torch.ones(3, dtype=torch.bool), "analytic-Si")


def test_small_cell_contains_all_six_self_images():
    batch = StructureBatch.from_structures([example()])
    graph = radius_graph(batch, 2.1)
    assert len(graph.src) == 6
    torch.testing.assert_close(graph.distances, torch.full_like(graph.distances, 2))


def test_periodic_wrapping_and_batch_isolation():
    a = example()
    b = example(positions=torch.tensor([[6., -4., 2.]], dtype=torch.float64))
    graph = radius_graph(StructureBatch.from_structures([a, b]), 2.1)
    assert len(graph.src) == 12
    assert torch.equal(graph.src, graph.dst)
    assert len(torch.unique(graph.edge_batch)) == 2
    torch.testing.assert_close(graph.distances, torch.full_like(graph.distances, 2))


def test_cartesian_and_strain_finite_difference():
    s = example(cell=torch.tensor([[3., 0., 0.], [.4, 3.2, 0.], [.1, .3, 3.4]],
                                 dtype=torch.float64),
                positions=torch.tensor([[.2, .3, .1], [1.3, .5, .4]], dtype=torch.float64))
    batch = StructureBatch.from_structures([s])
    x = batch.positions.clone().requires_grad_()
    eta = torch.zeros_like(batch.cell, requires_grad=True)

    def energy(position, strain):
        graph = radius_graph(strain_batch(batch.with_geometry(position, batch.cell), strain), 2.0)
        return (graph.weights * graph.distances.square()).sum()

    value = energy(x, eta)
    dx, de = torch.autograd.grad(value, (x, eta), create_graph=True)
    step = 1e-5
    delta_x, delta_e = torch.zeros_like(x), torch.zeros_like(eta)
    delta_x[1, 0], delta_e[0, 0, 1] = step, step
    torch.testing.assert_close(dx[1, 0], (energy(x + delta_x, eta) - energy(x - delta_x, eta)) / (2 * step))
    torch.testing.assert_close(de[0, 0, 1], (energy(x, eta + delta_e) - energy(x, eta - delta_e)) / (2 * step))
    assert torch.isfinite(torch.autograd.grad(dx.square().sum() + de.square().sum(), x)[0]).all()


def test_rotation_and_empty_neighbors():
    batch = StructureBatch.from_structures([example()])
    assert len(radius_graph(batch, 1.0).src) == 0
    rotation = torch.tensor([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]], dtype=torch.float64)
    graph = radius_graph(batch, 2.1)
    rotated = radius_graph(batch.with_geometry(batch.positions @ rotation, batch.cell @ rotation), 2.1)
    torch.testing.assert_close(torch.sort(graph.distances).values, torch.sort(rotated.distances).values)
