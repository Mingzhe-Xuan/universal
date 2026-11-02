"""Original model implementations loaded from their published training artifacts."""


def make_official(name, **options):
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
    raise ValueError(f"Official provider {name!r} is not implemented yet; no architecture-variant fallback")
