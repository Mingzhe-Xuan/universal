"""Versioned native feature semantics, dimensions and readout input requirements."""

from dataclasses import asdict, dataclass, field

import torch

from .e3nn_compat import load_o3
from .types import NativeFeatures


@dataclass(frozen=True)
class FeatureSpec:
    feature_dim: int
    irreps: str
    kind: str
    basis: str
    transformation: str
    gradients: dict = field(default_factory=dict)
    source: str = "model.feature_spec"
    dimension_assertion: int | None = None
    version: int = 1

    @property
    def even_scalars(self):
        return all(ir.l == 0 and ir.p == 1 for _, ir in load_o3().Irreps(self.irreps))

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ReadoutRequirement:
    construction: str = "direct"
    scopes: tuple = ("graph", "node")
    even_scalars: bool = True
    uses_graph_features: bool = False


def positive_dimension(value, field_name):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def resolve_feature_spec(backbone, declared_feature_dim=None):
    supplied = getattr(backbone, "feature_spec", None)
    if callable(supplied):
        supplied = supplied()
    if isinstance(supplied, FeatureSpec):
        supplied = supplied.to_dict()
    if supplied is not None and not isinstance(supplied, dict):
        raise ValueError("backbone.feature_spec must be a FeatureSpec or mapping")
    values = dict(supplied or {})
    unknown = set(values) - set(FeatureSpec.__dataclass_fields__)
    if unknown:
        raise ValueError(f"backbone.feature_spec unknown fields: {sorted(unknown)}")
    if values.get("version", 1) != 1 or isinstance(values.get("version"), bool):
        raise ValueError("Unsupported backbone.feature_spec version")
    ir = values.get("irreps") or getattr(backbone, "irreps", None)
    dimensions = []
    if values.get("feature_dim") is not None:
        dimensions.append(("model.feature_spec", positive_dimension(values["feature_dim"], "feature_spec.feature_dim")))
    if ir is not None:
        dimensions.append(("model.irreps", load_o3().Irreps(ir).dim))
    if getattr(backbone, "feature_dim", None) is not None:
        dimensions.append(("model.feature_dim", positive_dimension(backbone.feature_dim, "model.feature_dim")))
    if declared_feature_dim is not None:
        dimensions.append(("backbone.feature_dim", positive_dimension(declared_feature_dim, "backbone.feature_dim")))
    if not dimensions:
        raise ValueError("backbone output dimension missing: declare feature_spec/irreps/feature_dim or backbone.feature_dim")
    source, width = dimensions[0]
    positive_dimension(width, source)
    if any(value != width for _, value in dimensions):
        raise ValueError(f"backbone.feature_dim declaration conflict: {dimensions}")
    kind = values.get("kind", getattr(backbone, "kind", None))
    if kind not in {"invariant", "equivariant"}:
        raise ValueError("backbone must declare invariant/equivariant feature semantics")
    if ir is None:
        if kind != "invariant":
            raise ValueError("Non-scalar equivariant features require irreps, basis and transformation; F alone is insufficient")
        ir = f"{width}x0e"
    ir = str(load_o3().Irreps(ir))
    scalar = all(v.l == 0 and v.p == 1 for _, v in load_o3().Irreps(ir))
    if kind == "invariant" and not scalar:
        raise ValueError("Invariant backbone features must be even scalars")
    basis = values.get("basis") or getattr(backbone, "basis", None) or ("scalar" if scalar else None)
    transform = values.get("transformation") or getattr(backbone, "transformation", None) or ("invariant" if scalar else None)
    if not isinstance(basis, str) or not basis or transform not in {"invariant", "O3", "SO3"}:
        raise ValueError("Non-scalar feature semantics require a declared basis and O3/SO3 transformation")
    if not scalar and transform == "invariant":
        raise ValueError("Non-scalar irreps cannot declare invariant transformation")
    gradients = values.get("gradients", getattr(backbone, "gradient_capabilities", {}))
    if not isinstance(gradients, dict) or set(gradients) - {"positions", "strain", "mixed"}:
        raise ValueError("feature gradients must declare positions/strain/mixed capabilities")
    if any(type(v) is not bool for v in gradients.values()):
        raise ValueError("feature gradient capabilities must be booleans")
    gradients = {name: gradients.get(name, False) for name in ("positions", "strain", "mixed")}
    return FeatureSpec(width, ir, kind, basis, transform, gradients, source, declared_feature_dim)


def validate_native_features(features, spec, geometry):
    expected = (len(geometry.numbers), spec.feature_dim)
    if not isinstance(features, NativeFeatures):
        raise TypeError("backbone.encode must return NativeFeatures")
    shape = tuple(features.nodes.shape) if isinstance(features.nodes, torch.Tensor) else type(features.nodes).__name__
    if shape != expected:
        raise ValueError(f"backbone output from {spec.source}, declared F={spec.feature_dim}: actual shape={shape}, required={expected}")
    if features.geometry is not geometry:
        raise ValueError("backbone NativeFeatures must retain the input geometry reference")
    if str(load_o3().Irreps(features.irreps)) != spec.irreps or features.kind != spec.kind:
        raise ValueError(f"backbone output semantics differ from declared feature spec: {spec.to_dict()}")
    for key in ("basis", "transformation"):
        if features.metadata.get(key, getattr(spec, key)) != getattr(spec, key):
            raise ValueError(f"backbone output {key} differs from declared feature spec")
    features.validate()
