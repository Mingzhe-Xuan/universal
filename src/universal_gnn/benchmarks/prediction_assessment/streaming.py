"""Complete source inference validation without model deserialization or execution."""

import hashlib
import json
from pathlib import Path

from .contracts import SHAPES, compare, finite_shape, full_inference_config, source_context, unchanged_source


def verify_inference_stream(training_report, predictions, *, expected_sha256, expected_bytes):
    context = source_context(training_report)
    trained, config, task = (context[k] for k in ("trained", "config", "task"))
    digest, count, completed = hashlib.sha256(), 0, False
    names = ("total_energy", "forces", "stress") if task == "forcefield" else (task,)
    scalars = dict.fromkeys(names, 0)
    expected_config = full_inference_config(config)
    with Path(predictions).open("rb") as stream:
        raw = next(stream, None)
        if raw is None:
            raise ValueError("Missing inference metadata header")
        digest.update(raw)
        header = json.loads(raw)
        if (header.get("type") != "metadata" or header.get("structure_count") != len(context["ids"]) or
                header.get("structures") != [] or
                Path(header.get("checkpoint", "")).resolve() != Path(trained["best_checkpoint"]).resolve()):
            raise ValueError("Inference header source/count/checkpoint differs")
        actual_config = dict(header["config"])
        actual_config.pop("resolved_components", None)
        compare(actual_config, expected_config, "inference_config", rtol=0, atol=0)
        for raw in stream:
            if completed:
                raise ValueError("Records follow the inference completion marker")
            digest.update(raw)
            row = json.loads(raw)
            if row.get("type") == "completed":
                if row.get("structure_count") != len(context["ids"]) or count != len(context["ids"]):
                    raise ValueError("Inference completed before all source records")
                completed = True
                continue
            if (row.get("type") != "prediction" or count >= len(context["ids"]) or
                    row.get("id") != context["ids"][count] or row.get("derived") != {} or
                    set(row.get("predictions", {})) != set(names)):
                raise ValueError("Inference ordered ID/type/output names differ")
            for name in names:
                shape = (context["natoms"][count], 3) if name == "forces" else SHAPES[name]
                scalars[name] += finite_shape(row["predictions"][name], shape)
            count += 1
    if not completed or count != len(context["ids"]):
        raise ValueError("Inference lacks every source prediction and final completion marker")
    if digest.hexdigest() != expected_sha256 or Path(predictions).stat().st_size != expected_bytes:
        raise ValueError("Complete inference output bytes/hash differs")
    unchanged_source(context, training_report)
    return dict(status="passed", structures=count, all_ordered_ids_match_source=True,
                completion_marker_verified=True, finite_prediction_elements=scalars,
                source_sha256=config["dataset"]["sha256"], prediction_sha256=digest.hexdigest(),
                prediction_bytes=expected_bytes, formal_training_runs=0,
                scope="Complete source inference identity/shape/finiteness; no GNN load/forward or supervised stress accuracy")
