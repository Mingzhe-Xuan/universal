"""Initialization policy and state-layout checks without importing model libraries."""

MODES = ("pretrained", "scratch")
FRESH_OFFICIAL_PROVIDERS = ("cgcnn", "alignn", "mace", "nequip")


def validate_initialization(mode):
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError("backbone.initialization must be pretrained or scratch")
    return mode


def initialize_original(model, reference, *, mode="pretrained"):
    """Use an upstream constructor's fresh state, or load its entire published state."""
    validate_initialization(mode)
    if mode == "pretrained":
        model.load_state_dict(reference, strict=True)
    else:
        actual = model.state_dict()
        if set(actual) != set(reference):
            raise ValueError("Fresh official constructor state keys differ from source architecture")
        if any(tuple(actual[key].shape) != tuple(reference[key].shape) for key in actual):
            raise ValueError("Fresh official constructor state shapes differ from source architecture")
    return {"initialization": mode, "state_layout_verified": True}
