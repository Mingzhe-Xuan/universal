"""Bounded original-artifact task/head metadata inspection; submit through Slurm."""

import argparse
import inspect
import io
import json
import os
from pathlib import Path
import zipfile

import torch
from universal_gnn.backbones.factory import make_backbone


def small(value):
    if isinstance(value,torch.Tensor):
        return value.tolist() if value.numel()<=16 else {"shape":list(value.shape),"dtype":str(value.dtype)}
    if isinstance(value,dict):return {str(k):small(v) for k,v in value.items() if not isinstance(v,bytes)}
    if isinstance(value,(list,tuple)):return [small(v) for v in value[:120]]
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return str(value)[:2000]


def main(args):
    from universal_gnn.contracts.e3nn_compat import load_o3

    load_o3()
    b=make_backbone(args.model,implementation="official").float().eval()
    artifact=b.official_artifact;raw={}
    if args.model in {"cgcnn","equiformer"}:
        raw=torch.load(io.BytesIO(artifact["files"]["checkpoint"]),map_location="cpu",weights_only=False)
        raw={k:v for k,v in raw.items() if k not in {"state_dict","optimizer","scheduler","ema"}}
    elif args.model=="alignn":
        with zipfile.ZipFile(io.BytesIO(artifact["files"]["archive"])) as z:
            name=next(n for n in z.namelist() if n.endswith("config.json"))
            raw=json.loads(z.read(name))
            weights=next(n for n in z.namelist() if n.endswith("best_model.pt"))
            saved=torch.load(io.BytesIO(z.read(weights)),map_location="cpu",weights_only=True)
            raw["checkpoint_metadata"]={k:v for k,v in saved.items() if k not in {"model","state_dict","optimizer","scheduler"}}
    elif args.model=="megnet":raw=json.loads(artifact["files"]["model.json"])
    else:raw=getattr(b.model,"metadata",{})
    modules=[]
    for name,module in b.named_modules():
        if name.count(".")<3 or any(word in name for word in ("readout","scale_shift","atomic_energies","s2s","output_proj","head")):
            modules.append({"name":name,"type":type(module).__qualname__,
                            "parameters":sum(p.numel() for p in module.parameters(recurse=False)),
                            "buffers":{k:small(v) for k,v in module.named_buffers(recurse=False)}})
    sources={}
    if args.model in {"nequip","megnet","alignn","mace"}:
        for name in ("model","model.model","model.model.func"):
            try:module=b.get_submodule(name);sources[name]=inspect.getsource(type(module))[:65000]
            except (AttributeError,OSError,TypeError):pass
    result={"model":args.model,"slurm_job_id":os.environ["SLURM_JOB_ID"],"original_load":b.load_report,
            "metadata":small(raw),"modules":modules,"sources":sources,
            "model_attributes":{k:small(getattr(b.model,k,None)) for k in
                 ("heads","atomic_energies_fn","scale_shift","avg_num_nodes","task","classification")}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps({"model":args.model,"output":str(args.output)}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",required=True,choices=["alignn","cgcnn","megnet","mace","nequip","equiformer"])
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):raise SystemExit("Submit through Slurm")
    main(args)
