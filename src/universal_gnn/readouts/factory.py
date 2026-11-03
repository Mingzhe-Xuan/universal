"""Native-feature readouts, explicit processing and an extensible registration contract."""

from dataclasses import asdict, dataclass, replace
import math

import torch
from torch import nn

from universal_gnn.adapters.features import EquivariantAdapter, invariant_width, scalar_features
from universal_gnn.contracts.components import FeatureSpec, ReadoutRequirement, validate_native_features
from universal_gnn.data.geometry import scatter_mean, scatter_sum
from .properties import ResponseReadout


@dataclass(frozen=True)
class Registration:
    factory: object
    requirement: ReadoutRequirement
    fields: tuple


READOUTS = {}


def register_readout(name, factory, *, requirement=None, fields=()):
    if not isinstance(name, str) or not name or name in READOUTS:
        raise ValueError(f"Readout name is empty or already registered: {name!r}")
    READOUTS[name] = Registration(factory, requirement or ReadoutRequirement(), tuple(fields))


class ScalarInvariants(nn.Module):
    def __init__(self, irreps):
        super().__init__()
        self.irreps = irreps

    def forward(self, features):
        return replace(features, nodes=scalar_features(features.nodes, self.irreps),
                       irreps=f"{invariant_width(self.irreps)}x0e", kind="invariant")


class FeatureProcessing(nn.Module):
    def __init__(self, operation, spec):
        super().__init__()
        self.operation, self.output_spec = operation, spec

    def forward(self, features):
        output = self.operation(features)
        output = replace(output, metadata={**output.metadata, "basis": self.output_spec.basis,
                                           "transformation": self.output_spec.transformation})
        validate_native_features(output, self.output_spec, features.geometry)
        return output


def build_processing(config, spec):
    name = config["name"]
    if name == "none":
        return None, spec
    if not spec.even_scalars and spec.basis != "e3nn/component":
        raise ValueError(f"feature_processing requires e3nn/component basis; actual {spec.basis!r}")
    if name == "scalar_invariants":
        width = invariant_width(spec.irreps)
        out = replace(spec, feature_dim=width, irreps=f"{width}x0e", kind="invariant", basis="scalar",
                      transformation="SO3" if spec.transformation == "SO3" else "invariant", source="scalar_invariants", dimension_assertion=None)
        return FeatureProcessing(ScalarInvariants(spec.irreps), out), out
    if "cutoff" not in config:
        raise ValueError("equivariant feature_processing requires an explicit cutoff or backbone.cutoff")
    operation = EquivariantAdapter(spec.irreps, cutoff=config["cutoff"], basis_version=config["basis_version"])
    from universal_gnn.contracts.e3nn_compat import load_o3

    out = replace(spec, feature_dim=load_o3().Irreps(operation.irreps).dim, irreps=str(load_o3().Irreps(operation.irreps)),
                  kind="equivariant", basis="e3nn/component",
                  transformation="SO3" if spec.transformation == "SO3" else "O3", source="equivariant.small_response", dimension_assertion=None)
    return FeatureProcessing(operation, out), out


def aggregate(nodes, features, pooling):
    if pooling == "none":
        return nodes
    operation = scatter_sum if pooling == "sum" else scatter_mean
    return operation(nodes, features.batch, features.geometry.num_graphs)


class DirectReadout(nn.Module):
    def __init__(self, settings, features, spec):
        super().__init__()
        self.name, self.pooling, self.spec = settings["name"], settings["pooling"], spec
        widths = [features.feature_dim, *settings.get("hidden_features", []), math.prod(spec.shape)]
        layers = []
        for i, (before, after) in enumerate(zip(widths, widths[1:])):
            layers.append(nn.Linear(before, after, bias=settings["bias"]))
            if i < len(widths) - 2:
                layers.append(nn.SiLU())
        self.network = nn.Sequential(*layers)

    def forward(self, features):
        if self.name in {"linear", "graph_mlp"}:
            output = self.network(aggregate(features.nodes, features, self.pooling))
        else:
            output = aggregate(self.network(features.nodes), features, self.pooling)
        return output.reshape(len(output), *self.spec.shape)


class ConfiguredReadout(nn.Module):
    def __init__(self, core, processing, input_spec, effective_spec, property_spec, settings, registration, guarantee):
        super().__init__()
        self.core, self.processing = core, processing
        self.input_spec, self.effective_spec, self.spec = input_spec, effective_spec, property_spec
        self.derivative = registration.requirement.construction == "derivative"
        self.descriptor = {"config": settings, "input_spec": input_spec.to_dict(),
                           "effective_spec": effective_spec.to_dict(), "output_spec": property_spec.to_dict(),
                           "requirements": asdict(registration.requirement), "transformation_guarantee": guarantee,
                           "implementation": registration.factory.__module__ + "." + registration.factory.__qualname__,
                           "pooling_position": "before_network" if settings["name"] in {"linear", "graph_mlp", "response"} else "after_network",
                           "graph_features_used": registration.requirement.uses_graph_features}

    def forward(self, features, *, create_graph=None):
        validate_native_features(features, self.input_spec, features.geometry)
        if self.processing is not None:
            features = self.processing(features)
        output = self.core(features, create_graph=create_graph) if self.derivative else self.core(features)
        leading = features.geometry.num_graphs if self.spec.scope == "graph" else len(features.nodes)
        expected = (leading, *self.spec.shape)
        if not isinstance(output, torch.Tensor) or tuple(output.shape) != expected:
            raise ValueError(f"readout output shape={getattr(output, 'shape', None)}, required {expected}")
        if output.device != features.nodes.device or output.dtype != features.nodes.dtype:
            raise ValueError("readout output must preserve feature dtype/device")
        if not bool(torch.isfinite(output).all()):
            raise FloatingPointError("Nonfinite readout output")
        return output


def build_readout(settings, features, spec, *, independent_equivariant=False):
    registration = READOUTS[settings["name"]]
    processing, effective = build_processing(settings["feature_processing"], features)
    if registration.requirement.even_scalars and not effective.even_scalars:
        raise ValueError(f"readout {settings['name']} requires even scalar features; actual {effective.irreps}. Select explicit scalar_invariants processing")
    if settings["name"] == "response":
        equivariant = settings["feature_processing"]["name"] == "equivariant" or (
            independent_equivariant and settings["feature_processing"]["name"] == "none")
        if not equivariant and not effective.even_scalars:
            raise ValueError("response requires explicit equivariant or scalar_invariants feature_processing for non-scalar inputs")
        core = ResponseReadout(effective.irreps, "equivariant" if equivariant else "invariant", spec)
        guarantee = ("SO3_cartesian" if effective.transformation == "SO3" else "O3_cartesian") if equivariant else "fixed_frame_components"
    else:
        core = registration.factory(settings, effective, spec)
        guarantee = "fixed_frame_components" if len(spec.shape) > 1 else ("SO3_invariant" if effective.transformation == "SO3" else "invariant")
    return ConfiguredReadout(core, processing, features, effective, spec, settings, registration, guarantee)


register_readout("linear", DirectReadout, fields=("bias",))
register_readout("graph_mlp", DirectReadout, requirement=ReadoutRequirement(scopes=("graph",)),
                 fields=("hidden_features", "activation", "bias"))
register_readout("node_mlp", DirectReadout, fields=("hidden_features", "activation", "bias"))
register_readout("response", ResponseReadout,
                 requirement=ReadoutRequirement(construction="derivative", even_scalars=False))
