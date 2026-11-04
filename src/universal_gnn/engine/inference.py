"""Minibatched inference; JSONL writes each result without retaining the dataset output."""

import copy
import json
import os
from pathlib import Path
import tempfile

import torch

from universal_gnn.engine.training import load_checkpoint, predict


def run_inference(checkpoint, dataset_path, output, *, device="cpu", limit=None, config_override=None):
    from universal_gnn.engine.runtime import check_model_config, checkpoint_config
    from universal_gnn.engine.batching import batches
    from universal_gnn.data.indexed import open_structures, SelectedStructures
    from universal_gnn.engine.batching import model_dtype
    from universal_gnn.engine.derived import derived_outputs

    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    config = checkpoint_config(saved)
    if config_override is not None:
        check_model_config(config, config_override, training=False)
        config = copy.deepcopy(config_override)
    config.setdefault("dtype", saved["config"].get("dtype", "float64"))
    if config["dtype"] != saved["config"].get("dtype", "float64"):
        raise ValueError("Inference precision must match the checkpoint dtype")
    config["device"] = device
    model = load_checkpoint(checkpoint, device=device)
    if "optimization" in config or "prediction" in config:
        from universal_gnn.engine.optimization import configure_optimization, resolved_model_config, component_audit

        configure_optimization(model, config)
        model.eval()
        config = resolved_model_config(config, model)
    from universal_gnn.data.splits.loading import load_partition

    settings = config["dataset"]
    configured_path = str(settings["path"])
    same_source = (str(dataset_path) == configured_path if str(dataset_path).startswith("plugin:") or
                   configured_path.startswith("plugin:") else Path(dataset_path).resolve() == Path(configured_path).resolve())
    if not same_source:
        # A training-source partition cannot select records in a new prediction source.
        settings.pop("split_manifest", None)
        settings.pop("split_manifest_sha256", None)
        settings.pop("partition", None)
        settings.pop("sha256", None)
    settings["path"] = str(dataset_path)
    structures = open_structures(dataset_path, dtype=model_dtype(config), options=settings.get("options"))
    indices, _, _ = load_partition(structures, settings)
    if settings.get("split_manifest") is not None:
        structures = SelectedStructures(structures, indices)
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("Inference limit must be positive")
        structures = SelectedStructures(structures, range(min(limit, len(structures))))
    if not len(structures):
        raise ValueError("Dataset must not be empty")
    result = {"checkpoint": str(checkpoint), "config": config, "structure_count": len(structures),
              "checkpoint_format_version": saved.get("format_version", 1),
              "geometry_basis_version": getattr(getattr(model, "adapter", None), "basis_version", None),
              "structures": []}
    if "prediction" in config or "optimization" in config:
        result["components"] = component_audit(model)
        result["checkpoint_capability_updates"] = getattr(model,"_checkpoint_capability_updates",[])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    streaming = output.suffix.lower() == ".jsonl"
    descriptor, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            if streaming:
                stream.write(json.dumps({"type": "metadata", **result}) + "\n")
            for batch in batches(structures, config):
                metadata = [{"id": identifier, "provenance": provenance}
                            for identifier, provenance in zip(batch.identifiers, batch.metadata)]
                if config["task"]["kind"] == "generation":
                    from universal_gnn.engine.generation import generated_record

                    generated = generated_record(model.sample(batch, **config["task"].get("sampling", {})))
                    if streaming:
                        for i, record in enumerate(metadata):
                            stream.write(json.dumps({"type": "generation", **record,
                                "generation": {key: value[i] for key, value in generated.items()}}) + "\n")
                    else:
                        for key, value in generated.items():
                            result.setdefault("generation", {}).setdefault(key, []).extend(value)
                else:
                    predictions = predict(model, batch, config)
                    derived = derived_outputs(predictions, config["task"])
                    if streaming:
                        for i, record in enumerate(metadata):
                            values = {}
                            for key, value in predictions.items():
                                atomic = key == "forces" or (config["task"]["kind"] == "supervised" and
                                          model.spec.scope == "node")
                                start, end = (int(batch.ptr[i]), int(batch.ptr[i + 1])) if atomic else (i, i + 1)
                                values[key] = value[start:end].detach().cpu().tolist()
                            local_derived = {key: value[i:i + 1] if key == "epsilon1_finite_window" else value
                                             for key, value in derived.items()}
                            stream.write(json.dumps({"type": "prediction", **record,
                                                     "predictions": values, "derived": local_derived}) + "\n")
                    else:
                        for key, value in predictions.items():
                            result.setdefault("predictions", {}).setdefault(key, []).extend(value.detach().cpu().tolist())
                        destination = result.setdefault("derived", {})
                        for key, value in derived.items():
                            if key == "epsilon1_finite_window":
                                destination.setdefault(key, []).extend(value)
                            else:
                                destination[key] = value
                if not streaming:
                    result["structures"].extend(metadata)
            if streaming:
                stream.write(json.dumps({"type": "completed", "structure_count": len(structures)}) + "\n")
            else:
                json.dump(result, stream, indent=2)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if streaming:
        result["streamed"] = True
    return result
