import pytest
import torch

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.contracts import Structure, StructureBatch


def tiny_batch():
    cell = torch.eye(3, dtype=torch.float64) * 4
    structure = Structure(torch.tensor([14, 8]), torch.tensor([[.1, .2, .3], [1.2, .7, .5]],
                          dtype=torch.float64), cell, torch.ones(3, dtype=torch.bool), "analytic")
    return StructureBatch.from_structures([structure])


@pytest.mark.parametrize("name", ["cgcnn", "megnet", "alignn"])
def test_invariant_nodes_condition_and_input_gradient(name):
    torch.manual_seed(1)
    model = make_backbone(name, implementation="legacy", width=8, layers=1, cutoff=2., context_dim=2).double()
    batch = tiny_batch()
    batch.positions.requires_grad_()
    context = torch.tensor([[.3, -.2]], dtype=torch.float64, requires_grad=True)
    features = model.encode(batch, context)
    features.validate()
    assert features.nodes.shape[0] == 2
    assert features.kind == "invariant"
    weights = torch.linspace(.2, 1.3, features.nodes.numel(), dtype=torch.float64).reshape_as(features.nodes)
    objective = (features.nodes * weights).sum()
    dx, dc = torch.autograd.grad(objective, (batch.positions, context))
    assert torch.isfinite(dx).all() and float(dx.norm()) > 0
    assert torch.isfinite(dc).all() and float(dc.norm()) > 0
