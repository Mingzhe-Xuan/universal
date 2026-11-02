from pathlib import Path

import ase
import numpy as np
from ase.io import read

from universal_gnn.data.dfpt import parse_dfpt_xml


def test_public_dfpt_xml_keeps_matched_raw_labels_and_ase_stress():
    path = Path(ase.__file__).parent / "test/testdata/vasp/vasprun_dfpt.xml"
    expected = read(path)
    with path.open("rb") as stream:
        record = parse_dfpt_xml(stream, "ASE-DFPT-fixture")
    np.testing.assert_allclose(record["atoms"]["coords"], expected.positions)
    np.testing.assert_allclose(record["forces"], expected.calc.results["forces"])
    np.testing.assert_allclose(record["stress_ase"], expected.get_stress(voigt=False))
    np.testing.assert_allclose(record["born_effective_charges"], expected.calc.results["born_effective_charges"])
    assert record["free_energy"] == expected.calc.results["free_energy"]


def test_older_vasp_epsilon_tag_retains_same_electronic_tensor():
    import io
    import xml.etree.ElementTree as ET

    path = Path(ase.__file__).parent / "test/testdata/vasp/vasprun_dfpt.xml"
    data = path.read_bytes()
    root = ET.fromstring(data)
    # The real fixture has both tags; older VASP omits only dielectric_dft.
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "varray" and child.attrib.get("name") == "dielectric_dft":
                parent.remove(child)
    old_style = ET.tostring(root)
    assert old_style != data
    current = parse_dfpt_xml(io.BytesIO(data), "current")
    legacy = parse_dfpt_xml(io.BytesIO(old_style), "legacy")
    np.testing.assert_allclose(legacy["dielectric_tensor"], current["dielectric_tensor"])
