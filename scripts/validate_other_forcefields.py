"""Assess unverified official forcefield capabilities on real data; Slurm only."""

import argparse
from contextlib import contextmanager
import copy
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import traceback
from unittest.mock import patch

import torch

from universal_gnn.contracts import StructureBatch, resolve_feature_spec
from universal_gnn.data.formats import save_structures
from universal_gnn.data.geometry import strain_batch
from universal_gnn.engine import training
from universal_gnn.engine.inference import run_inference
from universal_gnn.engine.optimization import components, component_audit
from validate_official import independent_reference


MODELS = ("alignn", "cgcnn", "megnet", "nequip", "equiformer")


@contextmanager
def candidate_capabilities():
    original = training.make_backbone

    def assess(*args, **kwargs):
        backbone = original(*args, **kwargs)
        backbone.assessment_original_capabilities = dict(backbone.gradient_capabilities)
        # This scoped test factory permits assessing the guarded path. It changes metadata
        # only on newly constructed test instances, never production defaults or model layers.
        backbone.gradient_capabilities = {"positions": True, "strain": True, "mixed": True}
        return backbone

    with patch.object(training, "make_backbone", assess):
        yield


def configuration(model, path, spec, *, frozen, epochs):
    readout = {"name": "node_mlp", "pooling": "sum", "hidden_features": [32], "activation": "silu"}
    if not spec.even_scalars:
        readout["feature_processing"] = {"name": "scalar_invariants"}
    config = {"schema_version": 1, "seed": 123, "structures": "all", "batch_size": 5,
            "dtype": "float32", "device": "cpu", "epochs": epochs, "checkpoint_every": 1,
            "learning_rate": .001 if frozen else .0001,
            "backbone": {"name": model, "implementation": "official"},
            "dataset": {"path": str(path)}, "task": {"kind": "forcefield", "supervised_outputs": ["forces"]},
            "prediction": {"version": 1, "readout": readout},
            "optimization": {"train_backbone": not frozen, "train_readout": True}}
    if model in {"cgcnn", "equiformer"} and not frozen:
        config["optimization"]["backbone_eval"] = True
    return config


def reference_configuration(config):
    result = copy.deepcopy(config)
    if result["backbone"]["name"] == "cgcnn":
        # Original CIFData requires a scalar label slot, unused by prediction parity.
        # Its adapter takes the first component of the existing real force label.
        result["task"]["property"] = "forces"
    return result


def snapshot(module):
    return {key: value.detach().cpu().clone() for key, value in module.state_dict().items()}


def parameter_delta(before, module):
    return math.sqrt(sum(float((value.detach().cpu().double()-before[key].double()).square().sum())
                         for key, value in module.named_parameters()))


def assess_gradients(model, structures, *, step=.002):
    model.eval()
    source = structures[0]
    perturbation = .017 * torch.sin(torch.arange(source.positions.numel()).reshape_as(source.positions) * .73 + .31)
    probe = StructureBatch.from_structures([replace(source, positions=source.positions+perturbation)])
    model.zero_grad(set_to_none=True)
    value = model(probe, create_graph=True)
    for output in value.values(): assert bool(torch.isfinite(output).all())
    (value["forces"].square().sum()+value["stress"].square().sum()).backward()
    norms = {}
    for name, module in components(model).items():
        grads = [p.grad for p in module.parameters() if p.grad is not None]
        assert all(bool(torch.isfinite(g).all()) for g in grads)
        norms[name] = math.sqrt(sum(float(g.square().sum()) for g in grads))
        if not model._component_policy["train_"+name]: assert not grads
    assert norms["readout"] > 1e-10
    if model._component_policy["train_backbone"]: assert norms["backbone"] > 1e-10
    torch.testing.assert_close(value["forces"].sum(0),torch.zeros_like(value["forces"][0]),rtol=0,atol=2e-5)
    forces, stresses = [], []
    for atom in range(min(2,len(source.numbers))):
        for axis in range(3):
            change = torch.zeros_like(probe.positions);change[atom,axis] = step
            plus = model.energy_model(probe.with_geometry(probe.positions+change,probe.cell))
            minus = model.energy_model(probe.with_geometry(probe.positions-change,probe.cell))
            forces.append({"index":[atom,axis],"analytic":float(value["forces"][atom,axis].detach()),
                           "numeric":float((-(plus-minus)/(2*step)).detach().squeeze())})
    for i,j in ((0,0),(1,1),(0,1)):
        strain = torch.zeros_like(probe.cell);strain[0,i,j] = step
        plus = model.energy_model(strain_batch(probe,strain))
        minus = model.energy_model(strain_batch(probe,-strain))
        numeric = (plus-minus)/(2*step*torch.linalg.det(probe.cell[0]).abs())*160.21766208
        stresses.append({"index":[i,j],"analytic":float(value["stress"][0,i,j].detach()),
                         "numeric":float(numeric.detach().squeeze())})
    result = {"mixed_parameter_gradient_norms":norms,"forces":forces,"stress":stresses,
              "step":step,"rtol":.02,"atol":.002,
              "force_sum_max":float(value["forces"].sum(0).abs().max().detach())}
    for name, entries in (("forces",forces),("stress",stresses)):
        a = probe.positions.new_tensor([v["analytic"] for v in entries]);n = probe.positions.new_tensor([v["numeric"] for v in entries])
        result[name+"_max_abs_error"] = float((a-n).abs().max())
        result[name+"_finite_difference_passed"] = bool(torch.isclose(a,n,rtol=.02,atol=.002).all())
    return result


