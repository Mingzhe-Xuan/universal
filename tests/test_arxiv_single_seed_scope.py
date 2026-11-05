"""Campaign scope: every original task/mode/model retained, only training seeds reduced."""

import itertools
import json
from pathlib import Path
import unittest


class SingleSeedCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads((Path(__file__).resolve().parents[1] /
                                "configs/arxiv_v1_scope.json").read_text(encoding="utf8"))

    def test_all_48_original_comparisons_remain(self):
        expected = {f"seed-123--{task}--{model}--{mode}" for task, model, mode in itertools.product(
            ["classification", "bandgap", "dielectric", "spectrum", "forcefield", "generation"],
            ["cgcnn", "alignn", "mace", "nequip"], ["pretrained", "scratch"])}
        self.assertEqual(set(self.scope["active_case_ids"]), expected)
        self.assertEqual(len(self.scope["active_case_ids"]), 48)
        self.assertEqual(self.scope["expected_training_runs"], 48)
        self.assertEqual(self.scope["training_seeds"], [123])

    def test_all_excluded_replicates_are_explicit_and_disjoint(self):
        expected = {identifier.replace("seed-123--", f"seed-{seed}--", 1)
                    for identifier, seed in itertools.product(self.scope["active_case_ids"], [456, 789])}
        self.assertEqual(set(self.scope["excluded_case_ids"]), expected)
        self.assertEqual(len(self.scope["excluded_case_ids"]), 96)
        self.assertFalse(set(self.scope["active_case_ids"]) & expected)
        self.assertEqual(self.scope["excluded_training_seeds"], [456, 789])

    def test_supplements_and_fixed_sampling_rng_are_distinct(self):
        self.assertEqual(self.scope["supplemental_training_seeds"], [123])
        self.assertEqual(self.scope["generation_sampling_seed"], 456)
        self.assertNotIn(self.scope["generation_sampling_seed"], self.scope["training_seeds"])
        self.assertIn("not an additional training replicate", self.scope["sampling_seed_interpretation"])

    def test_original_frozen_source_is_preserved(self):
        self.assertEqual(self.scope["version"], 1)
        self.assertEqual(self.scope["kind"], "arxiv_v1_execution_scope")
        self.assertTrue(self.scope["original_matrix_preserved"])
        self.assertEqual(self.scope["base_matrix_sha256"],
                         "b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651")


if __name__ == "__main__":
    unittest.main()
