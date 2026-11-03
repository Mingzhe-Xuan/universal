__all__ = ["ALIGNNEncoder", "CGCNNEncoder", "MEGNetEncoder"]


def __getattr__(name):
    if name in __all__:
        from . import invariant

        value = getattr(invariant, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
