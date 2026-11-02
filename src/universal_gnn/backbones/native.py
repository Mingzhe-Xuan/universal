from __future__ import annotations

import inspect
from collections import OrderedDict
from importlib.metadata import version

import numpy as np
import torch
from torch import nn

from universal_gnn.contracts import NativeFeatures
from universal_gnn.contracts.e3nn_compat import load_o3
from universal_gnn.data.geometry import radius_graph

o3 = load_o3()


class MACEEncoder(nn.Module):
    """Official MACE interaction/product modules, exposed before energy readouts."""

    kind = "equivariant"

    def __init__(self, width=32, layers=2, cutoff=4., radial=8, context_dim=0):
        super().__init__()
        from mace.modules import MACE, RealAgnosticInteractionBlock, RealAgnosticResidualInteractionBlock

        channels = max(4, width // 4)
        self.cutoff = cutoff
        hidden = o3.Irreps(f"{channels}x0e + {channels}x1o + {channels}x2e")
        arguments = dict(r_max=cutoff, num_bessel=radial, num_polynomial_cutoff=5, max_ell=2,
                         interaction_cls=RealAgnosticResidualInteractionBlock,
                         interaction_cls_first=RealAgnosticInteractionBlock,
                         num_interactions=max(2, layers), num_elements=118,
                         hidden_irreps=hidden, MLP_irreps=o3.Irreps(f"{channels}x0e"),
                         atomic_energies=np.zeros(118), avg_num_neighbors=12.,
                         atomic_numbers=list(range(1, 119)), correlation=2,
                         gate=torch.nn.functional.silu, radial_MLP=[width, width])
        if "keep_last_layer_irreps" in inspect.signature(MACE).parameters:
            arguments["keep_last_layer_irreps"] = True
        model = MACE(**arguments)
        self.embedding = model.node_embedding
        self.harmonics = model.spherical_harmonics
        self.radial = model.radial_embedding
        self.interactions, self.products = model.interactions, model.products
        self.register_buffer("atomic_numbers", model.atomic_numbers.clone())
        self.context_projection = nn.Linear(context_dim, channels, bias=False) if context_dim else None
        irreps = o3.Irreps("")
        for product in self.products:
            irreps = irreps + product.linear.irreps_out
        self.irreps = str(irreps)
        self.backend_version = version("mace-torch")

    def encode(self, batch, context=None):
        graph = radius_graph(batch, self.cutoff)
        node_attrs = nn.functional.one_hot(batch.numbers - 1, 118).to(batch.positions.dtype)
        nodes = self.embedding(node_attrs)
        if self.context_projection is not None:
            if context is None:
                raise ValueError("MACE conditioned encoder requires context")
            nodes = nodes + self.context_projection(context)[batch.batch]
        edge_attrs = self.harmonics(-graph.vectors)
        edges, cutoff = self.radial(graph.distances[:, None], node_attrs,
                                    graph.edge_index, self.atomic_numbers)
        outputs = []
        for i, (interaction, product) in enumerate(zip(self.interactions, self.products)):
            kwargs = dict(node_attrs=node_attrs, node_feats=nodes, edge_attrs=edge_attrs,
                          edge_feats=edges, edge_index=graph.edge_index)
            parameters = inspect.signature(interaction.forward).parameters
            if "cutoff" in parameters:
                kwargs["cutoff"] = cutoff
            if "first_layer" in parameters:
                kwargs["first_layer"] = i == 0
            nodes, skip = interaction(**kwargs)
            nodes = product(node_feats=nodes, sc=skip, node_attrs=node_attrs)
            outputs.append(nodes)
        return NativeFeatures(torch.cat(outputs, dim=-1), self.irreps, self.kind,
                              batch.batch, batch.ptr, batch, metadata={"implementation": "mace.modules",
                              "version": self.backend_version, "layers": "all_product_blocks"})

    forward = encode


class NequIPEncoder(nn.Module):
    """Official NequIP embedding and ConvNetLayer stack, stopping before scalar collapse."""

    kind = "equivariant"

    def __init__(self, width=32, layers=2, cutoff=4., radial=8, context_dim=0):
        super().__init__()
        from ase.data import chemical_symbols
        from nequip.model.nequip_models import FullNequIPGNNModel
        from nequip.nn import SequentialGraphNetwork
        from nequip.utils.global_state import set_global_state

        self.cutoff = cutoff
        channels = max(4, width // 4)
        hidden = f"{channels}x0e + {channels}x1o + {channels}x2e"
        previous_dtype = torch.get_default_dtype()
        with torch.random.fork_rng(devices=[]):
            set_global_state()
            built = FullNequIPGNNModel(seed=123, model_dtype="float64", r_max=cutoff,
                type_names=chemical_symbols[1:119], radial_mlp_depth=[1] * (layers + 1),
                radial_mlp_width=[width] * (layers + 1),
                feature_irreps_hidden=[hidden] * layers + [f"{channels}x0e"],
                irreps_edge_sh=str(o3.Irreps.spherical_harmonics(2)),
                type_embed_num_features=channels, num_bessels=radial,
                avg_num_neighbors=12., per_type_energy_scales=1., per_type_energy_shifts=0.)
        torch.set_default_dtype(previous_dtype)
        network = next(module for module in built.modules()
                       if isinstance(module, SequentialGraphNetwork) and "type_embed" in module._modules)
        modules = OrderedDict()
        for name, module in network.named_children():
            if name == f"layer{layers}_convnet":
                break
            modules[name] = module
        if not modules or f"layer{layers - 1}_convnet" not in modules:
            raise RuntimeError("Unsupported NequIP module layout; refusing scalar-only fallback")
        self.trunk = nn.ModuleDict(modules)
        self.irreps = str(list(modules.values())[-1].irreps_out["node_features"])
        self.context_projection = nn.Linear(context_dim, channels, bias=False) if context_dim else None
        self.backend_version = version("nequip")

    def encode(self, batch, context=None):
        graph = radius_graph(batch, self.cutoff)
        data = {"pos": batch.positions, "cell": batch.cell, "pbc": batch.pbc,
                "batch": batch.batch, "ptr": batch.ptr, "atom_types": batch.numbers - 1,
                "edge_index": torch.stack([graph.dst, graph.src]),
                "edge_cell_shift": graph.images.to(batch.positions.dtype),
                "edge_vectors": graph.vectors, "edge_lengths": graph.distances}
        for name, module in self.trunk.items():
            data = module(data)
            if name == "type_embed" and self.context_projection is not None:
                if context is None:
                    raise ValueError("NequIP conditioned encoder requires context")
                data["node_features"] = data["node_features"] + self.context_projection(context)[batch.batch]
        return NativeFeatures(data["node_features"], self.irreps, self.kind,
                              batch.batch, batch.ptr, batch, metadata={"implementation": "nequip.nn",
                              "version": self.backend_version, "layers": list(self.trunk)})

    forward = encode
