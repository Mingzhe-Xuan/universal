"""Explicit, strict component initialization; never reuse an incompatible optimizer."""

import hashlib
from pathlib import Path

from .optimization import architecture_signature, components


def initialize_components(model, path, selected=("backbone",)):
    from .training import load_checkpoint

    if not isinstance(selected, (list, tuple)) or not selected or len(set(selected)) != len(selected):
        raise ValueError("warm_start_components must be a nonempty unique component list")
    source = load_checkpoint(path)
    old, new = components(source), components(model)
    old_signature, new_signature = architecture_signature(source), architecture_signature(model)
    if any(name not in old or name not in new for name in selected):
        raise ValueError(f"warm_start_components={selected}: source={list(old)}, target={list(new)}")
    # Preflight every selected component before mutating any target parameters.
    for name in selected:
        a, b = old[name].state_dict(), new[name].state_dict()
        if set(a) != set(b) or any(a[k].shape != b[k].shape for k in a):
            raise ValueError(f"warm-start {name} state keys/shapes differ; select only compatible components")
        for key in ("implementation", "module_types"):
            if old_signature["components"][name][key] != new_signature["components"][name][key]:
                raise ValueError(f"warm-start {name} implementation differs")
        if name == "readout" and old_signature["prediction"] != new_signature["prediction"]:
            raise ValueError("warm-start readout feature/output semantics differ; select only compatible components")
        if name == "backbone":
            for key in ("irreps", "kind", "cutoff"):
                if getattr(old[name], key, None) != getattr(new[name], key, None):
                    raise ValueError(f"warm-start backbone {key} differs")
            if type(old[name]) is not type(new[name]):
                raise ValueError("warm-start backbone implementation differs")
            old_artifact = getattr(old[name], "official_artifact", None)
            new_artifact = getattr(new[name], "official_artifact", None)
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
            "target_architecture": architecture_signature(model)}
