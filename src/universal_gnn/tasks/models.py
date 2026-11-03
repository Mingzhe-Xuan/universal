from __future__ import annotations

import torch
from torch import nn

from universal_gnn.adapters import EquivariantAdapter, ScalarAdapter
from universal_gnn.data.geometry import strain_batch
from universal_gnn.properties import property_spec
from universal_gnn.readouts import PropertyReadout, ResponseReadout


class SupervisedModel(nn.Module):
    def __init__(self, backbone: nn.Module, spec, *, route: str | None = None,
                 adapter_width: int = 32, adapter_version: int = 2, prediction=None, feature_dim=None):
        super().__init__()
        self.backbone, self.spec = backbone, spec
        if prediction is not None:
            from universal_gnn.contracts.components import resolve_feature_spec
            from universal_gnn.readouts.factory import build_processing, build_readout

            self.route = "native"
            self.native_spec = resolve_feature_spec(backbone, feature_dim)
            backbone._prediction_feature_spec = self.native_spec
            if getattr(backbone, "irreps", None) is None:
                backbone.irreps = self.native_spec.irreps
            self.adapter, effective = build_processing(prediction["adapter"], self.native_spec)
            self.readout = build_readout(prediction["readout"], effective, spec,
                                        independent_equivariant=prediction["adapter"]["name"] == "equivariant")
            self.resolved_prediction = prediction
            self.prediction_descriptor = {"version": 1, "native_spec": self.native_spec.to_dict(),
                "backbone_cutoff": getattr(backbone, "cutoff", None), "adapter": prediction["adapter"],
                "adapter_output_spec": effective.to_dict() if self.adapter is not None else None,
                "readout": self.readout.descriptor, "graph_features_preserved": True}
            return
        self.route = route or ("common_equivariant" if backbone.kind == "equivariant"
                               and spec.construction == "derivative" else "invariant_alignn")
        if self.route == "common_equivariant":
            self.adapter = EquivariantAdapter(backbone.irreps, cutoff=backbone.cutoff,
                                              basis_version=adapter_version)
        elif self.route == "invariant_alignn":
            self.adapter = ScalarAdapter(backbone.irreps, adapter_width)
        else:
            raise ValueError(f"Unknown route {self.route}")
        self.readout = (ResponseReadout(self.adapter.irreps, self.adapter.kind, spec)
                        if spec.construction == "derivative" else PropertyReadout(self.adapter.irreps, spec))

    def forward(self, batch, context=None, *, create_graph=None):
        if hasattr(self, "native_spec"):
            from universal_gnn.contracts.components import validate_native_features

            features = self.backbone.encode(batch, context)
            validate_native_features(features, self.native_spec, batch)
            if self.adapter is not None:
                features = self.adapter(features)
            return self.readout(features, create_graph=create_graph)
        features = self.adapter(self.backbone.encode(batch, context))
        if self.spec.construction == "derivative":
            return self.readout(features, create_graph=create_graph)
        return self.readout(features)

    def train(self, mode=True):
        super().train(mode)
        from universal_gnn.engine.optimization import apply_component_modes

        apply_component_modes(self)
        return self


class ForceFieldModel(nn.Module):
    def __init__(self, backbone: nn.Module, *, prediction=None, feature_dim=None):
        super().__init__()
        if prediction is not None and prediction.get("head_mode") == "native":
            from .native import NativeTaskModel

            self.energy_model = NativeTaskModel(backbone, property_spec("total_energy"),prediction=prediction,
                                                 feature_dim=feature_dim,forcefield=True)
        else:
            self.energy_model = SupervisedModel(backbone, property_spec("total_energy"), prediction=prediction, feature_dim=feature_dim)
        if prediction is not None:
            for name, available in self.energy_model.native_spec.gradients.items():
                if not available:
                    raise ValueError(f"backbone feature gradients.{name}=false: new forcefield requires verified positions/strain/mixed gradients")

    @property
    def backbone(self):
        return self.energy_model.backbone

    def train(self, mode=True):
        super().train(mode)
        from universal_gnn.engine.optimization import apply_component_modes

        apply_component_modes(self)
        return self

    def forward(self, batch, *, create_graph=None):
        create_graph = self.training if create_graph is None else create_graph
        with torch.enable_grad():
            positions = (batch.positions if batch.positions.requires_grad else
                         batch.positions.detach().clone().requires_grad_(True))
            strain = batch.cell.new_zeros(batch.cell.shape, requires_grad=True)
            live = strain_batch(batch.with_geometry(positions, batch.cell), strain)
            energy = self.energy_model(live)
            # Explicit zeros permit isolated structures with geometry-independent atomic energies.
            energy = energy + 0 * (positions.sum() + strain.sum())
            position_grad, strain_grad = torch.autograd.grad(energy.sum(), (positions, strain),
                                                            create_graph=create_graph, retain_graph=True)
            volume = torch.linalg.det(batch.cell).abs()
            stress = strain_grad / volume[:, None, None] * 160.21766208
            return {"total_energy": energy, "forces": -position_grad, "stress": stress}
