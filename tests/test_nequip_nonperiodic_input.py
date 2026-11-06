"""Actual NequIP nonperiodic input and derivative regressions; execute in Slurm."""

from dataclasses import replace
import json
import os
from pathlib import Path

import pytest
import torch

from universal_gnn.backbones.official.nequip import _respect_nonperiodic_axes
from universal_gnn.benchmarks.molecular.contracts import selected_group
from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.contracts import StructureBatch
from universal_gnn.engine.runtime import save_training_checkpoint
from universal_gnn.engine.training import build_model,dataset,load_checkpoint


pytestmark=pytest.mark.skipif(not os.environ.get("SLURM_JOB_ID"),reason="NequIP numerical checks require Slurm")
DEVICE=os.environ.get("UGNN_MOLECULAR_TEST_DEVICE","cpu")


def config(dtype):
    result=selected_group("nequip")["reference_config"]
    result.update(dtype="float64" if dtype==torch.float64 else "float32",device=DEVICE)
    return result


@pytest.fixture(scope="module")
def actual_examples():
    structures=dataset(config(torch.float64))
    assert len(structures)==900 and len(structures.source)==100000
    return [structures[0],structures[450],structures[899]]


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
def test_only_nonperiodic_components_change_and_allperiodic_is_same_tensor(dtype):
    original=torch.tensor([[float("nan"),2.,-3.],[4.,5.,float("nan")]],device=DEVICE,dtype=dtype)
    data={"edge_cell_shift":original}
    assert _respect_nonperiodic_axes(data,torch.ones(3,device=DEVICE,dtype=torch.bool)) is data
    assert data["edge_cell_shift"] is original
    result=_respect_nonperiodic_axes(dict(data),torch.tensor([False,True,False],device=DEVICE))
    torch.testing.assert_close(result["edge_cell_shift"],original.new_tensor([[0.,2.,0.],[0.,5.,0.]]),rtol=0,atol=0)


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
@pytest.mark.parametrize("pbc",[(False,False,False),(True,False,True),(True,True,True)])
def test_actual_original_native_fields_and_periodic_components_preserved(dtype,pbc,actual_examples,monkeypatch):
    import universal_gnn.backbones.official.nequip as adapter
    from nequip.data import _nl
    torch.manual_seed(123)
    model=build_model(config(dtype)).to(device=DEVICE,dtype=dtype).eval()
    for structure in actual_examples:
        if any(pbc):
            structure=replace(structure,cell=torch.eye(3,dtype=torch.float64)*8.,pbc=torch.tensor(pbc))
        batch=StructureBatch.from_structures([structure]).to(DEVICE,dtype)
        current=model.backbone.native_input(batch)
        with monkeypatch.context() as context:
            context.setattr(adapter,"_respect_nonperiodic_axes",lambda data,pbc:data)
            original=model.backbone.native_input(batch)
        assert set(current)==set(original)
        for key in current:
            if key!="edge_cell_shift":torch.testing.assert_close(current[key],original[key],rtol=0,atol=0)
        mask=batch.pbc[0]
        torch.testing.assert_close(current["edge_cell_shift"][:,mask],original["edge_cell_shift"][:,mask],rtol=0,atol=0)
        assert not bool(current["edge_cell_shift"][:,~mask].any())
        if not any(pbc):
            index=current["edge_index"]
            direct=batch.positions[index[1]]-batch.positions[index[0]]
            vectors=current["pos"][index[1]]-current["pos"][index[0]]+current["edge_cell_shift"]@current["cell"].reshape(3,3)
            torch.testing.assert_close(vectors,direct,rtol=0,atol=0)
            ase=_nl.neighbor_list_and_relative_vec(batch.positions.detach().cpu(),model.backbone.cutoff,
                cell=batch.cell[0].detach().cpu(),pbc=(False,False,False),NL="ase")
            assert set(map(tuple,index.cpu().T.tolist()))==set(map(tuple,ase[0].T.tolist()))
            assert index.shape[1]==72 and not bool((index[0]==index[1]).any())


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
def test_forcefield_original_finite_differences_geometry_and_mixed_parameter_gradients(dtype,actual_examples):
    settings=config(dtype);torch.manual_seed(123)
    model=build_model(settings).to(device=DEVICE,dtype=dtype).eval()
    report=validate_derivatives(model,actual_examples[:2],settings)
    assert report["passed"] and all(row["passed"] for row in report["checks"].values() if row["required"])
    assert all(value>1e-10 for value in report["mixed_parameter_gradient_norms"].values())


@pytest.mark.parametrize("dtype",[torch.float32,torch.float64])
def test_force_only_step_updates_backbone_readout_and_checkpoint_reload(dtype,actual_examples,tmp_path):
    settings=config(dtype);torch.manual_seed(123)
    model=build_model(settings).to(device=DEVICE,dtype=dtype).train()
    batch=StructureBatch.from_structures(actual_examples[:2]).to(DEVICE,dtype)
    modules=[model.backbone,model.energy_model.readout]
    before=[{key:value.detach().clone() for key,value in module.state_dict().items()} for module in modules]
    optimizer=torch.optim.Adam(model.parameters(),lr=3e-4);optimizer.zero_grad(set_to_none=True)
    loss=model(batch,create_graph=True)["forces"].square().mean();assert torch.isfinite(loss);loss.backward()
    for module in modules:
        values=[p.grad for p in module.parameters() if p.grad is not None]
        assert values and all(torch.isfinite(v).all() for v in values) and sum(float(v.norm()) for v in values)>1e-10
    optimizer.step()
    for module,previous in zip(modules,before):assert any(not torch.equal(value,module.state_dict()[key]) for key,value in previous.items())
    model.eval();expected=model(batch,create_graph=False)
    path=tmp_path/"nequip-nonperiodic.pt";save_training_checkpoint(path,model,None,settings,{},None)
    loaded=load_checkpoint(path,device=DEVICE)
    assert all(torch.equal(value,loaded.state_dict()[key]) for key,value in model.state_dict().items())
    actual=loaded(batch,create_graph=False)
    for key in ["total_energy","forces","stress"]:torch.testing.assert_close(actual[key],expected[key],rtol=3e-5,atol=3e-6)
