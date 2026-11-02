"""Shared artifact provenance and output-only conditioning; original modules stay intact."""

import hashlib
from pathlib import Path

import torch
from torch import nn

from universal_gnn.contracts import NativeFeatures


def artifact_files(provider, files, *, artifact=None, source=None):
    if artifact is not None:
        if artifact["provider"] != provider:
            raise ValueError("Embedded official artifact has the wrong provider")
        for name, content in artifact["files"].items():
            if hashlib.sha256(content).hexdigest() != artifact["sha256"][name]:
                raise ValueError(f"Embedded official artifact checksum mismatch: {name}")
        return artifact
    if any(path is None for path in files.values()):
        raise ValueError(f"Official {provider} requires source artifact files: {sorted(files)}")
    contents = {name: Path(path).read_bytes() for name, path in files.items()}
    return {"version": 1, "provider": provider, "source": source, "files": contents,
            "sha256": {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()}}


class ReferenceValue(torch.autograd.Function):
    """Keep an original preprocessing value exactly; differentiate its equivalent Torch expression."""

    @staticmethod
    def forward(ctx, reference, differentiable):
        return reference.clone()

    @staticmethod
    def backward(ctx, gradient):
        return None, gradient


class _ReadoutReached(Exception):
    def __init__(self, features):
        self.features = features


def capture_features(forward, module, extract, *, before=False):
    """Stop the original forward at its readout boundary, leaving every trunk operation intact."""
    def pre_hook(current, inputs):
        raise _ReadoutReached(extract(inputs))

    def post_hook(current, inputs, output):
        raise _ReadoutReached(extract(output))

    handle = module.register_forward_pre_hook(pre_hook) if before else module.register_forward_hook(post_hook)
    try:
        forward()
    except _ReadoutReached as reached:
        return reached.features
    finally:
        handle.remove()
    raise RuntimeError("Original model did not reach the configured readout boundary")


class OfficialBackbone(nn.Module):
    def __init__(self, model, irreps, kind, cutoff, artifact, *, context_dim=0, version=None):
        super().__init__()
        self.model = model
        self.feature_irreps = str(irreps)
        self.irreps = str(irreps) + (f" + {context_dim}x0e" if context_dim else "")
        self.kind, self.cutoff, self.context_dim = kind, float(cutoff), context_dim
        self.official_artifact, self.backend_version = artifact, version
        self.load_report = {"strict": True, "parameter_coverage": 1., "buffer_coverage": 1.,
                            "sha256": artifact["sha256"], "source": artifact.get("source"),
                            "native_class": type(model).__module__ + "." + type(model).__name__}

    def output(self, nodes, batch, context=None):
        if self.context_dim:
            if context is None or context.shape != (batch.num_graphs, self.context_dim):
                raise ValueError("Official backbone output adapter requires per-structure context")
            nodes = torch.cat((nodes, context[batch.batch]), dim=-1)
        elif context is not None:
            raise ValueError("Unexpected context for an unconditioned official backbone")
        result = NativeFeatures(nodes, self.irreps, self.kind, batch.batch, batch.ptr, batch,
                                metadata={"implementation": "official", **self.load_report})
        result.validate()
        return result

    def forward(self, batch, context=None):
        return self.encode(batch, context)
