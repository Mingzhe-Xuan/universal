import importlib
import copy
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


def test_backbone_eval_policy_is_explicit_bool_and_default_compatible():
    from universal_gnn.readouts.configuration import normalize_optimization
    base={"task":{"kind":"supervised","property":"bandgap"}}
    assert normalize_optimization(base)==normalize_optimization({**base,"optimization":{"backbone_eval":False}})
    assert normalize_optimization({**base,"optimization":{"backbone_eval":True}})["backbone_eval"]
    with pytest.raises(ValueError,match="bool"):
        normalize_optimization({**base,"optimization":{"backbone_eval":1}})


def test_capability_upgrade_does_not_allow_shape_or_capability_downgrade():
    from universal_gnn.engine.optimization import compare_architectures
    old=FeatureSpec(8,"8x0e","invariant","scalar","invariant",
                    {"positions":True,"strain":False,"mixed":False}).to_dict()
    new=copy.deepcopy(old);new["gradients"].update(strain=True,mixed=True)
    compatible,updates=compare_architectures(old,new)
    assert compatible and len(updates)==2 and not old["gradients"]["strain"]
    assert not compare_architectures(new,old)[0]
    new["feature_dim"]=9
    assert not compare_architectures(old,new)[0]


def test_capability_upgrade_checkpoint_replay(monkeypatch,tmp_path):
    from test_prediction_components import ControlledBackbone,config,batch
    from universal_gnn.engine.optimization import component_checkpoint
    monkeypatch.setattr(training,"make_backbone",lambda *a,**kw:ControlledBackbone())
    c=config();c["dtype"]="float64"
    model=training.build_model(c).double().eval()
    def unverified(value):
        if isinstance(value,dict):
            if "gradients" in value:value["gradients"].update(strain=False,mixed=False)
            for child in value.values():unverified(child)
        elif isinstance(value,list):
            for child in value:unverified(child)
    unverified(model.prediction_descriptor)
    expected=model(batch())
    path=tmp_path/"previous.pt"
    torch.save({"format_version":2,"config":c,"state_dict":model.state_dict(),
                "components":component_checkpoint(model)},path)
    restored=training.load_checkpoint(path)
    torch.testing.assert_close(restored(batch()),expected,rtol=0,atol=0)
    assert restored._checkpoint_capability_updates


def test_trainable_eval_backbone_preserves_buffers_and_trains_force_gradients(monkeypatch):
    from test_prediction_components import ControlledBackbone,config,batch
    from universal_gnn.engine.optimization import make_optimizer
    def factory(*a,**kw):
        backbone=ControlledBackbone();backbone.forcefield_requires_eval_training=True
        return backbone
    monkeypatch.setattr(training,"make_backbone",factory)
    c=config("node_mlp",task={"kind":"forcefield","supervised_outputs":["forces"]})
    c["prediction"]["readout"]["pooling"]="sum"
    with pytest.raises(ValueError,match="backbone_eval"):training.build_model(c)
    c["optimization"]={"train_backbone":True,"backbone_eval":True}
    model=training.build_model(c).double().train()
    assert not model.backbone.training and model.energy_model.readout.training
    assert all(p.requires_grad for p in model.backbone.parameters())
    buffers={k:v.clone() for k,v in model.backbone.named_buffers()}
    parameters={k:v.clone() for k,v in model.backbone.named_parameters()}
    optimizer=make_optimizer(model,c)
    model(batch(),create_graph=True)["forces"].square().sum().backward()
    assert any(p.grad is not None and p.grad.norm()>0 for p in model.backbone.parameters())
    optimizer.step()
    for key,value in buffers.items():torch.testing.assert_close(dict(model.backbone.named_buffers())[key],value,rtol=0,atol=0)
    assert any(not torch.equal(p,parameters[key]) for key,p in model.backbone.named_parameters())
