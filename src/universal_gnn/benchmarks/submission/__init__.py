"""Deferred full-data preparation gates and provenance-bound Slurm submission."""

from .planning import build_submission_plan
from .dispatch import dispatch_pair

__all__ = ["build_submission_plan", "dispatch_pair"]
