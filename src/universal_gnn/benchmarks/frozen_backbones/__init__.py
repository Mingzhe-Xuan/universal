"""Separate frozen-backbone ablations; primary full-finetune recipes are immutable."""

from .definitions import build_frozen_definitions, inspect_frozen_inputs, write_frozen_definitions

__all__ = ["build_frozen_definitions", "inspect_frozen_inputs", "write_frozen_definitions"]
