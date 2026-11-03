"""Actual ASE integration fixtures; execute through CPU Slurm."""

import unittest

from universal_gnn.data.preparation.perov5 import atoms_from_cif


CIF = """data_fixture
_cell_length_a 4
_cell_length_b 4
_cell_length_c 4
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt 'P 1'
_space_group_IT_number 1
loop_
_space_group_symop_operation_xyz
'x,y,z'
loop_
_atom_site_type_symbol
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Ba Ba0 0 0 0 1
Ti Ti1 0.5 0.5 0.5 1
O O2 0 0.5 0.5 1
O O3 0.5 0 0.5 1
O O4 0.5 0.5 0 1
"""


class Perov5CIFTests(unittest.TestCase):
    def test_ordered_five_atom_conventional_cell(self):
        atoms = atoms_from_cif(CIF)
        self.assertEqual(atoms["elements"], ["Ba", "Ti", "O", "O", "O"])
        for actual, expected in zip(atoms["coords"], ([0, 0, 0], [2, 2, 2], [0, 2, 2], [2, 0, 2], [2, 2, 0])):
            for a, b in zip(actual, expected):
                self.assertAlmostEqual(a, b, places=12)
        for i, row in enumerate(atoms["lattice_mat"]):
            for j, value in enumerate(row):
                self.assertAlmostEqual(value, 4. if i == j else 0., places=12)

    def test_incomplete_occupancy_and_wrong_atom_count_rejected(self):
        with self.assertRaisesRegex(ValueError, "occupancy"):
            atoms_from_cif(CIF.replace("Ba Ba0 0 0 0 1", "Ba Ba0 0 0 0 0.5"))
        with self.assertRaisesRegex(ValueError, "five_atoms"):
            atoms_from_cif(CIF.replace("O O4 0.5 0.5 0 1\n", ""))

    def test_missing_malformed_and_multiple_structure_cifs_rejected(self):
        for value in (None, "", "not a CIF"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                atoms_from_cif(value)
        with self.assertRaisesRegex(ValueError, "one_cif_structure"):
            atoms_from_cif(CIF + "\n" + CIF.replace("data_fixture", "data_second"))


if __name__ == "__main__":
    unittest.main()
