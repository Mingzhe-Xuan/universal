"""Real published CGCNN/ALIGNN molecular input and derivative tests; Slurm only."""

import copy
from dataclasses import replace
import os

import numpy as np
import pytest
import torch

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.backbones.official.base import default_dtype
from universal_gnn.backbones.official.molecular.cgcnn import MolecularCGCNNInput, valid_neighbor_messages
from universal_gnn.backbones.official.molecular.geometry import nonperiodic_edges
from universal_gnn.contracts import Structure, StructureBatch
from universal_gnn.engine.optimization import configure_optimization
from universal_gnn.engine.training import load_checkpoint
from universal_gnn.readouts.configuration import normalize_prediction
from universal_gnn.tasks import ForceFieldModel


pytestmark = pytest.mark.skipif(not os.environ.get("SLURM_JOB_ID"), reason="Original molecular numeric tests require Slurm")
DEVICE = os.environ.get("UGNN_MOLECULAR_TEST_DEVICE", "cpu")


def structure(numbers, positions, name, dtype, device=DEVICE):
    return Structure(torch.tensor(numbers, dtype=torch.long, device=device),
        torch.tensor(positions, dtype=dtype, device=device), torch.eye(3, dtype=dtype, device=device),
        torch.zeros(3, dtype=torch.bool, device=device), name, {"bandgap": 1.})


def molecules(dtype, device=DEVICE):
    return [structure([8, 1, 1], [[0., 0., 0.], [.92, .1, 0.], [-.27, .87, .13]], "water", dtype, device),
            structure([6, 1, 1, 1, 1], [[0., 0., 0.], [.63, .63, .63], [-.63, -.63, .63],
                        [-.63, .63, -.63], [.63, -.63, -.63]], "methane", dtype, device),
            structure([2], [[2., -1., .7]], "isolated", dtype, device)]


def config(provider, initialization, dtype):
    return dict(schema_version=1, seed=123, dtype="float64" if dtype==torch.float64 else "float32",
        backbone=dict(name=provider, implementation="official", initialization=initialization, input_profile="molecular_radius"),
        dataset=dict(path="unused-molecular.jsonl"), task=dict(kind="forcefield", supervised_outputs=["total_energy", "forces"]),
        prediction=dict(version=1, readout=dict(name="node_mlp", pooling="sum", hidden_features=[16], activation="silu")),
        optimization=dict(train_backbone=True, train_readout=True, backbone_eval=provider=="cgcnn"))


@pytest.fixture(params=[(p, i, d) for p in ["cgcnn", "alignn"] for i in ["pretrained", "scratch"]
                       for d in [torch.float32, torch.float64]])
def backbone_case(request):
    provider, initialization, dtype = request.param
    torch.manual_seed(123)
    backbone = make_backbone(provider, initialization=initialization, input_profile="molecular_radius").to(device=DEVICE, dtype=dtype).eval()
    assert next(backbone.parameters()).device.type == torch.device(DEVICE).type
    return provider, initialization, dtype, backbone


def forcefield(case):
    provider, initialization, dtype, backbone = case
    settings = config(provider, initialization, dtype)
    prediction = normalize_prediction(settings, cutoff=backbone.cutoff)
    model = ForceFieldModel(backbone, prediction=prediction).to(device=DEVICE, dtype=dtype)
    configure_optimization(model, settings)
    return model.eval(), settings


def ase_edges(values, cutoff=6.):
    from ase.neighborlist import primitive_neighbor_list

    positions = values.positions.detach().cpu().numpy()
    src, dst = primitive_neighbor_list("ij", [False]*3, np.eye(3), positions, cutoff, self_interaction=False)
    order = sorted(range(len(src)), key=lambda k: (int(src[k]), float(np.linalg.norm(positions[dst[k]]-positions[src[k]])), int(dst[k])))
    return np.asarray(src[order], dtype=np.int64), np.asarray(dst[order], dtype=np.int64)


def cgcnn_reference_inputs(backbone, values):
    src, dst = ase_edges(values)
    xyz = values.positions.detach().cpu().numpy().astype(np.float64)
    degree = np.bincount(src, minlength=len(xyz))
    assert np.all(degree==degree[0])
    width = int(degree[0])
    distances = np.linalg.norm(xyz[dst]-xyz[src], axis=1).reshape(len(xyz), width)
    atoms = np.vstack([backbone.atom_initializer.get_atom_fea(int(z)) for z in values.numbers])
    parameter = next(backbone.parameters())
    return (torch.tensor(atoms, dtype=torch.float32).to(parameter),
            torch.as_tensor(backbone.gaussian.expand(distances), device=parameter.device, dtype=parameter.dtype),
            torch.tensor(dst.reshape(len(xyz), width), device=parameter.device),
            [torch.arange(len(xyz), device=parameter.device)])


