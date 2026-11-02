"""Read matched geometric and response labels from published VASP DFPT output."""

import hashlib
import io
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
from ase.io import read
from ase.stress import voigt_6_to_full_3x3_stress


def parse_dfpt_xml(stream, identifier):
    xml = stream.read()
    atoms = read(io.BytesIO(xml), format="vasp-xml", index=-1)
    values = atoms.calc.results
    if values.get("dielectric_tensor") is None:
        # Older VASP puts the electronic tensor in epsilon, outside ASE's dielectric_dft path.
        candidates = ET.fromstring(xml).findall(".//varray[@name='epsilon']")
        if len(candidates) == 1:
            values["dielectric_tensor"] = np.array([[float(x) for x in row.text.split()]
                                                     for row in candidates[0].findall("v")])
    required = ["free_energy", "forces", "stress", "born_effective_charges", "dielectric_tensor"]
    for key in required:
        if values.get(key) is None or not np.isfinite(np.asarray(values[key])).all():
            raise ValueError(f"{identifier}: missing/nonfinite DFPT {key}")
    if np.asarray(values["forces"]).shape != (len(atoms), 3):
        raise ValueError("Force/site count mismatch")
    if np.asarray(values["born_effective_charges"]).shape != (len(atoms), 3, 3):
        raise ValueError("Born/site count mismatch")
    if np.asarray(values["dielectric_tensor"]).shape != (3, 3):
        raise ValueError("Dielectric shape mismatch")
    stress = np.asarray(values["stress"])
    if stress.shape == (6,):
        stress = voigt_6_to_full_3x3_stress(stress)
    if stress.shape != (3, 3) or not atoms.pbc.all() or abs(np.linalg.det(atoms.cell)) < 1e-9:
        raise ValueError("Expected periodic nonsingular cell and full stress")
    return {"jid": identifier,
            "atoms": {"elements": atoms.get_chemical_symbols(), "coords": atoms.positions.tolist(),
                      "lattice_mat": atoms.cell.array.tolist(), "cartesian": True, "pbc": atoms.pbc.tolist()},
            "free_energy": float(values["free_energy"]),
            "forces": np.asarray(values["forces"]).tolist(), "stress_ase": stress.tolist(),
            "born_effective_charges": np.asarray(values["born_effective_charges"]).tolist(),
            "dielectric_tensor": np.asarray(values["dielectric_tensor"]).tolist(),
            "metadata": {"label_units": {"free_energy": "eV", "forces": "eV/angstrom",
                                          "stress_ase": "eV/angstrom^3 tensile-positive",
                                          "born_effective_charges": "e", "dielectric_tensor": "dimensionless"},
                         "definition": "Same final VASP DFPT geometry; raw Born axes retained, no ASR or space-group projection"}}


def read_dfpt_zip(path, source):
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise ValueError(f"SHA256 mismatch: {path}")
    with zipfile.ZipFile(path) as archive:
        candidates = [name for name in archive.namelist() if Path(name).name == "vasprun.xml"]
        if len(candidates) != 1:
            raise ValueError(f"Expected one vasprun.xml, found {candidates}")
        data = archive.read(candidates[0])
        record = parse_dfpt_xml(io.BytesIO(data), source["jid"])
    record["metadata"]["raw_archive"] = {"url": source["url"], "sha256": digest,
                                              "xml_sha256": hashlib.sha256(data).hexdigest(),
                                              "xml_member": candidates[0]}
    return record
