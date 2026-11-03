import copy
from dataclasses import replace
import json

import pytest
import torch
from torch import nn

from universal_gnn.contracts import NativeFeatures, Structure, StructureBatch, resolve_feature_spec
from universal_gnn.contracts.schema import validate_config
from universal_gnn.data.geometry import scatter_mean
from universal_gnn.engine import training
from universal_gnn.engine.optimization import components, component_audit, make_optimizer
from universal_gnn.readouts.factory import READOUTS, aggregate, register_readout


class ControlledBackbone(nn.Module):
    kind = "invariant"
    basis = "scalar"
    transformation = "invariant"
    gradient_capabilities = {"positions": True, "strain": True, "mixed": True}
    cutoff = 2.

    def __init__(self, width=8, *, declared=True):
        super().__init__()
        self.irreps = f"{width}x0e" if declared else None
        self.width = width
        self.network = nn.Sequential(nn.Linear(1, width), nn.BatchNorm1d(width), nn.SiLU(), nn.Dropout(.4))

    def encode(self, batch, context=None):
        centers = scatter_mean(batch.positions, batch.batch, batch.num_graphs)[batch.batch]
        radial = (batch.positions - centers).square().sum(-1, keepdim=True)
        return NativeFeatures(self.network(radial), self.irreps, self.kind, batch.batch, batch.ptr, batch,
                              batch.positions.new_ones(batch.num_graphs, 2), {"source": "analytic controlled module"})


def batch():
    xyz = [[.1,.2,.3],[.8,.4,.5],[.3,.9,.6],[.5,.3,1.1]]
    a = Structure(torch.tensor([1]*4), torch.tensor(xyz, dtype=torch.float64), torch.eye(3).double()*5,
                  torch.tensor([False]*3), "a")
    b = replace(a, numbers=a.numbers[:3], positions=a.positions[:3]*1.3, identifier="b")
    return StructureBatch.from_structures([a, b])


def config(name="graph_mlp", *, width=8, task=None):
    head = {"name": name, "pooling": "mean"}
    if name in {"graph_mlp", "node_mlp"}:
        head["hidden_features"] = [7]
    return {"backbone": {"name": "analytic", "width": width}, "dataset": {"path": "unused"},
            "task": task or {"kind": "supervised", "property": "bandgap"},
            "prediction": {"version": 1, "readout": head}}


@pytest.fixture
def factory(monkeypatch):
    def make(name, **options):
        assert "feature_dim" not in options
        return ControlledBackbone(options.get("width", 8), declared=options.get("declared", True))
    monkeypatch.setattr(training, "make_backbone", make)


@pytest.mark.parametrize("width", [8, 256])
@pytest.mark.parametrize("name", ["linear", "graph_mlp", "node_mlp"])
def test_native_dimension_spectrum_and_batch_independence(factory, width, name):
    c = config(name, width=width, task={"kind": "supervised", "property": "spectrum", "channels": 5})
    model = training.build_model(c).double().eval()
    assert model.adapter is None and set(components(model)) == {"backbone", "readout"}
    assert model.readout.core.network[0].in_features == width
    b = batch()
    expected = model(b)
    assert expected.shape == (2,5)
    from universal_gnn.contracts import Structure
    singles = []
    for i in range(2):
        start,end = int(b.ptr[i]),int(b.ptr[i+1])
        s = Structure(b.numbers[start:end],b.positions[start:end],b.cell[i],b.pbc[i],str(i))
        singles.append(model(StructureBatch.from_structures([s])))
    torch.testing.assert_close(expected, torch.cat(singles), rtol=1e-10, atol=1e-10)
    assert not model.readout.descriptor["graph_features_used"]


def test_dimension_discovery_assertion_fallback_and_runtime_shape(factory):
    c = config(width=256)
    c["backbone"]["feature_dim"] = 256
    model = training.build_model(c)
    assert model.native_spec.dimension_assertion == 256 and model.native_spec.source == "model.irreps"
    c["backbone"]["feature_dim"] = 7
    with pytest.raises(ValueError, match="declaration conflict"):
        training.build_model(c)
    c["backbone"].update(declared=False, feature_dim=256)
    assert training.build_model(c).native_spec.source == "backbone.feature_dim"
    c["backbone"].pop("feature_dim")
    with pytest.raises(ValueError, match="dimension missing"):
        training.build_model(c)
    c["backbone"]["feature_dim"] = 255
    bad = training.build_model(c).double().eval()
    with pytest.raises(ValueError, match="declared F=255.*actual shape"):
        bad(batch())
    backbone = ControlledBackbone(3)
    backbone.irreps = "1x1o"
    backbone.kind = "equivariant"
    backbone.basis = None
    backbone.transformation = None
    with pytest.raises(ValueError, match="basis"):
        resolve_feature_spec(backbone)


