from .properties import PropertyReadout, ResponseReadout

# Import the registry lazily through these accessors, preserving legacy module initialization.
def register_readout(*args, **kwargs):
    from .factory import register_readout as register

    return register(*args, **kwargs)

__all__ = ["PropertyReadout", "ResponseReadout", "register_readout"]
