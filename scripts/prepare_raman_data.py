"""Curate CRD original Raman tensors/frequencies into explicit relative spectra (Slurm)."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from ase.data import chemical_symbols

from prepare_acceptance_data import Cohorts, digest
from universal_gnn.workflows.spectroscopy import broaden, raman_activity


def array(value):
    shape, dtype, values = value["__ndarray__"]
    return np.asarray(values, dtype=dtype).reshape(shape)


def convert(row):
    data, properties = row["data"], row["key_value_pairs"]
    numbers = array(row["numbers"])
    frequencies = np.fromstring(properties["frequencies_thz"].strip("[]"), sep=" ") * 33.35640951981521
    tensors = data["raman_tensors"]
    if len(frequencies) != len(tensors) or len(frequencies) != 3 * len(numbers):
        raise ValueError("Raman mode count mismatch")
    activity = torch.zeros(len(tensors), dtype=torch.float64)
    present = [i for i, tensor in enumerate(tensors) if tensor is not None]
    activity[present] = raman_activity(torch.tensor([tensors[i] for i in present], dtype=torch.float64))
    grid = torch.linspace(50, 1000, 200, dtype=torch.float64)
    curve = broaden(torch.from_numpy(frequencies), activity, grid, width=5.)
    if not bool(torch.isfinite(curve).all()) or float(curve.max()) <= 0:
        raise ValueError("No finite nonzero Raman curve")
    return {"jid": properties["mpid"],
            "atoms": {"elements": [chemical_symbols[n] for n in numbers],
                      "coords": array(row["positions"]).tolist(), "cartesian": True,
                      "lattice_mat": array(row["cell"]["array"]).tolist(),
                      "pbc": array(row["pbc"]).tolist()},
            "spectrum": (curve / curve.max()).tolist(),
            "metadata": {"frequencies_cm_signed": frequencies.tolist(),
                         "raw_raman_tensors": tensors, "intensity": "45*a_bar^2 + 7*gamma^2",
                         "tensor_processing": "symmetric part for powder Placzek activity only",
                         "grid_cm": grid.tolist(), "lorentzian_HWHM_cm": 5.,
                         "normalization": "per-structure peak", "positive_mode_cutoff_cm": 1.}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("tmp/crd-selected-raw.json"))
    parser.add_argument("--output", type=Path, default=Path("data/acceptance"))
    args = parser.parse_args()
    source = json.loads(args.input.read_text())
    records = [(item["source_key"], convert(item["row"])) for item in source["records"]]
    cohorts = Cohorts(args.output)
    cohorts.save("raman", records,
                 {"dataset": "Computational Raman Database 1.0.1", "url": source["source_url"],
                  "archive_md5": source["archive_md5"], "selected_raw_sha256": digest(args.input),
                  "definition": "Curve derived from original tensors and signed mode frequencies; explicit broadening"},
                 {"kind": "supervised", "property": "spectrum", "channels": 200,
                  "unit": "peak_normalized_relative_Raman"})
    path = args.output / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["tasks"].update(cohorts.tasks)
    manifest["pending"].pop("raman", None)
    path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"count": len(records), "task": "raman", "pending": manifest["pending"]}))


if __name__ == "__main__":
    main()
