"""Independent conditional sampling quality using a validation-selected checkpoint."""

import hashlib
import json
from pathlib import Path

from .protocol import condition_indices, nonnegative_integer
from .structure_quality import StructuralQuality



def structure_record(structure):
    return {"id": structure.identifier, "numbers": structure.numbers.cpu().tolist(),
            "positions": structure.positions.detach().cpu().tolist(), "cell": structure.cell.detach().cpu().tolist(),
            "pbc": structure.pbc.cpu().tolist()}



def condition_template(reference, volume_per_atom):
    """Expose only numbers/N/PBC to the sampler; erase reference geometry/labels."""
    from dataclasses import replace
    import torch

    count = len(reference.numbers)
    length = (count * volume_per_atom) ** (1 / 3)
    return replace(reference, positions=torch.zeros_like(reference.positions),
                   cell=torch.eye(3, dtype=reference.cell.dtype, device=reference.cell.device) * length,
                   targets={}, graph=None, metadata={"condition_id": reference.identifier})


def run_generation_quality(checkpoint, output, *, count=1000, draws_per_condition=5, seed=456,
                           device=None, distance_threshold=.5):
    import torch
    from universal_gnn.contracts import StructureBatch
    from universal_gnn.data.indexed import SelectedStructures
    from universal_gnn.data.splits.loading import load_partition
    from universal_gnn.engine.batching import model_dtype
    from universal_gnn.engine.evaluation.heldout import file_sha256, verified_best
    from universal_gnn.engine.evaluation.selection import ValidationTracker
    from universal_gnn.engine.runtime import checkpoint_config
    from universal_gnn.engine.training import dataset, execution_record, load_checkpoint, version_record

    nonnegative_integer(count, "sample count")
    nonnegative_integer(draws_per_condition, "draws per condition")
    if not count or not draws_per_condition or count % draws_per_condition:
        raise ValueError("Positive sample count must be divisible by positive draws_per_condition")
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    config = checkpoint_config(saved)
    if config["task"]["kind"] != "generation":
        raise ValueError("Independent generation evaluation requires a generation checkpoint")
    state = saved.get("training_state", {})
    selection = state.get("evaluation")
    if selection is None:
        raise ValueError("Supply the last training checkpoint with its validation selection history")
    training = dataset(config)
    test_indices, manifest, manifest_sha = load_partition(training.source, config["dataset"], partition="test")
    options = config.get("evaluation", {})
    tracker = ValidationTracker(manifest_sha, patience=options.get("patience"), min_delta=options.get("min_delta", 0.),
                                state=selection["tracker"])
    if len(tracker.state["history"]) != state["completed_epochs"]:
        raise ValueError("Validation selection history differs from completed training epochs")
    best = verified_best(selection)
    if file_sha256(best) != selection["best_sha256"]:
        raise ValueError("Changed validation-best checkpoint")
    test = SelectedStructures(training.source, test_indices)
    ids = [training.source.identifiers[index] for index in test_indices]
    selected = condition_indices(ids, count=count // draws_per_condition, seed=seed)
    prior = config.get("generation_prior", {})
    if prior.get("sampling_volume_source") != "train_fit":
        raise ValueError("This quality protocol requires a fitted training-only cell prior")
    volume = prior["statistics"]["volume_per_atom"]
    sampling = dict(config["task"].get("sampling", {}))
    if "steps" not in sampling or "inner_steps" not in sampling:
        raise ValueError("Quality evaluation requires explicit predeclared sampling steps and inner_steps")
    if sampling.get("volume_per_atom") != volume or prior["statistics"]["structures"] != len(training):
        raise ValueError("Sampling prior differs from the fitted training protocol")
    sampling.pop("seed", None)
    target_device = device or config.get("device", "cpu")
    model = load_checkpoint(best, device=target_device)
    scorer = StructuralQuality(training, distance_threshold=distance_threshold, record=structure_record)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    condition_hash = hashlib.sha256()
    with (output / "samples.jsonl").open("x", encoding="utf-8") as stream:
        for index, draw in ((index, draw) for index in selected for draw in range(draws_per_condition)):
            reference = test[index]
            payload = json.dumps(["ugnn-generation-sample-v1", seed, reference.identifier, draw], separators=(",", ":")).encode()
            local_seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63)
            condition_hash.update(payload + b"\n")
            template = condition_template(reference, volume)
            batch = StructureBatch.from_structures([template]).to(device=target_device, dtype=model_dtype(config))
            failure = None
            try:
                generated = model.sample(batch, seed=local_seed, **sampling)
                record = {"id": reference.identifier, "numbers": generated.numbers.cpu().tolist(),
                          "positions": generated.positions.cpu().tolist(), "cell": generated.cell[0].cpu().tolist(),
                          "pbc": generated.pbc[0].cpu().tolist()}
            except FloatingPointError as error:
                record, failure = None, str(error)
            metrics = scorer.update(record, structure_record(reference), failure=failure)
            stream.write(json.dumps({"condition_id": reference.identifier, "draw": draw, "sampling_seed": local_seed,
                                     "structure": record, "quality": metrics}, allow_nan=False) + "\n")
            stream.flush()
    result = scorer.result()
    if result["attempted"] != count:
        raise RuntimeError("Generation sample count differs from the declared protocol")
    result.update(execution_complete=True, requested_samples=count, seed=seed, sampling_batch_size=1,
                  draws_per_condition=draws_per_condition, selected_test_conditions=len(selected),
                  sampling=sampling, conditioning="given composition and atom count", partition="test",
                  source_sha256=manifest["source_sha256"], manifest_sha256=manifest_sha,
                  condition_sha256=condition_hash.hexdigest(), available_test_conditions=len(test),
                  training_structures=len(training), declared_training_structures=manifest["counts"]["train"],
                  full_training_partition=len(training) == manifest["counts"]["train"],
                  meets_v1_sample_count=count >= 1000, training_prior=prior,
                  checkpoint_role="validation_best", checkpoint_sha256=selection["best_sha256"],
                  selection=selection, execution=execution_record(model), versions=version_record(),
                  samples=str(output / "samples.jsonl"))
    (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result
