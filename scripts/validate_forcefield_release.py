"""Verify ordinary production forcefield resume/inference without provisional capabilities."""

import argparse
import copy
import json
import os
from pathlib import Path
import traceback

import torch

from universal_gnn.engine.inference import run_inference
from universal_gnn.engine.runtime import checkpoint_config
from universal_gnn.engine.training import load_checkpoint, run_training


def validate(args):
    evidence = json.loads((args.assessment/"validation.json").read_text())
    if not evidence["passed"] or not all(v["passed"] for v in evidence["modes"].values()):
        raise ValueError("Only fully passed candidate modes can enter release validation")
    modes = {}
    for name in ("frozen", "full"):
        source = args.assessment/name/"training/checkpoint.pt"
        saved = torch.load(source,map_location="cpu",weights_only=True)
        model = load_checkpoint(source)
        assert not hasattr(model.backbone,"assessment_original_capabilities")
        assert all(model.energy_model.native_spec.gradients.values())
        config = checkpoint_config(saved)
        completed = saved["training_state"]["completed_epochs"]
        config["epochs"] = completed+1
        report = run_training(config,args.output/name,resume=source)
        assert report["resume"]["kind"]=="full" and report["resume"]["completed_epochs_before"]==completed
        assert report["selected_structures"]==10 and report["supervised_outputs"]==["forces"]
        override=copy.deepcopy(report["config"])
        override["optimization"].update(train_backbone=False,train_readout=False)
        prediction=run_inference(args.output/name/"checkpoint.pt",config["dataset"]["path"],
                                 args.output/name/"predictions.jsonl",config_override=override)
        assert prediction["structure_count"]==10
        assert all(v["trainable_parameters"]==0 for v in prediction["components"].values())
        modes[name]={"passed":True,"resumed_epochs":[completed,completed+1],
            "segment_initial_loss":report["segment_initial_loss"],"final_loss":report["final_loss"],
            "parameter_delta_norm":report["parameter_delta_norm"],"execution":report["execution"],
            "components_during_training":report["components_during_training"],
            "structures":report["structures"],"frozen_parameter_inference":True}
    previous_replay=None
    if evidence["model"]=="cgcnn":
        old=Path("runs/prediction-cgcnn-real2-771/linear-frozen")
        saved=torch.load(old/"checkpoint.pt",map_location="cpu",weights_only=True)
        output=run_inference(old/"checkpoint.pt",saved["config"]["dataset"]["path"],args.output/"previous-bandgap.json")
        expected=json.loads((old/"report.json").read_text())["predictions"]["bandgap"]
        torch.testing.assert_close(torch.tensor(output["predictions"]["bandgap"]),torch.tensor(expected),rtol=1e-5,atol=1e-6)
        assert output["checkpoint_capability_updates"]
        previous_replay={"passed":True,"capability_updates":output["checkpoint_capability_updates"],
                         "max_prediction_error":float((torch.tensor(output["predictions"]["bandgap"])-torch.tensor(expected)).abs().max())}
    result={"passed":True,"model":evidence["model"],"slurm_job_id":os.environ["SLURM_JOB_ID"],
            "modes":modes,"assessment":str(args.assessment),"previous_supervised_replay":previous_replay,
            "provisional_capabilities_used":False,"interpretation":"production execution/resume validation, not held-out accuracy"}
    (args.output/"validation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({"model":result["model"],"passed":True,"provisional_capabilities_used":False}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessment",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):raise SystemExit("Submit through Slurm")
    args.output.mkdir(parents=True,exist_ok=True)
    try:validate(args)
    except Exception as error:
        (args.output/"failure.json").write_text(json.dumps({"error":repr(error),"traceback":traceback.format_exc()},indent=2))
        raise