def alignn_reference_inputs(backbone, values, monkeypatch):
    from alignn import torch_graph_builder as upstream
    from ase.data import chemical_symbols
    from jarvis.core.atoms import Atoms

    def independent_topology(positions, lattice, cutoff, **kwargs):
        src, dst = ase_edges(replace(values, positions=positions), cutoff)
        a = torch.tensor(src, device=positions.device)
        b = torch.tensor(dst, device=positions.device)
        return a, b, positions.new_zeros((len(a),3)), positions[b]-positions[a]

    monkeypatch.setattr(upstream, "torch_neighbor_list", independent_topology)
    atoms = Atoms(lattice_mat=np.eye(3), coords=values.positions.detach().cpu().numpy(), cartesian=True,
                  elements=[chemical_symbols[int(z)] for z in values.numbers])
    with default_dtype(values.positions.dtype):
        parent, line = upstream.build_pure_torch_graph(atoms=atoms, two_body_cutoff=6.,
            three_body_cutoff=backbone.configuration.get("three_body_cutoff",3.5), max_neighbors=None,
            atom_features=backbone.configuration.get("atom_features","cgcnn"), positions=values.positions,
            lattice=values.cell, device=values.positions.device)
    return parent, line, values.cell[None]


@pytest.mark.parametrize("provider", ["cgcnn", "alignn"])
@pytest.mark.parametrize("initialization", ["pretrained", "scratch"])
def test_original_constructor_parameter_buffer_layout_and_rng(provider, initialization):
    torch.manual_seed(123)
    original = make_backbone(provider, initialization=initialization)
    original_rng = torch.get_rng_state().clone()
    torch.manual_seed(123)
    adapted = make_backbone(provider, initialization=initialization, input_profile="molecular_radius")
    assert torch.equal(original_rng, torch.get_rng_state())
    assert type(original.model) is type(adapted.model)
    assert set(original.state_dict())==set(adapted.state_dict())
    assert all(torch.equal(value, adapted.state_dict()[key]) for key,value in original.state_dict().items())
    assert adapted.load_report["parameter_coverage"]==adapted.load_report["buffer_coverage"]==(1. if initialization=="pretrained" else 0.)
    assert adapted.load_report["state_layout_verified"]
    assert adapted.cutoff==6. and adapted.native_graph_provenance()["input_profile"]["all_neighbors"]
    assert "input_profile" not in original.load_report and "input_profile" not in original.official_artifact


def test_regular_neighbor_inputs_and_original_forward_reference(backbone_case, monkeypatch):
    provider, _, dtype, backbone = backbone_case
    values = molecules(dtype)[0]
    batch = StructureBatch.from_structures([values])
    original = copy.deepcopy(backbone.model).eval()
    features = []
    target = original.convs[-1] if provider=="cgcnn" else original.get_submodule(backbone.feature_path)
    handle = target.register_forward_hook(lambda module,args,out:features.append(out if provider=="cgcnn" else out[0]))
    try:
        if provider=="cgcnn":
            expected = original(*cgcnn_reference_inputs(backbone, values))
        else:
            expected = original(alignn_reference_inputs(backbone, values, monkeypatch))["out"]
    finally:
        handle.remove()
    predicted, nodes = backbone.native_forward(batch)
    if provider=="alignn":predicted=predicted["out"]
    torch.testing.assert_close(nodes, features[0], rtol=3e-5, atol=3e-6)
    torch.testing.assert_close(predicted, expected, rtol=3e-5, atol=3e-6)


def test_all_radius_neighbors_no_periodic_images_no_cross_graph_edges(backbone_case):
    provider, _, dtype, backbone = backbone_case
    dense = structure([1]*14, [[i*.1, (i%3)*.13, (i%2)*.17] for i in range(14)], "dense14", dtype)
    batch = StructureBatch.from_structures([dense, molecules(dtype)[-1]])
    if provider=="cgcnn":
        inputs=backbone.native_input(batch)
        assert inputs[2].shape==(15,13) and inputs.valid_mask.sum().item()==182
        assert inputs.valid_mask[:14].all() and not inputs.valid_mask[14].any()
        assert bool((inputs[2][inputs.valid_mask]<14).all())
    else:
        parent,line,_=backbone.native_input(batch)
        assert parent.num_edges==182 and not parent.edata["images"].any()
        assert torch.bincount(parent.src,minlength=15).tolist()==[13]*14+[0]
        assert not bool((parent.dst>=14).any())
        assert line.num_nodes==182
        torch.testing.assert_close(line.edata["h"],
            -(parent.edata["r"][line.src]*parent.edata["r"][line.dst]).sum(-1) /
            (parent.edata["r"][line.src].norm(dim=-1)*parent.edata["r"][line.dst].norm(dim=-1)), rtol=3e-5,atol=3e-6)
    periodic = replace(batch, pbc=torch.ones_like(batch.pbc))
    with pytest.raises(ValueError, match="nonperiodic"):
        backbone.native_input(periodic)


