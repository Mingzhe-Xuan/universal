"""Original task semantics retained when an existing prediction head is selected."""

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class NativeTaskContract:
    property: str
    head_paths: tuple[str, ...]
    unit: str
    reduction: str = "mean"
    shape: tuple[int, ...] = (1,)
    scope: str = "graph"
    kind: str = "regression"
    forcefield: bool = False
    original_task: str = ""
    pooling: str = "original model"
    normalization: dict = field(default_factory=dict)
    packaging: dict = field(default_factory=dict)
    artifact_sha256: dict = field(default_factory=dict)
    version: int = 1

    def __post_init__(self):
        if type(self.version) is not int or self.version != 1:
            raise ValueError("Unsupported native task contract version")
        if not self.head_paths or any(not isinstance(p,str) or not p for p in self.head_paths):
            raise ValueError("Native task requires original head module paths")
        if self.scope not in {"graph","node"} or not self.shape or any(type(n) is not int or n<1 for n in self.shape):
            raise ValueError("Native task scope/shape is invalid")

    def to_dict(self):
        return asdict(self)

    def validate(self, spec, *, forcefield=False):
        expected = {"name": self.property, "scope": self.scope, "shape": self.shape,
                    "unit": self.unit, "reduction": self.reduction, "kind": self.kind,
                    "construction": "direct"}
        actual = {key: getattr(spec,key) for key in expected}
        if actual != expected:
            raise ValueError(f"prediction.head_mode=native retains original task {expected}; actual {actual}. "
                             "Select head_mode=reset for a different task/readout")
        if forcefield and not self.forcefield:
            raise ValueError(f"Native {self.original_task or self.property} head is not an instantaneous "
                             "total-energy forcefield; select head_mode=reset")
