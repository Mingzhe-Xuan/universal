"""Explicit published-weight defaults; model construction never downloads on a compute node."""

import hashlib
import os
from pathlib import Path


PROFILES = {
    "mace": {"checkpoint": "mace/small.model", "source": "https://github.com/ACEsuit/mace-mp/releases/tag/mace_mp_0",
             "files": {"mace/small.model": "2ddb079cee0e131eaaf6912ba581b394551ead283e95c99cfe78c605d10b5736"}},
    "cgcnn": {"checkpoint": "cgcnn/band-gap.pth.tar", "atom_init": "cgcnn/atom_init.json",
              "source": "https://github.com/txie-93/cgcnn/tree/f42ab233c4ee0c416879d6bc2d22a264418413ad/pre-trained",
              "files": {"cgcnn/band-gap.pth.tar": "d269775b9be0995c046abed3dd6556c281a3eff7b2e1d73cf81b99e2a1d4aa6c",
                        "cgcnn/atom_init.json": "cb90bd2257dbf8cfc4e6b2b6d4348d4616e8e9680f1339b1461137032e0f1894"}},
    "megnet": {"checkpoint": "megnet", "source": "https://github.com/materialsvirtuallab/matgl/tree/v1.1.3/pretrained_models/MEGNet-MP-2018.6.1-Eform",
               "files": {"megnet/model.json": "d858219134667d55e3c183435475ba248231a67311573373ed7298191f05d0a4",
                         "megnet/model.pt": "2cafe3234e3ab5987f22b6d2cb6be15a68121046571129ace5ed3fcad1c19624",
                         "megnet/state.pt": "35381368b17a2783f9ee09af5556cf1d84b74bf786b82d3fadd4acb38c51d040"}},
    "alignn": {"checkpoint": "alignn/optb88vdw_bandgap_radius.zip", "source": "https://ndownloader.figshare.com/files/67163492",
               "files": {"alignn/optb88vdw_bandgap_radius.zip": "f59fb168f64a67f0d191f6b8f0d5402373275a5c9e4ff22a1b551b497b622369"}},
    "nequip": {"checkpoint": "nequip/NequIP-OAM-S-0.2.nequip.zip", "source": "https://zenodo.org/records/23472045",
               "files": {"nequip/NequIP-OAM-S-0.2.nequip.zip": "5a3357b70c67cf497c718b785b2744f3405db14619e56f42a95cc6d372b00fea"}},
    "equiformer": {"checkpoint": "equiformer/best_checkpoint.pt", "source": "https://github.com/atomicarchitects/equiformer",
                   "files": {"equiformer/best_checkpoint.pt": "45a991aac88702003156a5fc3e45ee80f63ca5be4af6c385f033448cd43ce7e2"}},
}


def cache_root():
    configured = os.environ.get("UGNN_MODEL_CACHE")
    if configured:
        return Path(configured).expanduser().resolve()
    repository = Path(__file__).resolve().parents[4]
    if (repository / "pyproject.toml").is_file():
        return repository / "models" / "official"
    return Path.home() / ".cache" / "universal_gnn" / "official"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def official_options(name, options):
    options = dict(options)
    if options.get("_artifact") is not None:
        return options
    changed = {key for key in ("width", "layers", "cutoff", "radial") if key in options}
    if changed:
        raise ValueError(f"Official {name} keeps its checkpoint architecture; remove {sorted(changed)} "
                         "or explicitly select implementation: legacy for the old variant")
    if options.get("checkpoint") is not None:
        if name == "cgcnn" and options.get("atom_init") is None:
            raise ValueError("An explicit CGCNN checkpoint requires its original atom_init file")
        return options
    root, profile = cache_root(), PROFILES[name]
    for relative, expected in profile["files"].items():
        path = root / relative
        if not path.is_file():
            raise ValueError(f"Official {name} weights are missing: {path}. Prepare the published profile "
                             "in UGNN_MODEL_CACHE or set backbone.checkpoint explicitly; no variant fallback is used")
        if sha256_file(path) != expected:
            raise ValueError(f"Official {name} cache checksum mismatch: {path}")
    options["checkpoint"] = str(root / profile["checkpoint"])
    if "atom_init" in profile:
        options["atom_init"] = str(root / profile["atom_init"])
    options.setdefault("source", profile["source"])
    return options
