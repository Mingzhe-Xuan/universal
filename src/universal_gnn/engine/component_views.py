"""Non-registering ownership views over unchanged original module/state paths."""

from collections import OrderedDict

import torch


def under(name, prefixes):
    return any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)


class ComponentView:
    def __init__(self, owner, head_paths, *, head):
        self.owner, self.head_paths, self.head = owner, tuple(head_paths), head
        self.unused_parameter_prefixes = ()

    def owns(self, name):
        return under(name, self.head_paths) == self.head

    def named_parameters(self):
        return ((k,v) for k,v in self.owner.named_parameters() if self.owns(k))

    def parameters(self):
        return (v for _,v in self.named_parameters())

    def named_modules(self):
        return ((k,v) for k,v in self.owner.named_modules() if self.owns(k))

    def modules(self):
        return (v for _,v in self.named_modules())

    @property
    def training(self):
        return any(m.training for m in self.modules())

    def train(self, mode=True):
        if type(mode) is not bool:raise ValueError("Training mode must be bool")
        # Calling parent.train would recurse into the other component. Official
        # module objects/paths stay intact; only this view's owned modes change.
        for module in self.modules():module.training = mode
        return self

    def eval(self):
        return self.train(False)

    def state_dict(self):
        return OrderedDict((k,v) for k,v in self.owner.state_dict().items() if self.owns(k))

    def load_state_dict(self, values, strict=True):
        if not strict:raise ValueError("ComponentView only supports strict loading")
        actual=self.state_dict()
        if set(values)!=set(actual) or any(values[k].shape!=actual[k].shape for k in actual):
            raise ValueError("Component view state keys/shapes differ")
        with torch.no_grad():
            for key,value in values.items():actual[key].copy_(value)


def native_component_views(backbone, paths):
    available=dict(backbone.named_modules(remove_duplicate=False))
    paths=tuple(path for path in paths if path in available)
    if not paths:raise ValueError("Native head has no registered original modules")
    ownership={}
    for name,parameter in backbone.named_parameters(remove_duplicate=False):
        role=under(name,paths)
        if id(parameter) in ownership and ownership[id(parameter)] != role:
            raise ValueError("Native head shares parameters with backbone; independent training policies are undefined")
        ownership[id(parameter)]=role
    return {"backbone":ComponentView(backbone,paths,head=False),
            "readout":ComponentView(backbone,paths,head=True)}
