"""Deterministic minibatches, bounded geometry memory and explicit precision."""

import torch

from universal_gnn.contracts import StructureBatch


def model_dtype(config, *, legacy=False):
    name = config.get("dtype", "float64" if legacy else "float32")
    if name not in {"float32", "float64"}:
        raise ValueError("dtype must be float32 or float64")
    return getattr(torch, name)


def validate_batching(config):
    model_dtype(config)
    for key in ("batch_size", "max_atoms"):
        value = config.get(key, 32 if key == "batch_size" else None)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
            raise ValueError(f"{key} must be a positive integer")
    if not isinstance(config.get("shuffle", True), bool):
        raise ValueError("shuffle must be boolean")


def batch_indices(structures, config, *, epoch=None):
    validate_batching(config)
    indices = range(len(structures))
    if epoch is not None and config.get("shuffle", True):
        generator = torch.Generator().manual_seed(config.get("seed", 123) + epoch)
        indices = torch.randperm(len(structures), generator=generator).tolist()
    batch, atoms = [], 0
    for index in indices:
        size = len(structures[index].numbers) if config.get("max_atoms") else 0
        if config.get("max_atoms") and size > config["max_atoms"]:
            raise ValueError(f"Structure {index} has {size} atoms, exceeding max_atoms")
        if batch and (len(batch) >= config.get("batch_size", 32) or
                      (config.get("max_atoms") and atoms + size > config["max_atoms"])):
            yield batch
            batch, atoms = [], 0
        batch.append(index)
        atoms += size
    if batch:
        yield batch


def batches(structures, config, *, epoch=None):
    for indices in batch_indices(structures, config, epoch=epoch):
        yield StructureBatch.from_structures([structures[i] for i in indices]).to(
            device=config.get("device", "cpu"), dtype=model_dtype(config))


def continuation_settings(config):
    return {"batch_size": config.get("batch_size", 32), "max_atoms": config.get("max_atoms"),
            "shuffle": config.get("shuffle", True), "dtype": str(model_dtype(config)),
            "selection": config.get("dataset", {}).get("selection", "first")}
