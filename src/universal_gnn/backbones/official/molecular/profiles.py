"""Pure metadata contract for optional molecular topology and checkpoint identity."""

from copy import deepcopy
import hashlib
import math
from pathlib import Path


def resolve_profile(provider, artifact, *, name=None, cutoff=None):
    if provider not in {"cgcnn", "alignn"}:
        raise ValueError("Molecular input profiles currently support official CGCNN and ALIGNN")
    saved = artifact.get("input_profile")
    if saved is not None:
        if (not isinstance(saved, dict) or type(saved.get("version")) is not int or saved["version"] != 1
                or saved.get("name") != "molecular_radius" or set(saved) != {"version", "name", "cutoff", "all_neighbors", "pbc"}
                or saved.get("all_neighbors") is not True or saved.get("pbc") != "none"):
            raise ValueError("Unsupported embedded molecular input profile")
        radius = saved["cutoff"]
        if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0:
            raise ValueError("Unsupported embedded molecular input cutoff")
    selected = name if name is not None else saved["name"] if saved is not None else "official"
    if not isinstance(selected, str) or selected not in {"official", "molecular_radius"}:
        raise ValueError("input_profile must be official or molecular_radius")
    if selected == "official":
        if cutoff is not None:
            raise ValueError("input_cutoff requires input_profile=molecular_radius; official graph remains unchanged")
        result = dict(version=1, name="official")
    else:
        radius = cutoff if cutoff is not None else saved["cutoff"] if saved is not None else 6.
        if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0:
            raise ValueError("Molecular input_cutoff must be positive and finite")
        result = dict(version=1, name="molecular_radius", cutoff=float(radius), all_neighbors=True, pbc="none")
    if saved is not None and saved != result:
        raise ValueError("Molecular input profile differs from the checkpoint; use explicit new-task transfer")
    return result


def configure_profile(provider, artifact, *, name=None, cutoff=None):
    if (artifact.get("input_profile") is None) != (artifact.get("input_profile_implementation") is None):
        raise ValueError("Embedded molecular profile and implementation must be provided together")
    profile = resolve_profile(provider, artifact, name=name, cutoff=cutoff)
    if profile["name"] == "official":
        return profile
    root = Path(__file__).resolve().parent.parent
    names = [provider + ".py", "molecular/__init__.py", "molecular/profiles.py", "molecular/geometry.py",
             "molecular/" + provider + ".py"]
    implementation = dict(version=1, source_line_endings="LF", source_sha256={
        "backbones/official/" + name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in names})
    saved = artifact.get("input_profile_implementation")
    if saved is not None and saved != implementation:
        raise ValueError("Molecular input adapter implementation differs from the checkpoint")
    artifact["input_profile"] = deepcopy(profile)
    artifact["input_profile_implementation"] = implementation
    return profile


def graph_provenance(backbone, original):
    if backbone.input_profile["name"] == "molecular_radius":
        return {**original, "input_profile": deepcopy(backbone.input_profile),
                "input_profile_implementation": deepcopy(backbone.official_artifact["input_profile_implementation"])}
    return original
