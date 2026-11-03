import copy

import pytest
import torch
from torch import nn

from universal_gnn.contracts import NativeFeatures, NativeTaskContract
from universal_gnn.contracts.schema import validate_config
from universal_gnn.data.geometry import scatter_mean, scatter_sum
from universal_gnn.engine import training
from universal_gnn.engine.component_views import native_component_views
from universal_gnn.engine.optimization import components,make_optimizer,FrozenStateGuard
from universal_gnn.readouts.configuration import normalize_prediction
from test_prediction_components import batch


class OriginalHead(nn.Module):
    def __init__(self,width):
        super().__init__()
        self.network=nn.Sequential(nn.Linear(width,width),nn.SiLU(),nn.Linear(width,1))
        self.register_buffer("calls",torch.zeros((),dtype=torch.long))
    def forward(self,value):
        if self.training:self.calls.add_(1)
        return self.network(value)


class OriginalToy(nn.Module):
    kind,irreps,cutoff,context_dim="invariant","4x0e",2.,0
    gradient_capabilities={"positions":True,"strain":True,"mixed":True}
    def __init__(self,native_property="bandgap",context_dim=0):
        super().__init__();self.native_property=native_property;self.context_dim=context_dim
        self.model=nn.Module()
        self.model.body=nn.Sequential(nn.Linear(1,4),nn.BatchNorm1d(4),nn.SiLU(),nn.Dropout(.3))
        self.model.head=OriginalHead(4)
    def encode(self,b,context=None):
        centers=scatter_mean(b.positions,b.batch,b.num_graphs)[b.batch]
        features=self.model.body((b.positions-centers).square().sum(-1,keepdim=True))
        return NativeFeatures(features,self.irreps,self.kind,b.batch,b.ptr,b)
    def native_task_contract(self):
        energy=self.native_property=="total_energy"
        return NativeTaskContract(self.native_property,("model.head",),"eV",reduction="sum" if energy else "mean",
                                  forcefield=energy,normalization={"mean":3.,"std":2.})
    def native_prediction(self,b,contract):
        f=self.encode(b)
        if contract.forcefield:return scatter_sum(self.model.head(f.nodes),b.batch,b.num_graphs)*2+3
        return self.model.head(scatter_mean(f.nodes,b.batch,b.num_graphs))*2+3


@pytest.fixture
def factory(monkeypatch):
    monkeypatch.setattr(training,"make_backbone",lambda name,**kwargs:OriginalToy(**kwargs))


def config(mode="native"):
    c={"backbone":{"name":"toy_native"},"dataset":{"path":"unused"},
       "task":{"kind":"supervised","property":"bandgap"},"dtype":"float64",
       "prediction":{"version":1,"head_mode":mode}}
    if mode=="reset":c["prediction"]["readout"]={"name":"graph_mlp","hidden_features":[7],"pooling":"mean"}
    return c


@pytest.mark.parametrize("change",[
    {"head_mode":"unknown"},{"head_mode":False},
    {"readout":{"name":"linear"}},{"adapter":{"name":"none"}},
])
def test_native_conflicting_or_unknown_settings(change):
    c=config();c["prediction"].update(change)
    with pytest.raises(ValueError):validate_config(c)


def test_reset_default_normalizes_identically():
    c=config("reset");old=copy.deepcopy(c);old["prediction"].pop("head_mode")
    assert normalize_prediction(c)==normalize_prediction(old)


def test_native_original_values_and_reset_only_changes_task_head(factory):
    torch.manual_seed(123);native=training.build_model(config()).double().eval()
    torch.manual_seed(123);reset=training.build_model(config("reset")).double().eval()
    for key,value in native.backbone.state_dict().items():
        torch.testing.assert_close(reset.backbone.state_dict()[key],value,rtol=0,atol=0)
    expected=native.backbone.native_prediction(batch(),native.native_contract)
    torch.testing.assert_close(native(batch()),expected,rtol=0,atol=0)
    assert not torch.allclose(native(batch()),reset(batch()))
    assert all(key.startswith("backbone.") for key in native.state_dict())
    assert not any(key.startswith("readout.") for key in native.state_dict())
    assert native.readout.owner.model.head is native.backbone.model.head
    assert "head_mode" not in reset.prediction_descriptor


def test_native_contract_rejects_changed_task_or_force_semantics(factory):
    c=config();c["task"]["property"]="formation_energy"
    with pytest.raises(ValueError,match="original task"):training.build_model(c)
    c=config();c["task"]["unit"]="GPa"
    with pytest.raises(ValueError,match="original task"):training.build_model(c)
    c=config();c["task"]={"kind":"forcefield","supervised_outputs":["forces"]}
    with pytest.raises(ValueError,match="original task|forcefield"):training.build_model(c)
    c=config();c["backbone"]["context_dim"]=1
    with pytest.raises(ValueError,match="conditioning"):training.build_model(c)
    c=config();c["optimization"]={"train_adapter":False}
    with pytest.raises(ValueError,match="independent adapter"):training.build_model(c)


