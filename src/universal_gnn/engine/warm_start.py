"""Explicit, strict component initialization; never reuse an incompatible optimizer."""

import hashlib
from pathlib import Path

from .optimization import architecture_signature, components, compare_architectures


def initialize_components(model, path, selected=("backbone",)):
    from .training import load_checkpoint

    if not isinstance(selected, (list, tuple)) or not selected or len(set(selected)) != len(selected):
        raise ValueError("warm_start_components must be a nonempty unique component list")
    source = load_checkpoint(path)
    old, new = components(source), components(model)
    source_root, target_root = getattr(source,"energy_model",source),getattr(model,"energy_model",model)
    native_transfer = "backbone" in selected and (
        hasattr(source_root,"native_components") or hasattr(target_root,"native_components"))
    ignored_native_heads = None
    if native_transfer:
        from .component_views import native_component_views

        for instance, mapping in ((source,old),(model,new)):
            backbone=instance.backbone
            contract=backbone.native_task_contract()
            mapping["backbone"]=native_component_views(backbone,contract.head_paths)["backbone"]
        ignored_native_heads={"source":sorted(set(source.backbone.state_dict())-set(old["backbone"].state_dict())),
                              "target":sorted(set(model.backbone.state_dict())-set(new["backbone"].state_dict())),
                              "target_unselected_heads":"retain target artifact initialization"}
    old_signature, new_signature = architecture_signature(source), architecture_signature(model)
    if any(name not in old or name not in new for name in selected):
        raise ValueError(f"warm_start_components={selected}: source={list(old)}, target={list(new)}")
    # Preflight every selected component before mutating any target parameters.
    for name in selected:
        if name == "adapter":
            fields = ("version", "native_spec", "adapter", "adapter_output_spec", "route", "adapter_version")
            if any(not compare_architectures(old_signature["prediction"].get(key),new_signature["prediction"].get(key))[0] for key in fields):
                raise ValueError("warm-start adapter feature/basis semantics differ")
        a, b = old[name].state_dict(), new[name].state_dict()
        if set(a) != set(b) or any(a[k].shape != b[k].shape for k in a):
            raise ValueError(f"warm-start {name} state keys/shapes differ; select only compatible components")
        if name=="backbone" and native_transfer:
            if ({k:type(v).__qualname__ for k,v in old[name].named_modules()} !=
                    {k:type(v).__qualname__ for k,v in new[name].named_modules()}):
                raise ValueError("warm-start native backbone body implementation differs")
        else:
            for key in ("implementation", "module_types"):
                if old_signature["components"][name][key] != new_signature["components"][name][key]:
                    raise ValueError(f"warm-start {name} implementation differs")
        if name == "readout" and not compare_architectures(old_signature["prediction"], new_signature["prediction"])[0]:
            raise ValueError("warm-start readout feature/output semantics differ; select only compatible components")
        if name == "backbone":
            from .runtime import verify_extensions

            old_backbone,new_backbone=source.backbone,model.backbone
            verify_extensions({"extensions": getattr(old_backbone, "extension_provenance", {})}, model)
            for key in ("irreps", "kind", "cutoff"):
                if getattr(old_backbone, key, None) != getattr(new_backbone, key, None):
                    raise ValueError(f"warm-start backbone {key} differs")
            if type(old_backbone) is not type(new_backbone):
                raise ValueError("warm-start backbone implementation differs")
            old_artifact = getattr(old_backbone, "official_artifact", None)
            new_artifact = getattr(new_backbone, "official_artifact", None)
            if (old_artifact is None) != (new_artifact is None) or (
                    old_artifact is not None and old_artifact["sha256"] != new_artifact["sha256"]):
                raise ValueError("warm-start official backbone source artifacts differ; use its original architecture/artifact")
    for name in selected:
        new[name].load_state_dict(old[name].state_dict(), strict=True)
    return {"kind": "explicit_component_warm_start", "checkpoint": str(path),
            "checkpoint_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "loaded": {name: {"keys": list(new[name].state_dict()),
                              "parameters": sum(p.numel() for p in new[name].parameters())} for name in selected},
            "ignored_source_components": [name for name in old if name not in selected],
            "new_initialized_components": [name for name in new if name not in selected],
            "optimizer_rebuilt": True, "source_architecture": architecture_signature(source),
            "target_architecture": architecture_signature(model),"native_head_state_excluded_from_backbone":ignored_native_heads}
