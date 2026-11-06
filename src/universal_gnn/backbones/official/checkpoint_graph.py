"""Narrow source compatibility for restoring an already trained periodic model."""

from contextlib import contextmanager
from contextvars import ContextVar
import copy
from types import MethodType

_RESTORING = ContextVar('ugnn_checkpoint_graph_restore', default=False)
LEGACY_NEQUIP_SOURCE = 'ad4518cabfc7e01e4204c22538fcfe8f85312ad4cec6c55eca5f3294d861363a'
PERIODIC_NEQUIP_SOURCE = '5eb20819c711846f0df036f4414bcb92472b5573ac835a7567b823653c2b9a17'
_FIELDS = {'artifact_sha256', 'adapter_source_sha256', 'provider_version', 'ase_version', 'torch_version'}


@contextmanager
def checkpoint_graph_restore():
    """Only checkpoint reconstruction opens this scope; fresh training stays strict."""
    token = _RESTORING.set(True)
    try:
        yield
    finally:
        _RESTORING.reset(token)


def restored_graph_compatibility(previous, current, *, provider):
    if not _RESTORING.get() or provider != 'nequip':
        return None
    if not isinstance(previous, dict) or not isinstance(current, dict) or set(previous) != _FIELDS or set(current) != _FIELDS:
        return None
    if (previous['adapter_source_sha256'] != LEGACY_NEQUIP_SOURCE or
            current['adapter_source_sha256'] != PERIODIC_NEQUIP_SOURCE):
        return None
    if any(previous[key] != current[key] for key in _FIELDS - {'adapter_source_sha256'}):
        return None
    # The only native_input change wraps neighbors(mapper(data)) in the helper
    # that returns its original data for all-periodic inputs. Other PBC domains
    # changed behavior, so the restored model must enforce this scope at runtime.
    return dict(kind='nequip_known_periodic_graph_source_restore', allowed_pbc='fully_periodic_only',
                original_native_graph=copy.deepcopy(previous), runtime_native_graph=copy.deepcopy(current),
                statistics_recalibrated=False,
                reason='Known adapter source change preserves fully periodic neighbor inputs; nonperiodic and partial-PBC inputs are refused')


def _periodic_native_input(self, batch):
    pbc = getattr(batch, 'pbc', None)
    graphs = getattr(batch, 'num_graphs', 0)
    if (type(graphs) is not int or graphs < 1 or pbc is None or tuple(pbc.shape) != (graphs, 3) or
            str(pbc.dtype) != 'torch.bool' or not bool(pbc.all())):
        raise ValueError('Restored legacy NequIP neighbor statistics require fully periodic inputs; use a checkpoint with a matching input implementation for other PBC profiles')
    return type(self).native_input(self, batch)


def install_periodic_restore_guard(backbone, compatibility):
    backbone._checkpoint_graph_compatibility = copy.deepcopy(compatibility)
    backbone.native_input = MethodType(_periodic_native_input, backbone)
