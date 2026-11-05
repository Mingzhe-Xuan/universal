"""Full predictive pair preparation for the frozen primary experiment matrix."""

from .specification import predictive_spec
from .predictive import prepare_predictive_pair

__all__ = ["predictive_spec", "prepare_predictive_pair"]