def test_nonlinear_pooling_order_and_node_scope(factory):
    a = training.build_model(config("graph_mlp")).double().eval()
    b = training.build_model(config("node_mlp")).double().eval()
    b.load_state_dict(a.state_dict(), strict=True)
    assert not torch.allclose(a(batch()), b(batch()), atol=1e-12, rtol=1e-12)
    c = config("linear", task={"kind":"supervised","property":"atom_scalar"})
    c["prediction"]["readout"]["pooling"] = "none"
    assert training.build_model(c).double().eval()(batch()).shape == (7,1)


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"unknown": 1},
    {"readout": {"name": "absent"}},
    {"readout": {"name": "linear", "output_features": 7}},
    {"readout": {"name": "linear", "pooling": "none"}},
    {"readout": {"name": "graph_mlp", "hidden_features": []}},
    {"readout": {"name": "graph_mlp", "hidden_features": [True]}},
    {"readout": {"name": "graph_mlp", "hidden_features": [7], "activation":"relu"}},
    {"readout": {"name": "linear", "feature_processing": {"name":"equivariant","profile":"other","basis_version":2}}},
])
def test_bad_configuration_fails_before_factory(change):
    c = config();c["prediction"].update(change)
    with pytest.raises(ValueError):validate_config(c)


def test_route_optimization_and_generation_rejections():
    c = config();c["task"]["route"]="invariant_alignn"
    with pytest.raises(ValueError,match="conflicts"):validate_config(c)
    c=config();c["optimization"]={"train_adapter":False}
    with pytest.raises(ValueError,match="independent adapter"):validate_config(c)
    c=config();c["optimization"]={"train_backbone":1}
    with pytest.raises(ValueError,match="bool"):validate_config(c)
    c=config();c["task"]={"kind":"generation"}
    with pytest.raises(ValueError,match="generation"):validate_config(c)
    c={"task":{"kind":"generation"},"optimization":{}}
    with pytest.raises(ValueError,match="generation"):validate_config(c)


def test_registry_head_two_dimensions(factory):
    class RegisteredHead(nn.Module):
        def __init__(self, settings, features, spec):
            super().__init__();self.linear=nn.Linear(features.feature_dim,1)
        def forward(self, features):
            return self.linear(aggregate(features.nodes,features,"mean"))
    register_readout("test_registered",RegisteredHead)
    try:
        for width in (8,256):
            m=training.build_model(config("test_registered",width=width)).double().eval()
            assert m(batch()).shape==(2,1)
    finally:READOUTS.pop("test_registered")


@pytest.mark.parametrize("frozen", ["backbone", "readout"])
def test_freezing_parameters_buffers_modes_and_upstream_gradients(factory, frozen):
    class StochasticHead(nn.Module):
        def __init__(self, settings, features, spec):
            super().__init__();self.net=nn.Sequential(nn.BatchNorm1d(features.feature_dim),nn.Dropout(.5),nn.Linear(features.feature_dim,1))
        def forward(self, features):return self.net(aggregate(features.nodes,features,"mean"))
    register_readout("test_stochastic",StochasticHead)
    try:
        c=config("test_stochastic");c["optimization"]={"train_"+frozen:False}
        m=training.build_model(c).double();m.eval();m.train()
        modules=components(m);locked=modules[frozen]
        assert all(not child.training for child in locked.modules())
        before={k:v.clone() for k,v in locked.state_dict().items()}
        optimizer=make_optimizer(m,c)
        ids=[id(p) for group in optimizer.param_groups for p in group["params"]]
        assert len(ids)==len(set(ids)) and not ({id(p) for p in locked.parameters()} & set(ids))
        optimizer.zero_grad();(m(batch())-1).square().mean().backward();optimizer.step()
        assert all(p.grad is None for p in locked.parameters())
        for key,value in before.items():torch.testing.assert_close(value,locked.state_dict()[key],rtol=0,atol=0)
        assert any(p.grad is not None and p.grad.norm()>0 for name,mod in modules.items() if name!=frozen for p in mod.parameters())
    finally:READOUTS.pop("test_stochastic")


