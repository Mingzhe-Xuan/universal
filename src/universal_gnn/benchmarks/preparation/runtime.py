"""Lazy numerical operations; public preparation orchestration imports no Torch."""

from pathlib import Path
import sys

from .specification import reference_examples


def load_training(config):
    from universal_gnn.engine.training import dataset
    return dataset(config)


def native_parity(structures, config):
    import torch
    from universal_gnn.backbones.factory import make_backbone
    from universal_gnn.engine.batching import model_dtype

    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
    from validate_official import independent_reference
    examples, reference = reference_examples(structures, config)
    torch.manual_seed(config["seed"])
    options = {key: value for key, value in config["backbone"].items() if key != "name"}
    backbone = make_backbone(config["backbone"]["name"], **options).to(dtype=model_dtype(config)).eval()
    return independent_reference(backbone, examples, reference)


def graph_scan(config, output):
    from ..probes.native_scan import scan_training_graphs
    return scan_training_graphs(config, output, warmup_batches=2, measure_batches=100)


def paired_capacity(configs, output, probe, timeout):
    from ..pairing.capacity import run_paired_capacity
    return run_paired_capacity(configs, output, probe=probe, timeout=timeout)


def derivatives(structures, config):
    import torch
    from universal_gnn.engine.training import build_model
    from universal_gnn.engine.batching import model_dtype
    from ..validation.derivatives import validate_derivatives

    torch.manual_seed(config["seed"])
    model = build_model(config).to(device=config["device"], dtype=model_dtype(config))
    try:
        return validate_derivatives(model, structures, config)
    finally:
        del model
        torch.cuda.empty_cache()
