"""Narrow compatibility for trusted e3nn constants, without weakening checkpoint loads."""

import torch


def load_o3():
    # e3nn 0.4.4 constants contain builtin slice indices; PyTorch >=2.6 needs them allowlisted.
    with torch.serialization.safe_globals([slice]):
        from e3nn import o3
    return o3
