from __future__ import annotations

import torch
from torch import nn

from universal_gnn.adapters import EquivariantAdapter, ScalarAdapter
from universal_gnn.data.geometry import strain_batch
from universal_gnn.properties import property_spec
from universal_gnn.readouts import PropertyReadout, ResponseReadout


class SupervisedModel(nn.Module):
    def __init__(self, backbone: nn.Module, spec, *, route: str | None = None,
                 adapter_width: int = 32, adapter_version: int = 2):
        super().__init__()
        self.backbone, self.spec = backbone, spec
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
        features = self.adapter(self.backbone.encode(batch, context))
        if self.spec.construction == "derivative":
            return self.readout(features, create_graph=create_graph)
        return self.readout(features)


class ForceFieldModel(nn.Module):
    def __init__(self, backbone: nn.Module):
        super().__init__()
        self.energy_model = SupervisedModel(backbone, property_spec("total_energy"))

    @property
    def backbone(self):
        return self.energy_model.backbone

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
