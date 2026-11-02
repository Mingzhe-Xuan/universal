from dataclasses import replace
from pathlib import Path
import shutil

import pytest
import torch

from universal_gnn.contracts import (BaseGNN, GNNOutput, GraphBatch, GraphRecord,
                                    Structure, StructureBatch)
from universal_gnn.backbones.factory import make_backbone
from universal_gnn.backbones.standard import StandardBackbone
from universal_gnn.data.graphs import KNNGraphBuilder, RadiusGraphBuilder, StoredGraphBuilder
from universal_gnn.data.formats import save_structures
from universal_gnn.engine.training import load_checkpoint, run_training
from universal_gnn.tasks import ForceFieldModel


def molecules():
    first = Structure(torch.tensor([8, 1, 1]),
                      torch.tensor([[0., 0., 0.], [1., .2, .1], [-.3, 1.4, .4]], dtype=torch.float64),
                      torch.eye(3, dtype=torch.float64) * 10, torch.tensor([False] * 3), "analytic-1", {"bandgap": 1.2})
    second = Structure(torch.tensor([6]), torch.tensor([[0., 0., 0.]], dtype=torch.float64),
                       first.cell, first.pbc, "analytic-2", {"bandgap": 2.})
    return [first, second]


def test_knn_per_structure_clamp_isolated_and_invalid_edges():
    batch = StructureBatch.from_structures(molecules())
    graph = KNNGraphBuilder(k=8)(batch)
    assert graph.edge_index.shape == (2, 6) and graph.cell_shifts.shape == (6, 3)
    assert bool((graph.edge_index < 3).all())
    assert len(set(map(tuple, graph.edge_index.T.tolist()))) == 6
    assert torch.equal(graph.geometry.batch[graph.src], graph.geometry.batch[graph.dst])
    with pytest.raises(ValueError, match="pbc=false"):
        KNNGraphBuilder()(replace(batch, pbc=torch.ones_like(batch.pbc)))
    with pytest.raises(ValueError, match="different structures"):
        GraphBatch(batch, torch.tensor([[0], [3]]), torch.zeros(1, 3, dtype=torch.long)).validate()
    with pytest.raises(ValueError, match="int64"):
        GraphRecord(torch.tensor([[0.], [1.]])).validate(3, batch.pbc[0])


def test_stored_offsets_attributes_and_live_periodic_geometry():
    structures = molecules()
    for i, structure in enumerate(structures):
        single = StructureBatch.from_structures([structure])
        graph = KNNGraphBuilder(k=2)(single)
        structures[i] = replace(structure, graph=GraphRecord(graph.edge_index, graph.cell_shifts,
                                  torch.arange(len(structure.numbers) * 2).reshape(-1, 2).double()))
    batch = StructureBatch.from_structures(structures).to("cpu", torch.float32)
    graph = StoredGraphBuilder()(batch)
    assert graph.node_features.dtype == torch.float32 and graph.node_features.shape == (4, 2)
    model = make_backbone("gcn", width=8, layers=1, input_dim=2, graph_config={"name": "stored"})
    assert model.encode(batch).nodes.shape == (4, 8)
    periodic = replace(structures[0], numbers=torch.tensor([1, 1]), graph=None,
                       positions=torch.tensor([[.1, 0., 0.], [3.7, 0., 0.]], dtype=torch.float64),
                       cell=torch.eye(3, dtype=torch.float64) * 4, pbc=torch.ones(3, dtype=torch.bool))
    live = StructureBatch.from_structures([periodic])
    live.positions.requires_grad_()
    live.cell.requires_grad_()
    graph = RadiusGraphBuilder(1.)(live)
    dr, dl = torch.autograd.grad(graph.vectors.square().sum(), (live.positions, live.cell))
    assert dr.norm() > 0 and dl.norm() > 0
    with pytest.raises(ValueError, match="GraphRecord"):
        StoredGraphBuilder()(StructureBatch.from_structures(molecules()))


def test_gcn_force_finite_difference_and_second_derivatives():
    torch.manual_seed(19)
    backbone = make_backbone("gcn", width=8, layers=2, graph_config={"name": "knn", "k": 2})
    model = ForceFieldModel(backbone).double()
    batch = StructureBatch.from_structures(molecules()[:1])
    batch.positions.requires_grad_()
    result = model(batch, create_graph=True)
    delta = torch.zeros_like(batch.positions)
    delta[1, 0] = 1e-5
    numeric = -(model.energy_model(batch.with_geometry(batch.positions + delta, batch.cell))
                - model.energy_model(batch.with_geometry(batch.positions - delta, batch.cell))).squeeze() / 2e-5
    torch.testing.assert_close(result["forces"][1, 0], numeric, rtol=2e-5, atol=1e-9)
    hessian = torch.autograd.grad(result["forces"][1, 0], batch.positions, retain_graph=True)[0]
    gradients = torch.autograd.grad(result["forces"].square().sum(), list(model.backbone.parameters()), allow_unused=True)
    assert torch.isfinite(hessian).all() and hessian.norm() > 0
    assert sum(float(g.norm()) for g in gradients if g is not None) > 0


def test_custom_gnn_graph_checkpoint_and_code_fingerprint(tmp_path):
    source = Path(__file__).resolve().parents[1] / "examples/custom_knn_gcn"
    plugin = tmp_path / "custom"
    shutil.copytree(source, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    data = tmp_path / "molecules.json"
    save_structures(data, molecules())
    config = {"schema_version": 1, "structures": 2, "epochs": 3, "seed": 123,
              "backbone": {"name": "plugin:" + str(plugin), "width": 8, "layers": 1},
              "graph": {"name": "plugin:" + str(plugin), "k": 2},
              "dataset": {"path": str(data)}, "task": {"kind": "supervised", "property": "bandgap"}}
    report = run_training(config, tmp_path / "run")
    saved_path = tmp_path / "run/checkpoint.pt"
    saved = torch.load(saved_path, weights_only=True)
    assert report["passed"] and saved["contract_versions"]["graph"] == 1
    assert set(saved["extensions"]) == {"gnn", "graph"}
    reloaded = load_checkpoint(saved_path)
    batch = StructureBatch.from_structures(molecules())
    torch.testing.assert_close(reloaded(batch), torch.tensor(report["predictions"]["bandgap"]).double(), rtol=1e-6, atol=1e-7)
    batch.positions.requires_grad_()
    dr = torch.autograd.grad(reloaded(batch).sum(), batch.positions, create_graph=True)[0]
    d2r = torch.autograd.grad(dr.square().sum(), batch.positions)[0]
    assert torch.isfinite(d2r).all() and dr.norm() > 0 and d2r.norm() > 0
    saved["contract_versions"]["graph"] = 99
    torch.save(saved, tmp_path / "bad-version.pt")
    with pytest.raises(ValueError, match="graph schema"):
        load_checkpoint(tmp_path / "bad-version.pt")
    path = plugin / "model.py"
    path.write_text(path.read_text() + "\n# plugin source changed\n")
    with pytest.raises(ValueError, match="plugin code changed"):
        load_checkpoint(saved_path)


def test_standard_wrapper_rejects_bad_node_output():
    class BadGNN(BaseGNN):
        def __init__(self):
            super().__init__("2x0e", "invariant")

        def forward(self, graph, context=None):
            return GNNOutput(graph.geometry.positions.new_zeros(1, 2))

    batch = StructureBatch.from_structures(molecules())
    with pytest.raises(ValueError, match="dimensions"):
        StandardBackbone(BadGNN(), KNNGraphBuilder())(batch)