def test_forcefield_ragged_empty_batch_geometry_and_mixed_gradients(backbone_case):
    provider, _, dtype, backbone = backbone_case
    model, _ = forcefield(backbone_case)
    values=molecules(dtype);batch=StructureBatch.from_structures(values)
    batch.positions.requires_grad_()
    prediction=model(batch,create_graph=True)
    assert torch.isfinite(prediction["forces"]).all()
    assert torch.equal(prediction["forces"][-1],torch.zeros(3,device=DEVICE,dtype=dtype))
    for i,value in enumerate(values):
        separate=model(StructureBatch.from_structures([value]),create_graph=False)
        a,b=int(batch.ptr[i]),int(batch.ptr[i+1])
        torch.testing.assert_close(prediction["total_energy"][i:i+1],separate["total_energy"],rtol=.001,atol=.0002)
        torch.testing.assert_close(prediction["forces"][a:b],separate["forces"],rtol=.001,atol=.0002)
    rotated=torch.tensor([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]],device=DEVICE,dtype=dtype)
    for transformed,force_reference in [
        (batch.with_geometry(batch.positions+batch.positions.new_tensor([.31,-.27,.19]),batch.cell),prediction["forces"]),
        (batch.with_geometry(batch.positions@rotated.T,batch.cell@rotated.T),prediction["forces"]@rotated.T),
        (batch.with_geometry(batch.positions,batch.cell*17),prediction["forces"])]:
        result=model(transformed,create_graph=False)
        torch.testing.assert_close(result["total_energy"],prediction["total_energy"],rtol=.001,atol=.0002)
        torch.testing.assert_close(result["forces"],force_reference,rtol=.001,atol=.0002)
    permuted, permuted_forces = [], []
    for i,value in enumerate(values):
        order=torch.arange(len(value.numbers)-1,-1,-1,device=DEVICE)
        permuted.append(replace(value,numbers=value.numbers[order],positions=value.positions[order]))
        permuted_forces.append(prediction["forces"][int(batch.ptr[i]):int(batch.ptr[i+1])][order])
    result=model(StructureBatch.from_structures(permuted),create_graph=False)
    torch.testing.assert_close(result["total_energy"],prediction["total_energy"],rtol=.001,atol=.0002)
    torch.testing.assert_close(result["forces"],torch.cat(permuted_forces),rtol=.001,atol=.0002)
    step=1e-3 if dtype==torch.float32 else 1e-5
    offset=torch.zeros_like(batch.positions);offset[1,0]=step
    plus=model.energy_model(batch.with_geometry(batch.positions+offset,batch.cell)).sum()
    minus=model.energy_model(batch.with_geometry(batch.positions-offset,batch.cell)).sum()
    numeric=-(plus-minus)/(2*step)
    torch.testing.assert_close(prediction["forces"][1,0],numeric,rtol=.02,atol=.002)
    hessian=torch.autograd.grad(prediction["forces"][1,0],batch.positions,retain_graph=True)[0]
    assert torch.isfinite(hessian).all() and float(hessian.norm())>1e-10
    targets=torch.arange(prediction["forces"].numel(),device=DEVICE,dtype=dtype).reshape_as(prediction["forces"])/100
    objective=(prediction["forces"]-targets).square().sum()
    for module in [model.backbone,model.energy_model.readout]:
        gradients=torch.autograd.grad(objective,list(module.parameters()),retain_graph=True,allow_unused=True)
        active=[value for value in gradients if value is not None]
        assert active and all(torch.isfinite(value).all() for value in active)
        assert sum(float(value.norm()) for value in active)>1e-10
    model.train()
    if provider=="cgcnn":assert not backbone.model.training
    model(batch,create_graph=True)["forces"].square().sum().backward()
    assert all(not module._forward_hooks and not module._forward_pre_hooks for module in backbone.model.modules())


