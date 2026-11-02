"""Narrow compatibility for trusted e3nn constants, without weakening checkpoint loads."""

import torch
from contextlib import nullcontext


def load_o3():
    # e3nn 0.4.4 constants contain builtin slice indices; PyTorch >=2.6 needs them allowlisted.
    allowlist = getattr(torch.serialization, "safe_globals", None)
    with allowlist([slice]) if allowlist is not None else nullcontext():
        from e3nn import o3
    return o3
