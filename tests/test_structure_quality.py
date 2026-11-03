"""Actual ASE/Pymatgen structure metrics without Torch; run numerical cases on Slurm."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest

from universal_gnn.engine.generative.structure_quality import StructuralQuality


def reference():
    return {"id": "reference", "numbers": [14, 8], "positions": [[0., 0., 0.], [1.2, 1., .5]],
            "cell": [[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]], "pbc": [True, True, True]}


class StructuralQualityTests(unittest.TestCase):
    def test_exact_match_permutation_uniqueness_and_zero_distribution_error(self):
        expected = reference()
        scorer = StructuralQuality([expected])
        first = scorer.update(expected, expected)
        permutation = {**copy.deepcopy(expected), "numbers": list(reversed(expected["numbers"])),
                       "positions": list(reversed(expected["positions"]))}
        second = scorer.update(permutation, expected)
        self.assertTrue(first["geometrically_valid"] and first["unique"] and first["matches_assigned_reference"])
        self.assertFalse(first["novel_to_train"])
        self.assertFalse(second["unique"])
        self.assertTrue(second["matches_assigned_reference"])
        self.assertAlmostEqual(first["normalized_rms"], 0., places=10)
        result = scorer.result()
        self.assertEqual(result["attempted"], 2)
        self.assertEqual(result["geometric_validity"], 1.)
        self.assertEqual(result["uniqueness_among_valid"], .5)
        self.assertEqual(result["novelty_among_valid"], 0.)
        self.assertEqual(result["paired_match_rate"], 1.)
        self.assertEqual(result["distribution_wasserstein_1"], {"volume_per_atom_angstrom3": 0., "density_g_cm3": 0.})

    def test_periodic_boundary_collisions_and_geometry_policy(self):
        expected = reference()
        samples = []
        collision = copy.deepcopy(expected)
        collision["positions"] = [[.05, 0., 0.], [3.95, 0., 0.]]
        samples.append((collision, "periodic_distance_below_threshold"))
        outside = copy.deepcopy(expected); outside["positions"][0][0] = 4.1
        samples.append((outside, "fractional_coordinates_outside_unit_cell"))
        nonfinite = copy.deepcopy(expected); nonfinite["positions"][0][0] = float("nan")
        samples.append((nonfinite, "nonfinite_singular_or_nonperiodic_geometry"))
        singular = copy.deepcopy(expected); singular["cell"] = [[0., 0., 0.]] * 3
        samples.append((singular, "nonfinite_singular_or_nonperiodic_geometry"))
        for generated, reason in samples:
            with self.subTest(reason=reason):
                scorer = StructuralQuality([expected])
                result = scorer.update(generated, expected)
                self.assertFalse(result["geometrically_valid"])
                self.assertEqual(result["reason"], reason)
                self.assertEqual(scorer.result()["geometric_validity"], 0.)

    def test_scaled_matching_still_reports_physical_volume_bias(self):
        expected = reference()
        generated = copy.deepcopy(expected)
        generated["positions"] = [[2 * value for value in row] for row in generated["positions"]]
        generated["cell"] = [[2 * value for value in row] for row in generated["cell"]]
        scorer = StructuralQuality([expected])
        result = scorer.update(generated, expected)
        self.assertTrue(result["matches_assigned_reference"])
        summary = scorer.result()
        self.assertAlmostEqual(summary["distribution_wasserstein_1"]["volume_per_atom_angstrom3"], 224.)
        self.assertGreater(summary["distribution_wasserstein_1"]["density_g_cm3"], 0.)
        self.assertEqual(summary["matching"]["rms_unit"], "normalized by (V/N)^(1/3)")

    def test_unseen_compositions_and_no_valid_samples_are_explicit(self):
        expected = reference()
        carbon = {**copy.deepcopy(expected), "numbers": [6, 6]}
        scorer = StructuralQuality([expected])
        self.assertTrue(scorer.update(carbon, carbon)["novel_to_train"])
        summary = scorer.result()
        self.assertEqual(summary["novelty_among_valid"], 1.)
        self.assertIsNone(summary["novelty_among_valid_with_training_seen_composition"])
        self.assertEqual(summary["valid_samples_with_training_seen_composition"], 0)
        failed = StructuralQuality([expected])
        result = failed.update(None, expected, failure="nonfinite sampler")
        self.assertEqual(result["reason"], "nonfinite sampler")
        summary = failed.result()
        self.assertIsNone(summary["uniqueness_among_valid"])
        self.assertTrue(all(value is None for value in summary["distribution_wasserstein_1"].values()))

    def test_contract_errors_do_not_become_scientific_invalidity(self):
        expected = reference()
        with self.assertRaisesRegex(ValueError, "composition"):
            StructuralQuality([expected]).update({**expected, "numbers": [6, 6]}, expected)
        for threshold in (0, True, float("inf")):
            with self.assertRaisesRegex(ValueError, "threshold"):
                StructuralQuality([expected], distance_threshold=threshold)
        with self.assertRaisesRegex(ValueError, "No generated"):
            StructuralQuality([expected]).result()

    def test_metadata_import_needs_no_torch_or_scientific_packages(self):
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        subprocess.run([sys.executable, "-S", "-c", "import sys; import universal_gnn.engine.generative.structure_quality; "
                        "assert not {'torch','numpy','ase','pymatgen'} & sys.modules.keys()"],
                       env=environment, capture_output=True, check=True)


if __name__ == "__main__":
    unittest.main()