def test_profile_checkpoint_is_self_contained_and_rejects_profile_change(backbone_case,tmp_path):
    provider, initialization, dtype, backbone=backbone_case
    model,settings=forcefield(backbone_case)
    batch=StructureBatch.from_structures(molecules(dtype))
    expected=model(batch,create_graph=False)
    settings["backbone"]["checkpoint"]="/missing/source/checkpoint"
    if provider=="cgcnn":settings["backbone"]["atom_init"]="/missing/source/atom_init.json"
    path=tmp_path/"molecular.pt"
    payload=dict(format_version=2,config=settings,state_dict=model.state_dict(),official_backbone=copy.deepcopy(backbone.official_artifact))
    torch.save(payload,path)
    loaded=load_checkpoint(path,device=DEVICE)
    assert loaded.backbone.input_profile==backbone.input_profile
    assert all(torch.equal(value,loaded.state_dict()[key]) for key,value in model.state_dict().items())
    actual=loaded(batch,create_graph=False)
    for key in ["total_energy","forces"]:
        torch.testing.assert_close(actual[key],expected[key],rtol=3e-5,atol=3e-6)
    payload["config"]["backbone"]["input_cutoff"]=5.
    torch.save(payload,tmp_path/"changed-profile.pt")
    with pytest.raises(ValueError,match="profile differs"):
        load_checkpoint(tmp_path/"changed-profile.pt",device=DEVICE)


@pytest.mark.parametrize("dtype", [torch.float32,torch.float64])
@pytest.mark.parametrize("training", [False,True])
@pytest.mark.parametrize("initialization", ["pretrained","scratch"])
def test_cgcnn_ragged_mask_matches_packed_original_modules(dtype,training,initialization):
    torch.manual_seed(123)
    backbone=make_backbone("cgcnn",initialization=initialization,input_profile="molecular_radius").to(device=DEVICE,dtype=dtype)
    backbone.train(training);original=copy.deepcopy(backbone.model)
    values=molecules(dtype);batch=StructureBatch.from_structures(values)
    inputs=backbone.native_input(batch)
    x=original.embedding(inputs[0])
    srcs,dsts,radials=[],[],[];start=0
    for value in values:
        src,dst=ase_edges(value)
        xyz=value.positions.detach().cpu().numpy().astype(np.float64)
        distance=np.linalg.norm(xyz[dst]-xyz[src],axis=-1)
        srcs.append(torch.tensor(src+start,device=DEVICE));dsts.append(torch.tensor(dst+start,device=DEVICE))
        radials.append(torch.as_tensor(backbone.gaussian.expand(distance),device=DEVICE,dtype=dtype))
        start+=len(value.numbers)
    src,dst,y=torch.cat(srcs),torch.cat(dsts),torch.cat(radials)
    for conv in original.convs:
        gate=conv.bn1(conv.fc_full(torch.cat([x[src],x[dst],y],dim=-1)))
        filt,core=gate.chunk(2,dim=-1)
        aggregate=x.new_zeros(x.shape).index_add(0,src,conv.sigmoid(filt)*conv.softplus1(core))
        x=conv.softplus2(x+conv.bn2(aggregate))
    actual=backbone.encode(batch).nodes
    torch.testing.assert_close(actual,x,rtol=3e-5,atol=3e-6)
    for key,value in original.state_dict().items():
        if "running_" in key or "num_batches_tracked" in key:
            torch.testing.assert_close(backbone.model.state_dict()[key],value,rtol=3e-5,atol=3e-6)


@pytest.mark.parametrize("dtype", [torch.float32,torch.float64])
def test_cgcnn_padding_has_no_value_gradient_or_edge_bn_statistics(dtype):
    backbone=make_backbone("cgcnn",input_profile="molecular_radius").to(device=DEVICE,dtype=dtype).eval()
    inputs=backbone.native_input(StructureBatch.from_structures(molecules(dtype)))
    with valid_neighbor_messages(backbone.model,inputs):expected=backbone.model(*inputs)
    edge=inputs[1].detach().clone();edge[~inputs.valid_mask]=1e5;edge.requires_grad_()
    index=inputs[2].clone();index[~inputs.valid_mask]=len(inputs[0])-1
    modified=MolecularCGCNNInput((inputs[0],edge,index,inputs[3]),inputs.valid_mask)
    with valid_neighbor_messages(backbone.model,modified):actual=backbone.model(*modified)
    torch.testing.assert_close(actual,expected,rtol=3e-5,atol=3e-6)
    gradient=torch.autograd.grad(actual.sum(),edge)[0]
    assert torch.equal(gradient[~inputs.valid_mask],torch.zeros_like(gradient[~inputs.valid_mask]))