def test_force_only_frozen_backbone_head_gradients_and_finite_differences(factory):
    c=config("node_mlp",task={"kind":"forcefield","supervised_outputs":["forces"]})
    c["prediction"]["readout"]["pooling"]="sum"
    c["optimization"]={"train_backbone":False,"train_readout":True}
    m=training.build_model(c).double().train();b=batch()
    value=m(b,create_graph=True)
    value["forces"].square().sum().backward()
    assert all(p.grad is None for p in m.backbone.parameters())
    assert any(p.grad is not None and p.grad.norm()>0 for p in m.energy_model.readout.parameters())
    step=1e-5;delta=torch.zeros_like(b.positions);delta[0,0]=step
    numeric=-(m.energy_model(b.with_geometry(b.positions+delta,b.cell))[0]-m.energy_model(b.with_geometry(b.positions-delta,b.cell))[0])/(2*step)
    torch.testing.assert_close(value["forces"][0,0],numeric.squeeze(),rtol=2e-5,atol=1e-9)
    from universal_gnn.data.geometry import strain_batch
    strain = torch.zeros_like(b.cell);strain[0,0,0] = step
    numeric_stress = (m.energy_model(strain_batch(b,strain))[0] - m.energy_model(strain_batch(b,-strain))[0])/(2*step)
    numeric_stress = numeric_stress / torch.linalg.det(b.cell[0]).abs() * 160.21766208
    torch.testing.assert_close(value["stress"][0,0,0],numeric_stress.squeeze(),rtol=2e-5,atol=1e-9)
    torch.testing.assert_close(value["forces"][:4].sum(0),torch.zeros(3,dtype=torch.float64),rtol=0,atol=1e-12)
    c["prediction"]["readout"]["pooling"]="mean"
    with pytest.raises(ValueError,match="pooling"):training.build_model(c)


def test_all_frozen_inference_and_no_optimizer(factory):
    c=config();c["optimization"]={"train_backbone":False,"train_readout":False}
    m=training.build_model(c).double().eval()
    assert m(batch()).shape==(2,1)
    with pytest.raises(ValueError,match="no trainable"):make_optimizer(m,c)


def test_response_internal_processing_rotation_and_no_independent_adapter(factory):
    from universal_gnn.contracts.e3nn_compat import load_o3
    c=config("response",task={"kind":"supervised","property":"dielectric"})
    c["prediction"]["readout"]["feature_processing"]={"name":"equivariant","profile":"small_response","basis_version":2}
    m=training.build_model(c).double().eval();b=batch();q=load_o3().rand_matrix(dtype=torch.float64)
    original=m(b,create_graph=True)
    transformed=m(b.with_geometry(b.positions@q.T,b.cell@q.T),create_graph=True)
    torch.testing.assert_close(transformed,torch.einsum('ia,bac,jc->bij',q,original,q),rtol=2e-6,atol=2e-7)
    original.square().sum().backward()
    assert m.adapter is None and any(p.grad is not None and p.grad.norm()>0 for p in m.readout.parameters())
    assert m.readout.descriptor['transformation_guarantee']=='O3_cartesian'


