"""Component ownership, parameter freezing, mode control and optimizer reconstruction."""

import copy
import json

import torch

from universal_gnn.readouts.configuration import normalize_optimization


def components(model):
    root = getattr(model, "energy_model", model)
    result = {"backbone": root.backbone}
    if getattr(root, "adapter", None) is not None:
        result["adapter"] = root.adapter
    result["readout"] = root.readout
    return result


def configure_optimization(model, config):
    policy = normalize_optimization(config, has_adapter="adapter" in components(model))
    model._component_policy = policy
    seen = set()
    for name, module in components(model).items():
        for parameter in module.parameters():
            if id(parameter) in seen:
                raise ValueError("Component parameters overlap; cannot construct disjoint optimizer groups")
            seen.add(id(parameter))
            parameter.requires_grad_(policy["train_" + name])
            if not parameter.requires_grad:
                parameter.grad = None
    if seen != {id(parameter) for parameter in model.parameters()}:
        raise ValueError("Model parameters have no component owner")
    apply_component_modes(model)


def apply_component_modes(model):
    if not hasattr(model, "_component_policy") or not model.training:
        return
    for name, module in components(model).items():
        if not model._component_policy["train_" + name]:
            module.eval()


def parameter_groups(model):
    return [{"name": name, "parameters": [key for key, value in module.named_parameters() if value.requires_grad]}
            for name, module in components(model).items() if any(p.requires_grad for p in module.parameters())]


def make_optimizer(model, config):
    if "prediction" not in config and "optimization" not in config:
        return torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", 1e-3))
    groups = [{"name": name, "params": [p for p in module.parameters() if p.requires_grad]}
              for name, module in components(model).items() if any(p.requires_grad for p in module.parameters())]
    if not groups:
        raise ValueError("optimization has no trainable parameters; all-frozen models support inference only")
    return torch.optim.Adam(groups, lr=config.get("learning_rate", 1e-3))


def component_audit(model):
    result = {}
    for name, module in components(model).items():
        params = dict(module.named_parameters())
        unused = [key for key in params if any(key == prefix or key.startswith(prefix + ".")
                  for prefix in getattr(module, "unused_parameter_prefixes", ()))]
        total = sum(p.numel() for p in params.values())
        trainable = sum(p.numel() for p in params.values() if p.requires_grad)
        unused_size = sum(params[key].numel() for key in unused)
        result[name] = {"total_parameters": total, "trainable_parameters": trainable,
                        "frozen_parameters": total - trainable, "mode": "train" if module.training else "eval",
                        "module_modes": {"train": sum(m.training for m in module.modules()),
                                         "eval": sum(not m.training for m in module.modules())},
                        "known_unused_original_head": {"names": unused, "parameters": unused_size},
                        "task_parameter_upper_bound": total - unused_size,
                        "effective_trainable_upper_bound": trainable - sum(params[k].numel() for k in unused if params[k].requires_grad),
                        "unused_detection": "declared_only"}
    return result


def architecture_signature(model):
    root = getattr(model, "energy_model", model)
    descriptor = getattr(root, "prediction_descriptor", None)
    if descriptor is None:
        descriptor = {"version": "legacy", "route": root.route,
                      "native_irreps": root.backbone.irreps, "adapter_irreps": root.adapter.irreps,
                      "output_spec": root.spec.to_dict(), "backbone_cutoff": getattr(root.backbone, "cutoff", None),
                      "adapter_version": getattr(root.adapter, "basis_version", None)}
    # Canonical JSON types keep tuples and file-loaded lists equivalent.
    return json.loads(json.dumps({"prediction": descriptor, "components": {
        name: {"implementation": type(module).__module__ + "." + type(module).__qualname__,
               "module_types": {key: type(value).__qualname__ for key, value in module.named_modules()},
               "state_shapes": {key: list(value.shape) for key, value in module.state_dict().items()}}
        for name, module in components(model).items()}}))


def resolved_model_config(config, model, *, structure_count=None):
    result = copy.deepcopy(config)
    if "prediction" in config or "optimization" in config:
        root = getattr(model, "energy_model", model)
        if "prediction" in config:
            result["prediction"] = copy.deepcopy(root.resolved_prediction)
        result["optimization"] = dict(model._component_policy)
        result["resolved_components"] = architecture_signature(model)["prediction"]
        for key, value in {"seed": 123, "batch_size": 32, "max_atoms": None, "shuffle": True,
                           "dtype": "float32", "device": "cpu", "learning_rate": .001,
                           "epochs": 10, "structures": None, "checkpoint_every": 0,
                           "clip_grad_norm": 10., "report_structure_limit": 1000}.items():
            result.setdefault(key, value)
        result["dataset"].setdefault("selection", "first")
        result["dataset"].setdefault("selection_seed", result["seed"])
        if structure_count is not None:
            result.setdefault("report_predictions", structure_count <= 1000)
        if result["task"]["kind"] == "forcefield":
            from universal_gnn.tasks.supervision import supervised_outputs

            result["task"]["supervised_outputs"] = list(supervised_outputs(config))
    return result


def component_checkpoint(model):
    return {"version": 1, "architecture": architecture_signature(model), "policy": dict(model._component_policy),
            "optimizer_groups": parameter_groups(model)}


def verify_component_checkpoint(saved, model, *, training=False):
    expected = saved.get("components")
    if expected is None:
        return
    if expected.get("version") != 1 or expected["architecture"] != architecture_signature(model):
        raise ValueError("Checkpoint component architecture/signature mismatch")
    if training and (expected["policy"] != model._component_policy or expected["optimizer_groups"] != parameter_groups(model)):
        raise ValueError("Checkpoint optimization policy/parameter groups differ; use explicit warm-start")


class FrozenStateGuard:
    """Reject eval-time state mutation without disabling input autograd."""

    def __init__(self, model):
        self.model = model
        self.states = {name: {key: value.detach().cpu().clone() for key, value in module.state_dict().items()}
                       for name, module in components(model).items()
                       if not model._component_policy["train_" + name]}

    def verify(self):
        for name, expected in self.states.items():
            module = components(self.model)[name]
            if any(child.training for child in module.modules()):
                raise RuntimeError(f"Frozen component {name} must remain in eval mode")
            actual = module.state_dict()
            if set(expected) != set(actual) or any(not torch.equal(value, actual[key].detach().cpu())
                                                   for key, value in expected.items()):
                raise RuntimeError(f"Frozen component {name} mutated parameters or persistent buffers in eval mode")