def test_shared_native_parameters_are_rejected():
    module=nn.Module();module.body=nn.Linear(2,2);module.head=module.body
    with pytest.raises(ValueError,match="shares parameters"):
        native_component_views(module,("head",))


@pytest.mark.parametrize("frozen",["backbone","readout"])
def test_native_independent_freeze_buffers_modes_and_optimizer(factory,frozen):
    c=config();c["optimization"]={"train_"+frozen:False}
    m=training.build_model(c).double().train();parts=components(m)
    guard=FrozenStateGuard(m)
    before={name:{k:v.clone() for k,v in view.state_dict().items()} for name,view in parts.items()}
    optimizer=make_optimizer(m,c)
    ids=[id(p) for group in optimizer.param_groups for p in group["params"]]
    assert len(ids)==len(set(ids)) and set(ids)=={id(p) for p in m.parameters() if p.requires_grad}
    assert all(not x.training for x in parts[frozen].modules())
    optimizer.zero_grad();m(batch()).square().mean().backward();optimizer.step();guard.verify()
    for key,value in before[frozen].items():torch.testing.assert_close(parts[frozen].state_dict()[key],value,rtol=0,atol=0)
    assert all(p.grad is None for p in parts[frozen].parameters())
    other="readout" if frozen=="backbone" else "backbone"
    assert any(p.grad is not None and p.grad.norm()>0 for p in parts[other].parameters())
    assert any(not torch.equal(value,parts[other].state_dict()[key]) for key,value in before[other].items())


def test_native_frozen_body_force_head_mixed_gradient(factory):
    c=config();c["backbone"]["native_property"]="total_energy"
    c["task"]={"kind":"forcefield","supervised_outputs":["forces"]}
    c["optimization"]={"train_backbone":False,"train_readout":True}
    m=training.build_model(c).double().train()
    m(batch(),create_graph=True)["forces"].square().sum().backward()
    assert all(p.grad is None for p in components(m)["backbone"].parameters())
    assert any(p.grad is not None and p.grad.norm()>0 for p in components(m)["readout"].parameters())


@pytest.mark.parametrize("source_mode,target_mode",[("native","reset"),("reset","native")])
def test_body_warm_start_cross_head_mode_is_strict_and_preserves_target_head(factory,tmp_path,source_mode,target_mode):
    from universal_gnn.engine.warm_start import initialize_components
    c=config(source_mode);m=training.build_model(c).double()
    with torch.no_grad():
        for p in m.backbone.model.body.parameters():p.add_(.2)
        for p in m.backbone.model.head.parameters():p.add_(.7)
    path=tmp_path/"source.pt"
    torch.save({"format_version":2,"config":c,"state_dict":m.state_dict()},path)
    target=training.build_model(config(target_mode)).double()
    before={k:v.clone() for k,v in target.backbone.model.head.state_dict().items()}
    result=initialize_components(target,path,["backbone"])
    for key,value in m.backbone.model.body.state_dict().items():
        torch.testing.assert_close(target.backbone.model.body.state_dict()[key],value,rtol=0,atol=0)
    for key,value in before.items():torch.testing.assert_close(target.backbone.model.head.state_dict()[key],value,rtol=0,atol=0)
    assert result["native_head_state_excluded_from_backbone"] and result["optimizer_rebuilt"]


def test_native_checkpoint_continuation_and_mode_switch_refusal(factory,tmp_path):
    import json
    from universal_gnn.engine.runtime import check_model_config
    b=batch();records=[]
    for i in range(b.num_graphs):
        start,end=int(b.ptr[i]),int(b.ptr[i+1])
        records.append({"id":str(i),"numbers":b.numbers[start:end].tolist(),"positions":b.positions[start:end].tolist(),
                        "cell":b.cell[i].tolist(),"pbc":b.pbc[i].tolist(),"targets":{"bandgap":1.+i}})
    path=tmp_path/"data.json";path.write_text(json.dumps(records))
    c=config();c.update(epochs=3,batch_size=1,checkpoint_every=1)
    c["dataset"]["path"]=str(path);c["optimization"]={"train_backbone":False,"train_readout":True}
    report=training.run_training(c,tmp_path/"continuous")
    training.run_training({**c,"epochs":1},tmp_path/"first")
    training.run_training(c,tmp_path/"resumed",resume=tmp_path/"first/checkpoint.pt")
    a=training.load_checkpoint(tmp_path/"continuous/checkpoint.pt")
    d=training.load_checkpoint(tmp_path/"resumed/checkpoint.pt")
    for key,value in a.state_dict().items():torch.testing.assert_close(value,d.state_dict()[key],rtol=0,atol=0)
    assert max(report["backbone_gradient_norms"])==0 and report["components"]["readout"]["trainable_parameters"]>0
    with pytest.raises(ValueError,match="warm-start"):check_model_config(c,{**c,"prediction":config("reset")["prediction"]})