def test_new_checkpoint_resume_warm_start_and_inference_policy(factory,tmp_path):
    from universal_gnn.engine.inference import run_inference
    path=tmp_path/'data.json'
    b=batch();records=[]
    for i in range(2):
        start,end=int(b.ptr[i]),int(b.ptr[i+1])
        records.append({'id':str(i),'numbers':b.numbers[start:end].tolist(),'positions':b.positions[start:end].tolist(),
                        'cell':b.cell[i].tolist(),'pbc':b.pbc[i].tolist(),'targets':{'bandgap':1.+.2*i}})
    path.write_text(json.dumps(records))
    c=config();c.update(epochs=3,batch_size=1,dtype='float64',checkpoint_every=1)
    c['dataset']['path']=str(path);c['optimization']={'train_backbone':False,'train_readout':True}
    training.run_training(c,tmp_path/'continuous')
    training.run_training({**c,'epochs':1},tmp_path/'prefix')
    training.run_training(c,tmp_path/'resumed',resume=tmp_path/'prefix/checkpoint.pt')
    a=training.load_checkpoint(tmp_path/'continuous/checkpoint.pt');d=training.load_checkpoint(tmp_path/'resumed/checkpoint.pt')
    for key,value in a.state_dict().items():torch.testing.assert_close(value,d.state_dict()[key],rtol=0,atol=0)
    saved=torch.load(tmp_path/'continuous/checkpoint.pt',weights_only=True)
    assert saved['components']['version']==1 and [v['name'] for v in saved['components']['optimizer_groups']]==['readout']
    changed=copy.deepcopy(c);changed['optimization']['train_backbone']=True
    with pytest.raises(ValueError,match='warm-start'):training.run_training(changed,tmp_path/'bad',resume=tmp_path/'prefix/checkpoint.pt')
    new=config('linear');new.update(epochs=1,dtype='float64');new['dataset']['path']=str(path)
    new['optimization']={'train_backbone':False,'train_readout':True}
    warm=training.run_training(new,tmp_path/'warm',warm_start=tmp_path/'continuous/checkpoint.pt')
    assert warm['initialization']['new_initialized_components']==['readout'] and warm['initialization']['optimizer_rebuilt']
    override=copy.deepcopy(saved['config']);override['optimization']={'train_backbone':False,'train_readout':False}
    result=run_inference(tmp_path/'continuous/checkpoint.pt',str(path),tmp_path/'predictions.json',config_override=override)
    assert result['components']['readout']['trainable_parameters']==0


def test_independent_adapter_and_internal_processing_ownership(factory):
    c = config("response", task={"kind":"supervised","property":"dielectric"})
    processing = {"name":"equivariant","profile":"small_response","basis_version":2}
    c["prediction"]["adapter"] = processing
    c["optimization"] = {"train_adapter":False,"train_backbone":False}
    m = training.build_model(c).double().train()
    assert set(components(m)) == {"backbone","adapter","readout"}
    assert m.adapter is not None and not m.adapter.training and m.readout.processing is None
    assert not ({id(p) for p in m.adapter.parameters()} &
                {id(p) for g in make_optimizer(m,c).param_groups for p in g["params"]})
    assert m(batch()).shape == (2,3,3)
    c["prediction"]["readout"]["feature_processing"] = processing
    with pytest.raises(ValueError,match="duplicate"):validate_config(c)


@pytest.mark.parametrize("corruption", ["dtype","batch","geometry","semantics","basis"])
def test_native_contract_runtime_mismatch(factory, corruption, monkeypatch):
    m = training.build_model(config()).double().eval()
    original = m.backbone.encode
    def wrong(b, context=None):
        f = original(b, context)
        changes = {"dtype":{"nodes":f.nodes.float()}, "batch":{"batch":f.batch.flip(0)},
                   "geometry":{"geometry":replace(b)}, "semantics":{"kind":"equivariant"},
                   "basis":{"metadata":{"basis":"unknown"}}}
        return replace(f, **changes[corruption])
    monkeypatch.setattr(m.backbone,"encode",wrong)
    with pytest.raises(ValueError):m(batch())


def test_frozen_guard_rejects_custom_eval_buffer_mutation(factory):
    from universal_gnn.engine.optimization import FrozenStateGuard
    c = config();c["optimization"] = {"train_backbone":False}
    m = training.build_model(c).double().eval()
    guard = FrozenStateGuard(m)
    m.backbone.network[1].running_mean.add_(1)
    with pytest.raises(RuntimeError,match="persistent buffers"):guard.verify()


def test_checkpoint_signature_and_scope_refusals(factory):
    from universal_gnn.engine.optimization import component_checkpoint, verify_component_checkpoint
    m = training.build_model(config())
    saved = {"components":component_checkpoint(m)}
    verify_component_checkpoint(saved,m,training=True)
    saved["components"]["architecture"]["prediction"]["native_spec"]["feature_dim"] += 1
    with pytest.raises(ValueError,match="signature"):verify_component_checkpoint(saved,m)
    c = config("graph_mlp", task={"kind":"supervised","property":"atom_scalar"})
    with pytest.raises(ValueError,match="scope"):validate_config(c)
    c = config("linear", task={"kind":"supervised","property":"dielectric"})
    with pytest.raises(ValueError,match="construction"):validate_config(c)
