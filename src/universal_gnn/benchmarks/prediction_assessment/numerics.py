"""Numerical work used only by CPU Slurm post-processing."""

from contextlib import contextmanager
import gc
from pathlib import Path
from unittest.mock import patch

from .contracts import full_inference_config


def peak_rss_bytes():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def trained_physics(checkpoint, config, indices):
    from universal_gnn.engine.training import dataset, load_checkpoint
    from ..validation.derivatives import validate_derivatives
    model = load_checkpoint(checkpoint, device="cpu").eval()
    structures = dataset(config)
    try:
        return validate_derivatives(model, [structures[i] for i in indices], config)
    finally:
        del model, structures
        gc.collect()


def complete_inference(checkpoint, config, output):
    from universal_gnn.engine.inference import run_inference
    return run_inference(checkpoint, config["dataset"]["path"], Path(output), device="cpu", limit=None,
                         config_override=full_inference_config(config))


@contextmanager
def forbid_models():
    """Tensor-only CPU softmax remains allowed; model loads/forwards are forbidden."""
    import torch
    def refused(*args, **kwargs):
        raise RuntimeError("Independent prediction validation must not load or run a GNN")
    with patch.object(torch, "load", refused), patch.object(torch.jit, "load", refused), \
            patch.object(torch.nn.Module, "__call__", refused):
        yield
