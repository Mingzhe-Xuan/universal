"""Resample NIST TBmBJ dielectric spectra; run numerical preprocessing with Slurm."""

import argparse
import ast
import io
import json
from pathlib import Path

from ase.io import read
import numpy as np

from prepare_acceptance_data import Cohorts, digest


def convert(item):
    atoms = read(io.StringIO(ast.literal_eval(item["contcar"])), format="vasp")
    energy = np.asarray(item["energies"])
    imaginary = np.asarray(item["imag_diagonal"])
    if imaginary.shape != (3, len(energy)) or not np.isfinite(imaginary).all():
        raise ValueError("Invalid dielectric component arrays")
    if not (np.diff(energy) > 0).all() or energy[0] > .05 or energy[-1] < 10:
        raise ValueError("Optical source does not cover the declared grid")
    grid = np.linspace(.05, 10., 200)
    curve = np.interp(grid, energy, imaginary.mean(0))
    return {"jid": item["jid"], "atoms": {"elements": atoms.get_chemical_symbols(),
            "coords": atoms.positions.tolist(), "cartesian": True,
            "lattice_mat": atoms.cell.array.tolist()}, "spectrum": curve.tolist(),
            "metadata": {"upstream_xml_url": item["url"], "upstream_xml_sha256": item["sha256"],
                         "geometry": "contcar from the same published material XML",
                         "definition": "trace average of TBmBJ imag_1,imag_2,imag_3; signed source values retained",
                         "grid_eV": grid.tolist(), "interpolation": "linear; no extrapolation"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("tmp/optical-selected-raw.json"))
    parser.add_argument("--output", type=Path, default=Path("data/acceptance"))
    args = parser.parse_args()
    items = json.loads(args.input.read_text())
    records = [(i, convert(item)) for i, item in enumerate(items)]
    cohorts = Cohorts(args.output)
    cohorts.save("optical", records,
                 {"dataset": "NIST JARVIS TBmBJ published optical dielectric function",
                  "selected_raw_sha256": digest(args.input),
                  "definition": "Trace-average epsilon2; epsilon1 finite-window KK assumes missing spectral weight zero"},
                 {"kind": "supervised", "property": "spectrum", "channels": 200, "unit": "dimensionless",
                  "postprocess": {"kind": "kramers_kronig", "grid": np.linspace(.05, 10., 200).tolist(),
                                  "grid_unit": "eV"}})
    path = args.output / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["tasks"].update(cohorts.tasks)
    path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"count": len(records), "task": "optical"}))


if __name__ == "__main__":
    main()
