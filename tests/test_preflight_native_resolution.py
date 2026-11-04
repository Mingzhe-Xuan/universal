"""Native calibration acceptance in a real disposable stdlib controller; no GNN execution."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.backbones.blueprints import aggregate_native_neighbor_counts
from universal_gnn.benchmarks.preflight import run_preflight
from universal_gnn.benchmarks.resolution import resolved_candidate
from universal_gnn.engine.initialization.policy import inherit_neighbor_statistics, requires_native_neighbor_statistics
from test_preflight_control import WORKER
from test_preflight_generation_resolution import generation_case


def native_case():
    candidate = dict(device="cuda", batch_size=5, backbone=dict(name="mace", initialization="scratch"),
                     task=dict(kind="supervised", property="bandgap"),
                     dataset=dict(path="full.jsonl", split_manifest="split.json", partition="train"))
    artifact = dict(model="a" * 64)
    statistics = aggregate_native_neighbor_counts([dict(atomic_nodes=2, active_receivers=2, directed_edges=2)] * 2,
                    provider="mace", cutoff=6., dtype="float32", source_sha256="b" * 64,
                    manifest_sha256="c" * 64, training_fingerprint="d" * 64, declared_training_structures=2)
    statistics["native_graph"] = dict(artifact_sha256=artifact, adapter_source_sha256="e" * 64,
                                      provider_version="0.3.16", ase_version="3.27.0", torch_version="2.7.1+cu128")
    worker = dict(resolved_native_initialization=dict(neighbor_statistics=statistics), selected_training_structures=2,
                  execution=dict(backbone_cutoff=6., backend_version="0.3.16", official=dict(
                      initialization="scratch", parameter_coverage=0., buffer_coverage=0., state_layout_verified=True,
                      sha256=artifact, neighbor_statistics=copy.deepcopy(statistics))))
    return candidate, worker


class NativeResolutionTests(unittest.TestCase):
    def test_only_receipt_added_explicit_settings_and_inputs_preserved(self):
        candidate, worker = native_case()
        original, response = copy.deepcopy(candidate), copy.deepcopy(worker)
        resolved = resolved_candidate(candidate, worker)
        expected = copy.deepcopy(candidate)
        expected["backbone"]["neighbor_statistics"] = worker["resolved_native_initialization"]["neighbor_statistics"]
        self.assertEqual(resolved, expected)
        self.assertEqual(candidate, original)
        self.assertEqual(worker, response)
        self.assertEqual(resolved_candidate(expected, worker), expected)
        generation, generation_worker = generation_case()
        generation.update(backbone=copy.deepcopy(candidate["backbone"]), dataset=copy.deepcopy(candidate["dataset"]))
        generation.pop("graph")
        combined = resolved_candidate(generation, {**worker, "resolved_generation": generation_worker})
        self.assertEqual(combined["generation_prior"], generation_worker["generation_prior"])
        self.assertEqual(combined["backbone"], expected["backbone"])

    def test_false_fresh_missing_provenance_and_changed_defaults_are_rejected(self):
        candidate, worker = native_case()
        invalid = [{}, {"resolved_native_initialization": None}]
        for change in ("extra", "coverage", "state_layout", "consumed_stats", "artifact", "precision", "cutoff", "selected", "adapter", "backend"):
            value = copy.deepcopy(worker)
            if change == "extra": value["resolved_native_initialization"]["graph"] = {}
            elif change == "coverage": value["execution"]["official"]["parameter_coverage"] = 1.
            elif change == "state_layout": value["execution"]["official"]["state_layout_verified"] = False
            elif change == "consumed_stats": value["execution"]["official"]["neighbor_statistics"]["source_sha256"] = "f" * 64
            elif change == "artifact": value["execution"]["official"]["sha256"] = {"model": "f" * 64}
            elif change == "precision": value["resolved_native_initialization"]["neighbor_statistics"]["dtype"] = "float64"
            elif change == "cutoff": value["execution"]["backbone_cutoff"] = 4.
            elif change == "selected": value["selected_training_structures"] = 3
            elif change == "adapter": value["resolved_native_initialization"]["neighbor_statistics"]["native_graph"]["adapter_source_sha256"] = "bad"
            else: value["execution"]["backend_version"] = "other"
            invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolved_candidate(candidate, value)
        for change in ({"structures": 1}, {"structures": True}, {"graph": {"name": "radius", "cutoff": 6.}},
                       {"dataset": {**candidate["dataset"], "partition": "test"}},
                       {"backbone": {**candidate["backbone"], "neighbor_statistics": {"explicit": True}}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolved_candidate({**candidate, **change}, worker)
        for options in ({"name": "cgcnn", "initialization": "scratch"}, {"name": "mace"},
                        {"name": "mace", "initialization": "scratch", "implementation": "legacy"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                resolved_candidate({**candidate, "backbone": options}, worker)

    def test_resume_inherits_only_omitted_compatible_statistics(self):
        candidate, worker = native_case()
        saved = resolved_candidate(candidate, worker)
        original = copy.deepcopy(candidate)
        self.assertTrue(requires_native_neighbor_statistics(candidate))
        self.assertEqual(inherit_neighbor_statistics(candidate, saved), saved)
        self.assertEqual(candidate, original)
        for explicit in ({"explicit": True}, None):
            changed = {**candidate, "backbone": {**candidate["backbone"], "neighbor_statistics": explicit}}
            self.assertEqual(inherit_neighbor_statistics(changed, saved), changed)
        for options in ({"name": "nequip", "initialization": "scratch"}, {"name": "mace"},
                        {"name": "mace", "initialization": "scratch", "implementation": "legacy"}):
            changed = {**candidate, "backbone": options}
            self.assertEqual(inherit_neighbor_statistics(changed, saved), changed)

    def test_actual_controller_writes_only_accepted_receipt_and_never_halves_bad_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);(root / "native_fixture.py").write_text(WORKER)
            with patch.dict(os.environ, {"PYTHONPATH": str(root)}):
                candidate, worker = native_case()
                candidate["fixture_native_worker_fields"] = worker
                good = run_preflight(candidate, root / "good", probe={"indices": [0]}, worker_module="native_fixture")
                self.assertTrue(good["passed"])
                actual = json.loads((root / "good/config.resolved.json").read_text())
                self.assertEqual(actual["backbone"]["neighbor_statistics"], worker["resolved_native_initialization"]["neighbor_statistics"])
                bad = copy.deepcopy(candidate)
                bad["fixture_native_worker_fields"]["execution"]["official"]["parameter_coverage"] = 1.
                failed = run_preflight(bad, root / "bad", probe={"indices": [0]}, worker_module="native_fixture")
                self.assertFalse(failed["passed"])
                self.assertEqual(len(failed["attempts"]), 1)
                self.assertEqual(failed["attempts"][0]["status"], "invalid_result")
                self.assertFalse((root / "bad/config.resolved.json").exists())


if __name__ == "__main__":
    unittest.main()
