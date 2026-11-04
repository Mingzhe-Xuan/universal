"""Configuration/protocol tests with disposable stdlib workers; no model execution."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.preflight import run_preflight
from universal_gnn.benchmarks.resolution import resolved_candidate
from universal_gnn.engine.generative.protocol import fit_volume_prior
from test_preflight_control import WORKER


def generation_case():
    candidate = {"device": "cuda", "batch_size": 5,
                 "backbone": {"name": "alignn", "initialization": "scratch"},
                 "graph": {"name": "radius", "cutoff": 6.},
                 "task": {"kind": "generation", "sampling": {"steps": 50, "inner_steps": 2}},
                 "dataset": {"path": "full.jsonl", "partition": "train"}}
    stats = fit_volume_prior([{"numbers": [14], "cell": [[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]]}],
                             training_fingerprint="a" * 64)
    value = {"generation_corruption": "per_epoch_structure_v2",
             "generation_prior": {"statistics": stats, "sampling_volume_source": "train_fit"},
             "sampling": {**candidate["task"]["sampling"], "volume_per_atom": stats["volume_per_atom"]}}
    return candidate, value


class GenerationResolutionTests(unittest.TestCase):
    def test_only_actual_defaults_added_and_all_user_settings_preserved(self):
        config, value = generation_case()
        before = copy.deepcopy(config)
        resolved = resolved_candidate(config, {"resolved_generation": value})
        self.assertEqual(config, before)
        self.assertEqual(resolved["backbone"], config["backbone"])
        self.assertEqual(resolved["graph"], config["graph"])
        self.assertEqual(resolved["dataset"], config["dataset"])
        self.assertEqual(resolved["task"]["sampling"]["steps"], 50)
        self.assertEqual(resolved["task"]["sampling"]["inner_steps"], 2)
        self.assertEqual(resolved["task"]["sampling"]["volume_per_atom"], value["sampling"]["volume_per_atom"])
        self.assertEqual(resolved["generation_prior"], value["generation_prior"])

    def test_missing_wrong_noise_modified_steps_or_prior_are_rejected(self):
        config, value = generation_case()
        invalid = [{}, {"resolved_generation": None}]
        for change in ("noise", "steps", "new_setting", "wrong_volume", "missing_provenance", "graph"):
            changed = copy.deepcopy(value)
            if change == "noise": changed["generation_corruption"] = "per_structure_v1"
            elif change == "steps": changed["sampling"]["steps"] = 2
            elif change == "new_setting": changed["sampling"]["max_length"] = 1.
            elif change == "wrong_volume": changed["sampling"]["volume_per_atom"] = 20.
            elif change == "missing_provenance": changed["generation_prior"]["statistics"].pop("training_fingerprint")
            else: changed["graph"] = {"cutoff": 1.}
            invalid.append({"resolved_generation": changed})
        for worker in invalid:
            with self.subTest(worker=worker), self.assertRaises(ValueError):
                resolved_candidate(config, worker)
        explicit = copy.deepcopy(config)
        explicit["generation_prior"] = {"wrong": True}
        with self.assertRaisesRegex(ValueError, "explicit generation prior"):
            resolved_candidate(explicit, {"resolved_generation": value})

    def test_explicit_volume_preserved_and_legacy_objective_not_migrated(self):
        config, value = generation_case()
        config["task"]["sampling"]["volume_per_atom"] = 20.
        value["sampling"]["volume_per_atom"] = 20.
        value["generation_prior"]["sampling_volume_source"] = "explicit_config"
        self.assertEqual(resolved_candidate(config, {"resolved_generation": value})["task"]["sampling"]["volume_per_atom"], 20.)
        config["generation_corruption"] = "per_structure_v1"
        value.update(generation_corruption="per_structure_v1", generation_prior=None)
        self.assertEqual(resolved_candidate(config, {"resolved_generation": value}), config)
        with self.assertRaisesRegex(ValueError, "Non-generation"):
            resolved_candidate({"task": {"kind": "forcefield"}}, {"resolved_generation": value})

    def test_success_and_unknown_resolution_failure_through_actual_controller(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "capacity_fixture.py").write_text(WORKER)
            with patch.dict(os.environ, {"PYTHONPATH": str(root)}):
                config, value = generation_case()
                config["fixture_resolved_generation"] = value
                good = run_preflight(config, root / "good", probe={"indices": [0]}, worker_module="capacity_fixture")
                self.assertTrue(good["passed"])
                actual = json.loads((root / "good/config.resolved.json").read_text())
                self.assertEqual(actual["generation_prior"], value["generation_prior"])
                self.assertEqual(actual["task"]["sampling"], value["sampling"])
                broken = copy.deepcopy(config)
                broken["fixture_resolved_generation"]["sampling"]["steps"] = 2
                bad = run_preflight(broken, root / "bad", probe={"indices": [0]}, worker_module="capacity_fixture")
                self.assertFalse(bad["passed"])
                self.assertEqual(len(bad["attempts"]), 1)
                self.assertEqual(bad["attempts"][0]["status"], "invalid_result")
                self.assertFalse((root / "bad/config.resolved.json").exists())


if __name__ == "__main__":
    unittest.main()
