"""Actual plugin constructor/forcefield derivatives and checkpoint checks; Slurm only."""

import json
import os
from pathlib import Path
import subprocess

import pytest
import torch

from universal_gnn.backbones.standard import StandardBackbone
from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.contracts import StructureBatch
from universal_gnn.contracts.plugins import load_plugin
from universal_gnn.data.indexed import JSONLStructures
from universal_gnn.engine.runtime import save_training_checkpoint
from universal_gnn.engine.training import build_model, load_checkpoint


pytestmark=pytest.mark.skipif(not os.environ.get("SLURM_JOB_ID"),reason="Molecular numerical checks require Slurm")
DEVICE=os.environ.get("UGNN_MOLECULAR_TEST_DEVICE","cpu")


@pytest.fixture(scope="module")
def actual_training_examples():
    root=Path("data/arxiv-v1/rmd17-ethanol-prepared-4f30bea")
    manifest=json.loads((root/"split.json").read_bytes())
    source=JSONLStructures(root/"structures.jsonl",dtype=torch.float64)
    assert source.sha256=="71747e9ce58fd67aba9b87ef367036915a1ba9348c6ce74968a63691b6def4db" and len(source)==100000
    train=manifest["partitions"]["train"];assert len(train)==900
    return [source[train[i]] for i in [0,len(train)//2,len(train)-1]]


def config(dtype):
    return dict(schema_version=1,seed=123,dtype="float64" if dtype==torch.float64 else "float32",device=DEVICE,
        backbone=dict(name="plugin:examples/custom_knn_gcn",implementation="legacy",width=16,layers=2,cutoff=6.),
        graph=dict(name="plugin:examples/custom_knn_gcn",k=2),
        dataset=dict(path="data/arxiv-v1/rmd17-ethanol-prepared-4f30bea/structures.jsonl"),
        task=dict(kind="forcefield",supervised_outputs=["total_energy","forces"]),
        prediction=dict(version=1,head_mode="reset",readout=dict(name="node_mlp",pooling="sum",hidden_features=[128,64],activation="silu")),
        optimization=dict(train_backbone=True,train_readout=True))


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
@pytest.mark.parametrize("context_dim",[0,3])
def test_metadata_only_update_preserves_original_constructor_rng_state_and_direct_features(dtype,context_dim,actual_training_examples):
    old_source=subprocess.check_output(["git","show","1e19447:examples/custom_knn_gcn/model.py"],text=True)
    namespace={"__name__":"original_molecular_gcn_reference"}
    exec(compile(old_source,"<original1e19447MolecularGCN>","exec"),namespace)
    module=load_plugin("examples/custom_knn_gcn")
    torch.manual_seed(123)
    original=namespace["MolecularGCN"](width=16,layers=2,context_dim=context_dim)
    original_rng=torch.random.get_rng_state().clone()
    torch.manual_seed(123)
    current=module.build_gnn(width=16,layers=2,context_dim=context_dim)
    assert torch.equal(torch.random.get_rng_state(),original_rng)
    wrapped=StandardBackbone(current,module.build_graph_builder(k=2),cutoff=6.)
    assert set(original.state_dict())==set(wrapped.gnn.state_dict())
    assert all(torch.equal(value,wrapped.gnn.state_dict()[key]) for key,value in original.state_dict().items())
    assert wrapped.gnn.gradient_capabilities==dict(positions=True,strain=True,mixed=True)
    assert not original.gradient_capabilities
    original=original.to(device=DEVICE,dtype=dtype).eval();wrapped=wrapped.to(device=DEVICE,dtype=dtype).eval()
    batch=StructureBatch.from_structures(actual_training_examples[:2]).to(DEVICE,dtype)
    graph=wrapped.graph_builder(batch)
    context=torch.linspace(-.2,.3,batch.num_graphs*context_dim,device=DEVICE,dtype=dtype).reshape(batch.num_graphs,context_dim) if context_dim else None
    expected=original(graph,context).nodes
    actual=wrapped(batch,context).nodes
    torch.testing.assert_close(actual,expected,rtol=0,atol=0)
    assert next(wrapped.parameters()).device.type==torch.device(DEVICE).type


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
def test_declared_forcefield_capabilities_pass_original_finite_difference_geometry_and_mixed_gradient_policy(dtype,actual_training_examples):
    settings=config(dtype);torch.manual_seed(123)
    model=build_model(settings).to(device=DEVICE,dtype=dtype).eval()
    report=validate_derivatives(model,actual_training_examples[:2],settings)
    assert report["passed"] and report["dtype"]==str(dtype) and report["device"].startswith(DEVICE)
    assert report["checks"]["forces_finite_difference"]["required"]
    assert report["checks"]["stress_finite_difference"]["required"]
    assert all(row["passed"] for row in report["checks"].values() if row["required"])
    assert all(value>1e-10 for value in report["mixed_parameter_gradient_norms"].values())


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
def test_force_only_diagnostic_updates_body_readout_and_standard_checkpoint_reloads(dtype,actual_training_examples,tmp_path):
    settings=config(dtype);torch.manual_seed(123)
    model=build_model(settings).to(device=DEVICE,dtype=dtype).train()
    batch=StructureBatch.from_structures(actual_training_examples[:2]).to(DEVICE,dtype)
    before_body={k:v.detach().clone() for k,v in model.backbone.state_dict().items()}
    before_head={k:v.detach().clone() for k,v in model.energy_model.readout.state_dict().items()}
    optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
    optimizer.zero_grad(set_to_none=True)
    predictions=model(batch,create_graph=True)
    loss=predictions["forces"].square().mean();assert torch.isfinite(loss)
    loss.backward()
    for module in [model.backbone,model.energy_model.readout]:
        gradients=[p.grad for p in module.parameters() if p.grad is not None]
        assert gradients and all(torch.isfinite(g).all() for g in gradients)
        assert sum(float(g.norm()) for g in gradients)>1e-10
    optimizer.step()
    assert any(not torch.equal(v,model.backbone.state_dict()[k]) for k,v in before_body.items())
    assert any(not torch.equal(v,model.energy_model.readout.state_dict()[k]) for k,v in before_head.items())
    model.eval();expected=model(batch,create_graph=False)
    path=tmp_path/"plugin-standard.pt"
    save_training_checkpoint(path,model,None,settings,{},None)
    saved=torch.load(path,map_location="cpu",weights_only=True)
    assert saved["format_version"]==2 and saved["extensions"] and saved["components"]["version"]==1
    loaded=load_checkpoint(path,device=DEVICE)
    assert all(torch.equal(v,loaded.state_dict()[k]) for k,v in model.state_dict().items())
    actual=loaded(batch,create_graph=False)
    for key in ["total_energy","forces","stress"]:
        torch.testing.assert_close(actual[key],expected[key],rtol=3e-5,atol=3e-6)