@pytest.mark.parametrize("dtype", [torch.float32,torch.float64])
def test_cgcnn_empty_bn_and_hook_modes_survive_success_and_exceptions(dtype):
    backbone=make_backbone("cgcnn",input_profile="molecular_radius").to(device=DEVICE,dtype=dtype).eval()
    empty=StructureBatch.from_structures([molecules(dtype)[-1]])
    state={key:value.clone() for key,value in backbone.state_dict().items()}
    assert torch.isfinite(backbone.encode(empty).nodes).all()
    assert all(torch.equal(value,backbone.state_dict()[key]) for key,value in state.items())
    backbone.train()
    modes={name:module.training for name,module in backbone.model.named_modules()}
    empty_pair=StructureBatch.from_structures([molecules(dtype)[-1],
        structure([10],[[0.,0.,0.]],"another_isolated",dtype)])
    edge_state={key:value.clone() for key,value in backbone.state_dict().items() if ".bn1." in key}
    assert torch.isfinite(backbone.encode(empty_pair).nodes).all()
    assert all(torch.equal(value,backbone.state_dict()[key]) for key,value in edge_state.items())
    assert modes=={name:module.training for name,module in backbone.model.named_modules()}
    def fail(module,arguments):raise RuntimeError("injected original forward failure")
    handle=backbone.model.convs[0].fc_full.register_forward_pre_hook(fail)
    try:
        for batch in [empty,StructureBatch.from_structures(molecules(dtype))]:
            with pytest.raises(RuntimeError,match="injected"):
                backbone.encode(batch)
            assert modes=={name:module.training for name,module in backbone.model.named_modules()}
    finally:handle.remove()
    assert all(not module._forward_hooks and not module._forward_pre_hooks for module in backbone.model.modules())


def test_alignn_profile_rejects_invented_lattice_features_and_native_bulk_stress():
    backbone=make_backbone("alignn",input_profile="molecular_radius").to(device=DEVICE).eval()
    batch=StructureBatch.from_structures(molecules(torch.float32))
    backbone.configuration["use_lattice_prop"]=True
    with pytest.raises(ValueError,match="lattice-property"):
        backbone.native_input(batch)
    backbone.configuration["use_lattice_prop"]=False
    backbone.model.config.calculate_gradient=True
    backbone.model.config.stresswise_weight=1.
    with pytest.raises(ValueError,match="bulk volume"):
        backbone.native_forward(batch)


def test_nonperiodic_topology_cutoff_cell_independence_and_live_vectors():
    value=structure([1,1],[[0.,0.,0.],[5.999,0.,0.]],"boundary",torch.float64)
    batch=StructureBatch.from_structures([value]);batch.positions.requires_grad_()
    src,dst,r=nonperiodic_edges(batch,6.)
    assert len(src)==2
    assert torch.isfinite(torch.autograd.grad(r.square().sum(),batch.positions)[0]).all()
    altered=batch.with_geometry(batch.positions,batch.cell*1000)
    a,b,v=nonperiodic_edges(altered,6.)
    assert torch.equal(a,src) and torch.equal(b,dst) and torch.equal(v,r)
    for separation in [6.,6.001]:
        positions=batch.positions.detach().clone();positions[1,0]=separation
        assert len(nonperiodic_edges(batch.with_geometry(positions,batch.cell),6.)[0])==0
    positions=batch.positions.detach().clone();positions[1]=positions[0]
    with pytest.raises(ValueError,match="Coincident"):
        nonperiodic_edges(batch.with_geometry(positions,batch.cell),6.)


@pytest.mark.parametrize("provider", ["cgcnn","alignn"])
@pytest.mark.parametrize("dtype", [torch.float32,torch.float64])
def test_omitted_profile_periodic_original_input_and_forward_regression(provider,dtype):
    from ase.build import bulk
    from universal_gnn.backbones.official.reference import cgcnn_reference,alignn_reference

    values=[]
    for symbol,kind,a in [("Si","diamond",5.43),("Cu","fcc",3.6)]:
        atoms=bulk(symbol,kind,a=a)
        values.append(Structure(torch.tensor(atoms.numbers),torch.tensor(atoms.positions,dtype=dtype),
            torch.tensor(atoms.cell.array,dtype=dtype),torch.ones(3,dtype=torch.bool),symbol,{"bandgap":1.}))
    backbone=make_backbone(provider).to(dtype=dtype).eval()
    reference=cgcnn_reference if provider=="cgcnn" else alignn_reference
    with default_dtype(dtype):
        result=reference(backbone,values,dict(task=dict(property="bandgap"),dtype="float64" if dtype==torch.float64 else "float32"))
    assert result["structures"]==2 and "input_profile" not in backbone.native_graph_provenance()
