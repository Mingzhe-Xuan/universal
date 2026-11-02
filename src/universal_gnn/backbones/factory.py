from __future__ import annotations

import importlib.util
from pathlib import Path

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
        path = Path(name.removeprefix("plugin:")) / "plugin.py"
        spec = importlib.util.spec_from_file_location("universal_user_backbone", path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load backbone plugin {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build_backbone(**kwargs)
    raise ValueError(f"Unknown backbone {name!r}; expected one of six built-ins or plugin:/path")
