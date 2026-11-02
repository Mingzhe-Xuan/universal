from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PropertySpec:
    name: str
    scope: str
    shape: tuple[int, ...]
    unit: str
    kind: str = "regression"
    reduction: str = "mean"
    response_indices: str | None = None
    auxiliary_indices: str | None = None
    construction: str = "direct"
    version: int = 1

    def to_dict(self):
        return asdict(self)


CATALOG = {
    "formation_energy": PropertySpec("formation_energy", "graph", (1,), "eV/atom"),
    "bandgap": PropertySpec("bandgap", "graph", (1,), "eV"),
    "total_energy": PropertySpec("total_energy", "graph", (1,), "eV", reduction="sum"),
    "classification": PropertySpec("classification", "graph", (2,), "class", kind="classification"),
    "atom_scalar": PropertySpec("atom_scalar", "node", (1,), "dataset_defined", reduction="none"),
    "spectrum": PropertySpec("spectrum", "graph", (200,), "dataset_defined"),
    "dielectric": PropertySpec("dielectric", "graph", (3, 3), "dimensionless",
                               response_indices="i", auxiliary_indices="j", construction="derivative"),
    "piezoelectric": PropertySpec("piezoelectric", "graph", (3, 3, 3), "C/m^2",
                                  response_indices="i", auxiliary_indices="jk", construction="derivative"),
    "elastic": PropertySpec("elastic", "graph", (3, 3, 3, 3), "GPa",
                            response_indices="ij", auxiliary_indices="kl", construction="derivative"),
    "born_charge": PropertySpec("born_charge", "node", (3, 3), "e",
                                response_indices="i", auxiliary_indices="j", construction="derivative",
                                reduction="none"),
}


def property_spec(name: str, *, channels: int | None = None, unit: str | None = None) -> PropertySpec:
    from dataclasses import replace

    if name not in CATALOG:
        raise ValueError(f"Unknown property {name!r}; register an explicit PropertySpec")
    spec = CATALOG[name]
    if channels is not None:
        if name != "spectrum":
            raise ValueError("Only spectrum accepts a grid channel override")
        spec = replace(spec, shape=(channels,))
    return replace(spec, unit=unit) if unit is not None else spec
