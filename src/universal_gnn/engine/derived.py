"""Explicit optional postprocessing; derived outputs are not extra training labels."""

import torch


def derived_outputs(predictions, task):
    specification = task.get("postprocess")
    if specification is None:
        return {}
    if specification["kind"] != "kramers_kronig":
        raise ValueError("Unknown spectral postprocess")
    from universal_gnn.workflows.spectroscopy import kramers_kronig

    value = predictions[task["property"]]
    grid = value.new_tensor(specification["grid"])
    real = kramers_kronig(grid, value)
    if not bool(torch.isfinite(real).all()):
        raise FloatingPointError("Nonfinite derived dielectric function")
    return {"epsilon1_finite_window": real.detach().cpu().tolist(),
            "grid": grid.cpu().tolist(), "grid_unit": specification["grid_unit"],
            "assumption": "epsilon2=0 outside supplied interval; endpoint values unreliable"}
