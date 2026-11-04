"""Original model implementations loaded from their published training artifacts."""


def make_official(name, **options):
    from universal_gnn.backbones.initialization import FRESH_OFFICIAL_PROVIDERS, validate_initialization

    initialization = validate_initialization(options.pop("initialization", "pretrained"))
    if initialization == "scratch" and name not in FRESH_OFFICIAL_PROVIDERS:
        raise ValueError(f"Official {name} fresh construction is not implemented yet; no pretrained or legacy fallback")
    if name in FRESH_OFFICIAL_PROVIDERS:
        options["initialization"] = initialization
    if name == "alignn":
        from .alignn import OfficialALIGNN

        return OfficialALIGNN(**options)
    if name == "mace":
        from .mace import OfficialMACE

        return OfficialMACE(**options)
    if name == "cgcnn":
        from .cgcnn import OfficialCGCNN

        return OfficialCGCNN(**options)
    if name == "megnet":
        from .megnet import OfficialMEGNet

        return OfficialMEGNet(**options)
    if name == "nequip":
        from .nequip import OfficialNequIP

        return OfficialNequIP(**options)
    if name == "equiformer":
        from .equiformer import OfficialEquiformer

        return OfficialEquiformer(**options)
    raise ValueError(f"Official provider {name!r} is not implemented yet; no architecture-variant fallback")
