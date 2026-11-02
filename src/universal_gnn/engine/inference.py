import json
from pathlib import Path

import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.data.structures import load_structures
from universal_gnn.engine.training import load_checkpoint, predict


def run_inference(checkpoint, dataset_path, output, *, device="cpu", limit=None):
    saved = torch.load(checkpoint, map_location=device, weights_only=True)
    config = saved["config"]
    model = load_checkpoint(checkpoint, device=device)
    structures = load_structures(dataset_path, options=config["dataset"].get("options"))
    if limit is not None:
        if limit < 1:
            raise ValueError("Inference limit must be positive")
        structures = structures[:limit]
    batch = StructureBatch.from_structures(structures).to(device=device, dtype=torch.float64)
    result = {"checkpoint": str(checkpoint), "config": config,
              "checkpoint_format_version": saved.get("format_version", 1),
              "geometry_basis_version": getattr(getattr(model, "adapter", None), "basis_version", None),
              "structures": [{"id": structure.identifier, "provenance": structure.metadata}
                             for structure in structures]}
    if config["task"]["kind"] == "generation":
        from universal_gnn.engine.generation import generated_record

        generated = model.sample(batch, **config["task"].get("sampling", {}))
        result["generation"] = generated_record(generated)
    else:
        # Derivative heads and E/F/S intentionally enable input/auxiliary autograd in eval.
        from universal_gnn.engine.derived import derived_outputs

        predictions = predict(model, batch, config)
        result["predictions"] = {key: value.detach().cpu().tolist() for key, value in predictions.items()}
        result["derived"] = derived_outputs(predictions, config["task"])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
