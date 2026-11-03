import importlib
from types import SimpleNamespace

import pytest
import torch

from universal_gnn.contracts import FeatureSpec
from universal_gnn.engine import training


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.syspath_prepend("scripts")
    return importlib.import_module("validate_other_forcefields")


def test_candidate_capabilities_are_scoped_and_do_not_change_production(harness,monkeypatch):
    def factory(*a,**kw):
        return SimpleNamespace(gradient_capabilities={"positions":True,"strain":False,"mixed":False})
    monkeypatch.setattr(training,"make_backbone",factory)
    with pytest.raises(RuntimeError):
        with harness.candidate_capabilities():
            candidate=training.make_backbone("test")
            assert all(candidate.gradient_capabilities.values())
            assert not candidate.assessment_original_capabilities["mixed"]
            raise RuntimeError("test exception cleanup")
    assert training.make_backbone is factory and not training.make_backbone().gradient_capabilities["mixed"]


def test_assessment_configuration_keeps_force_only_and_explicit_representation(harness):
    scalar=FeatureSpec(8,"8x0e","invariant","scalar","invariant")
    vector=FeatureSpec(3,"1x1o","equivariant","e3nn/component","O3")
    for spec in (scalar,vector):
        c=harness.configuration("nequip","real.json",spec,frozen=True,epochs=4)
        assert c["task"]["supervised_outputs"]==["forces"]
        head=c["prediction"]["readout"]
        assert head["name"]=="node_mlp" and head["pooling"]=="sum"
        assert ("feature_processing" in head)==(spec is vector)
        assert not c["optimization"]["train_backbone"]


def test_native_reference_uses_existing_force_label_without_mutating_training(harness):
    c={"backbone":{"name":"cgcnn"},"task":{"kind":"forcefield","supervised_outputs":["forces"]}}
    r=harness.reference_configuration(c)
    assert r["task"]["property"]=="forces" and "property" not in c["task"]
    c["backbone"]["name"]="nequip"
    assert harness.reference_configuration(c)==c


def test_discrete_periodic_topology_retains_live_geometry_and_mixed_derivatives():
    from universal_gnn.backbones.official.base import attach_periodic_topology
    pos=torch.tensor([[.2,.3,.4],[1.1,.6,.8]],dtype=torch.float64,requires_grad=True)
    cell=(torch.eye(3,dtype=torch.float64)*3).requires_grad_()
    data=SimpleNamespace(pos=pos,cell=cell)
    def original_builder(data,radius,neighbors):
        assert not torch.is_grad_enabled() and data.pos is pos and data.cell is cell
        repeat=torch.ceil(data.cell[0,0])
        assert torch.arange(-repeat,repeat+1).numel()==7
        return torch.tensor([[0],[1]]),torch.tensor([[1.,0.,0.]],dtype=cell.dtype),torch.tensor([1])
    assert attach_periodic_topology(data,original_builder,4.,12) is data
    parameter=torch.tensor(.7,dtype=pos.dtype,requires_grad=True)
    vector=data.pos[0]-data.pos[1]+data.cell_offsets[0]@data.cell
    energy=parameter*vector.square().sum()
    gp,gc=torch.autograd.grad(energy,(pos,cell),create_graph=True)
    mixed=torch.autograd.grad(gp.square().sum()+gc.square().sum(),parameter)[0]
    assert gp.norm()>0 and gc.norm()>0 and mixed.isfinite() and mixed.abs()>0
