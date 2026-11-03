"""Original task head selection without replacing modules or duplicating state."""

import math

import torch
from torch import nn

from universal_gnn.contracts.components import resolve_feature_spec
from universal_gnn.contracts.native import NativeTaskContract
from universal_gnn.engine.component_views import native_component_views


class NativeTaskModel(nn.Module):
    def __init__(self, backbone, spec, *, prediction, feature_dim=None, forcefield=False):
        super().__init__()
        if not callable(getattr(backbone,"native_task_contract",None)) or not callable(getattr(backbone,"native_prediction",None)):
            raise ValueError("prediction.head_mode=native requires a backbone with an explicit original-head task contract")
        if getattr(backbone,"context_dim",0):
            raise ValueError("prediction.head_mode=native cannot add conditioning to the original task")
        self.backbone,self.spec,self.adapter,self.route=backbone,spec,None,"official_native"
        self.native_contract=backbone.native_task_contract()
        if not isinstance(self.native_contract,NativeTaskContract):raise TypeError("native_task_contract must return NativeTaskContract")
        self.native_contract.validate(spec,forcefield=forcefield)
        self.native_spec=resolve_feature_spec(backbone,feature_dim)
        backbone._native_feature_spec=self.native_spec
        self.native_components=native_component_views(backbone,self.native_contract.head_paths)
        self.readout=self.native_components["readout"]
        self.resolved_prediction=prediction
        self.prediction_descriptor={"version":1,"head_mode":"native","native_spec":self.native_spec.to_dict(),
            "native_task":self.native_contract.to_dict(),"backbone_cutoff":getattr(backbone,"cutoff",None),
            "native_implementation":type(backbone).__module__+"."+type(backbone).__qualname__,
            "head_paths":list(self.readout.head_paths),"adapter_output_spec":None,
            "original_modules_and_state_paths_preserved":True}

    def forward(self,batch,context=None,*,create_graph=None):
        if context is not None:raise ValueError("Native task has no additional conditioning input")
        value=self.backbone.native_prediction(batch,self.native_contract)
        count=batch.num_graphs if self.spec.scope=="graph" else len(batch.numbers)
        shape=(count,*self.spec.shape)
        if not isinstance(value,torch.Tensor) or value.numel()!=count*math.prod(self.spec.shape):
            raise ValueError(f"Native output shape {getattr(value,'shape',None)} cannot represent original task {shape}")
        if not value.is_floating_point() or value.device!=batch.positions.device or not bool(torch.isfinite(value).all()):
            raise ValueError("Native task must return finite floating predictions on the input device")
        return value.reshape(shape)

    def train(self,mode=True):
        super().train(mode)
        from universal_gnn.engine.optimization import apply_component_modes

        apply_component_modes(self)
        return self
