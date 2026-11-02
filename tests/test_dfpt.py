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
