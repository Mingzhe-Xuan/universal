"""Exact checkpoint state and reproducible prediction comparison, without training changes."""
from contextlib import contextmanager

import torch


@contextmanager
def checkpoint_verification(expected, actual):
    first, second = expected.state_dict(), actual.state_dict()
    if first.keys() != second.keys():
        raise ValueError('Checkpoint verification state keys differ')
    for name, value in first.items():
        other = second[name]
        if (value.shape != other.shape or value.dtype != other.dtype or
                not torch.equal(value, other.to(device=value.device))):
            raise ValueError('Checkpoint verification state differs: '+name)
    previous = torch.are_deterministic_algorithms_enabled()
    warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True, warn_only=False)
    try:
        yield {'state_exact': True, 'state_tensors': len(first), 'deterministic_algorithms': True,
               'scope': 'reload prediction comparison only; training and prediction tolerances unchanged'}
    finally:
        torch.use_deterministic_algorithms(previous, warn_only=warn_only)