def assess_batches(model, structures, *, train):
    before = snapshot(model)
    model.train(train)
    selected = [structures[0],structures[1]]
    b = StructureBatch.from_structures(selected)
    combined = model(b,create_graph=False)
    repeated = model(b,create_graph=False)
    separated = [model(StructureBatch.from_structures([s]),create_graph=False) for s in selected]
    errors, passed = {}, True
    for name in combined:
        values = torch.cat([v[name] for v in separated])
        errors[name] = float((combined[name]-values).abs().max().detach())
        passed = passed and bool(torch.isclose(combined[name],values,rtol=2e-4,atol=2e-5).all())
    result = {"passed":passed,"max_abs_errors":errors,"rtol":2e-4,"atol":2e-5,
              "repeat_max_abs_errors":{k:float((combined[k]-repeated[k]).abs().max().detach()) for k in combined},
              "original_stochastic_settings":{k:getattr(model.backbone.model,k,None) for k in
                   ("alpha_drop","proj_drop","out_drop","drop_path_rate")} if hasattr(model.backbone,"model") else {},
              "components":component_audit(model),"normalization_modules":[
                  {"name":name,"type":type(module).__qualname__,"training":module.training}
                  for name,module in model.backbone.named_modules()
                  if isinstance(module,torch.nn.modules.batchnorm._BatchNorm)]}
    model.load_state_dict(before,strict=True)
    model.eval()
    return result


def validate_mode(config, output, *, fd_step=.002):
    output.mkdir(parents=True,exist_ok=True)
    result = {"config":config,"errors":[],"candidate_metadata_only":True}
    torch.manual_seed(config["seed"])
    model = training.build_model(config).float()
    structures = training.dataset(config)
    before = {name:snapshot(module) for name,module in components(model).items()}
    result["original_capabilities"] = model.backbone.assessment_original_capabilities
    result["native_spec"] = model.energy_model.native_spec.to_dict()
    for stage, action in (("derivatives",lambda:assess_gradients(model,structures,step=fd_step)),
                          ("eval_batch",lambda:assess_batches(model,structures,train=False)),
                          ("train_batch",lambda:assess_batches(model,structures,train=True))):
        try:
            result[stage] = action()
            passed = result[stage].get("passed",all(result[stage].get(k,True) for k in
                         ("forces_finite_difference_passed","stress_finite_difference_passed")))
            if not passed:result["errors"].append({"stage":stage,"error":"numeric comparison failed"})
        except Exception as error:
            result["errors"].append({"stage":stage,"error":repr(error),"traceback":traceback.format_exc()})
    try:
        if config["optimization"].get("backbone_eval"):
            with patch.dict(model._component_policy, {"backbone_eval": False}):
                result["unrestricted_train_batch_diagnostic"] = assess_batches(model,structures,train=True)
        report = training.run_training(config,output/"training")
        trained = training.load_checkpoint(output/"training/checkpoint.pt")
        changes = {name:parameter_delta(before[name],module) for name,module in components(trained).items()}
        assert changes["readout"] > 0
        if config["optimization"]["train_backbone"]: assert changes["backbone"] > 0
        else:
            for key,value in before["backbone"].items():
                torch.testing.assert_close(value,trained.backbone.state_dict()[key],rtol=0,atol=0)
        assert report["selected_structures"] == 10 and report["supervised_outputs"] == ["forces"]
        assert report["final_loss"] < report["initial_loss"]
        saved = torch.load(output/"training/checkpoint.pt",map_location="cpu",weights_only=True)
        assert set(saved["scales"]) == {"forces"} and saved["official_backbone"]
        inferred = run_inference(output/"training/checkpoint.pt",config["dataset"]["path"],output/"predictions.jsonl")
        assert inferred["structure_count"] == 10
        result["training"] = {"passed":True,"initial_loss":report["initial_loss"],"final_loss":report["final_loss"],
            "component_parameter_delta_norms":changes,"backbone_gradient_norms":report["backbone_gradient_norms"],
            "gradient_norms":report["gradient_norms"],"components_during_training":report["components_during_training"],
            "execution":report["execution"],"structures":report["structures"],"inferred_structures":10}
    except Exception as error:
        result["errors"].append({"stage":"training","error":repr(error),"traceback":traceback.format_exc()})
    result["passed"] = not result["errors"]
    (output/"validation.json").write_text(json.dumps(result,indent=2))
    return result


