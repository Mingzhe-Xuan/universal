from __future__ import annotations

from .invariant import ALIGNNEncoder, CGCNNEncoder, MEGNetEncoder


def make_backbone(name: str, **kwargs):
    if name == "mace":
        from .native import MACEEncoder
        return MACEEncoder(**kwargs)
    if name == "nequip":
        from .native import NequIPEncoder
        return NequIPEncoder(**kwargs)
    if name == "equiformer":
        from .equiformer import EquiformerEncoder
        return EquiformerEncoder(**kwargs)
    factories = {"alignn": ALIGNNEncoder, "cgcnn": CGCNNEncoder, "megnet": MEGNetEncoder}
    if name in factories:
        return factories[name](**kwargs)
    if name.startswith("plugin:"):
        from universal_gnn.contracts.plugins import load_plugin

        module = load_plugin(name.removeprefix("plugin:"))
        return module.build_backbone(**kwargs)
    raise ValueError(f"Unknown backbone {name!r}; expected one of six built-ins or plugin:/path")
