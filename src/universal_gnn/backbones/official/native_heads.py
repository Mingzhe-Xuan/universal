"""Native head contracts and physical predictions for verified published artifacts."""

import io
import json

import torch

from universal_gnn.contracts.native import NativeTaskContract
from .profiles import PROFILES


def native_contract(backbone):
    if getattr(backbone, "initialization", "pretrained") != "pretrained":
        raise ValueError("prediction.head_mode=native requires the original pretrained head; use head_mode=reset with scratch")
    artifact = backbone.official_artifact
    name = artifact["provider"]
    if (name not in PROFILES or sorted(artifact["sha256"].values()) != sorted(PROFILES[name]["files"].values())):
        raise ValueError("prediction.head_mode=native has no verified task contract for this artifact; "
                         "register its original task/normalization or select head_mode=reset")
    options = {"artifact_sha256": dict(artifact["sha256"])}
    if name == "alignn":
        options.update(property="bandgap",unit="eV",head_paths=("model.fc","model.fc_atomwise","model.fc_additional_output"),
                       original_task="JARVIS optb88vdw band gap",pooling="original scatter_mean",
                       normalization={"link":backbone.model.link_name,"external_scaler":False})
    elif name == "cgcnn":
        raw = torch.load(io.BytesIO(artifact["files"]["checkpoint"]),map_location="cpu",weights_only=False)
        stats = raw["normalizer"]
        options.update(property="bandgap",unit="eV",
            head_paths=("model.conv_to_fc","model.conv_to_fc_softplus","model.fcs","model.softpluses",
                        "model.fc_out","model.dropout","model.logsoftmax"),
            original_task="Materials Project band gap",pooling="original mean before conv_to_fc",
            normalization={"mean":float(stats["mean"]),"std":float(stats["std"]),"operation":"output * std + mean"})
    elif name == "megnet":
        raw=json.loads(artifact["files"]["model.json"])
        options.update(property="formation_energy",unit="eV/atom",
            head_paths=("model.model.node_s2s","model.model.edge_s2s","model.model.output_proj"),
            original_task="MEGNet MP formation energy per atom",pooling="original node/edge Set2Set and global state",
            normalization={"transformer":raw["kwargs"]["target_transformer"],"operation":"original inverse_transform"})
    elif name in {"mace","nequip"}:
        if name == "mace":
            paths=("model.readouts","model.atomic_energies_fn","model.scale_shift")
            normalization={"operation":"original atomic references and scale_shift",
                           "scale":float(backbone.model.scale_shift.scale),"shift":float(backbone.model.scale_shift.shift)}
        else:
            prefix="model."+backbone.feature_path.rsplit(".",1)[0]
            paths=("model."+backbone.feature_path,prefix+".per_type_energy_scale_shift",prefix+".total_energy_sum")
            normalization={"operation":"original per_type_energy_scale_shift and total-energy reduction"}
        options.update(property="total_energy",unit="eV",reduction="sum",forcefield=True,
                       head_paths=paths,original_task=f"{name} native total energy potential",
                       pooling="original atomic-energy sum",normalization=normalization,
                       packaging={"energy":"native total energy reshaped [B,1]",
                           "forces":"-d(original energy)/dR in eV/angstrom",
                           "stress":"d(original energy)/dstrain / V; eV/angstrom^3 multiplied by160.21766208 for UGNN GPa"})
    elif name == "equiformer":
        raw=torch.load(io.BytesIO(artifact["files"]["checkpoint"]),map_location="cpu",weights_only=False)
        stats=raw["normalizers"]["target"]
        options.update(property="oc20_relaxed_energy",unit="eV",reduction="sum",
            head_paths=("model.head","model.head_skip_connect","model.auxiliary_head"),
            original_task="OC20 IS2RE relaxed energy (not an instantaneous force potential)",
            pooling="original scaled_scatter and avg_num_nodes",
            normalization={"mean":float(stats["mean"]),"std":float(stats["std"]),"operation":"OCP target denorm"})
    return NativeTaskContract(**options)


def native_prediction(backbone, batch, contract):
    name=backbone.official_artifact["provider"]
    if name == "mace":
        value=backbone.native_forward(batch)
        prediction,nodes=value["energy"],value["node_feats"]
    elif name == "nequip":
        target=backbone.model.get_submodule(backbone.feature_path)
        captured=[]
        handle=target.register_forward_pre_hook(lambda module,inputs:captured.append(inputs[0]["node_features"]))
        try:
            data=backbone.native_input(batch)
            restricted={k:data[k] for k in backbone.model.model_input_fields if k in data}
            # Original energy network, including native head/scale-shift/reduction.
            # Its ForceStressOutput wrapper consumes the graph in eval; UGNN derives
            # F/S from this same original energy to retain mixed gradients when frozen.
            value=backbone.model.model.func(restricted)
            prediction,nodes=value["total_energy"],captured[0]
        finally:handle.remove()
    else:
        prediction,nodes=backbone.native_forward(batch)
        if name == "alignn":prediction=prediction["out"]
        elif name in {"cgcnn","equiformer"}:
            stats=contract.normalization
            prediction=prediction*prediction.new_tensor(stats["std"])+prediction.new_tensor(stats["mean"])
    features=backbone.output(nodes,batch)
    from universal_gnn.contracts.components import validate_native_features

    validate_native_features(features,backbone._native_feature_spec,batch)
    return prediction
