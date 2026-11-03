"""Geometry exports load on demand; split metadata tools do not require Torch."""

__all__ = ["PeriodicGraph", "radius_graph", "scatter_mean", "scatter_sum", "strain_batch"]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(".geometry", __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