def validate(args):
    entry = json.loads(Path("data/acceptance/manifest.json").read_text())["tasks"]["forcefield"]
    assert hashlib.sha256(Path(entry["dataset"]["path"]).read_bytes()).hexdigest() == entry["dataset"]["sha256"]
    source = {"dataset":entry["dataset"],"task":{"kind":"forcefield","supervised_outputs":["forces"]},"dtype":"float32"}
    structures = training.dataset(source)
    force_only = [replace(s,targets={"forces":s.targets["forces"]}) for s in structures]
    assert len(force_only) == 10
    path = args.output/"real-force-only.json"
    save_structures(path,force_only,metadata={"source":entry["dataset"]["path"],"dtype":"float32","labels":["forces"]})
    backbone = training.make_backbone(args.model,implementation="official").float().eval()
    spec = resolve_feature_spec(backbone)
    config = configuration(args.model,path,spec,frozen=True,epochs=args.epochs)
    reference = independent_reference(backbone,force_only,reference_configuration(config))
    original_load = copy.deepcopy(backbone.load_report)
    del backbone
    modes = {}
    with candidate_capabilities():
        if args.fd_sweep:
            torch.manual_seed(config["seed"])
            model = training.build_model(config).float()
            values = [assess_gradients(model,force_only,step=step) for step in (.002,.001,.0005,.0002,.0001)]
            result = {"model":args.model,"slurm_job_id":os.environ["SLURM_JOB_ID"],"steps":values,
                      "interpretation":"fixed model/probe finite-difference convergence diagnostic; no tolerance change"}
            if args.model == "alignn":
                from universal_gnn.engine.configuration import load_config

                documented = training.build_model(load_config("configs/prediction_bandgap.yaml"))
                result["documented_bandgap_first_layer"] = documented.readout.core.network[0].in_features
                assert result["documented_bandgap_first_layer"] == 512
            (args.output/"fd-sweep.json").write_text(json.dumps(result,indent=2))
            print(json.dumps({"model":args.model,"steps":[{k:v[k] for k in
                  ("step","forces_max_abs_error","stress_max_abs_error","forces_finite_difference_passed","stress_finite_difference_passed")} for v in values]}))
            return True
        for frozen in (True,False):
            name = "frozen" if frozen else "full"
            config = configuration(args.model,path,spec,frozen=frozen,epochs=args.epochs)
            modes[name] = validate_mode(config,args.output/name,fd_step=args.fd_step)
    result = {"model":args.model,"passed":all(v["passed"] for v in modes.values()),
              "slurm_job_id":os.environ["SLURM_JOB_ID"],"independent_reference":reference,
              "official_load":original_load,"modes":modes,"production_capabilities_changed":False,
              "interpretation":"candidate capability assessment; real ten-structure execution, not held-out accuracy"}
    (args.output/"validation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({"model":args.model,"passed":result["passed"],"modes":{
          k:{"passed":v["passed"],"errors":[e["stage"] for e in v["errors"]]} for k,v in modes.items()}}))
    return result["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",choices=MODELS,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--epochs",type=int,default=4)
    parser.add_argument("--fd-step",type=float,default=.002)
    parser.add_argument("--fd-sweep",action="store_true",help="Fixed-probe step convergence diagnostic without training")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):raise SystemExit("Submit through Slurm")
    if args.epochs < 1:raise SystemExit("epochs must be positive")
    if not math.isfinite(args.fd_step) or args.fd_step <= 0:raise SystemExit("fd-step must be finite and positive")
    args.output.mkdir(parents=True,exist_ok=True)
    try:
        passed = validate(args)
    except Exception as error:
        (args.output/"failure.json").write_text(json.dumps({"error":repr(error),"traceback":traceback.format_exc()},indent=2))
        raise
    if not passed:raise SystemExit(2)
