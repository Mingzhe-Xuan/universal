from __future__ import annotations

from .invariant import ALIGNNEncoder, CGCNNEncoder, MEGNetEncoder


def make_backbone(name: str, *, graph_config=None, **kwargs):
    if name == "gcn" or name.startswith("plugin:"):
        from universal_gnn.backbones.standard import StandardBackbone
        from universal_gnn.contracts import BaseGNN
        from universal_gnn.data.graphs import make_graph_builder

        cutoff = kwargs.get("cutoff", 4.)
        if name == "gcn":
            from .gcn import GCN

            kwargs.pop("cutoff", None)
            gnn = GCN(**kwargs)
        else:
            from universal_gnn.contracts.plugins import load_plugin

            module = load_plugin(name.removeprefix("plugin:"))
            if not hasattr(module, "build_gnn"):
                if graph_config is not None:
                    raise ValueError("Independent graph selection requires a build_gnn plugin")
                backbone = module.build_backbone(**kwargs)
                backbone.extension_provenance = {"legacy_backbone": {**module.__ugnn_provenance__,
                                                                       "factory": "build_backbone"}}
                return backbone
            kwargs.pop("cutoff", None)
            gnn = module.build_gnn(**kwargs)
            if not isinstance(gnn, BaseGNN):
                raise TypeError("build_gnn must return a BaseGNN")
            gnn.extension_provenance = {**module.__ugnn_provenance__, "factory": "build_gnn"}
        return StandardBackbone(gnn, make_graph_builder(graph_config or {"name": "knn"}), cutoff=cutoff)
    if graph_config is not None:
        raise ValueError("This native backbone builds its own graph; graph selection requires gcn or build_gnn")
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
    raise ValueError(f"Unknown backbone {name!r}; expected a built-in or plugin:/path")
