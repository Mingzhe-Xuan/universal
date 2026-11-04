"""Pure controls for source-preserving, frozen original-head evaluation."""

import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.registry import DATASETS, canonical_digest
from universal_gnn.benchmarks.native_heads import native_baseline_config, evaluate_native_baseline


def fixture():
    matrix = dict(kind="arxiv_v1_primary_matrix", definition_revision=2,
                  registry={}, registry_sha256=canonical_digest({}), cases=[])
    for provider in ("cgcnn", "alignn", "mace", "nequip"):
        task = "bandgap" if provider in {"cgcnn", "alignn"} else "forcefield"
        source = "jarvis-gap" if task == "bandgap" else "mlearn-forcefield"
        config = dict(seed=123, structures="all", max_atoms=None, dtype="float32", device="cuda",
                      batch_size=32 if task == "bandgap" else 4,
                      backbone=dict(name=provider, implementation="official", initialization="pretrained"),
                      prediction=dict(version=1, head_mode="reset", readout={"name": "old_head"}),
                      optimization=dict(train_backbone=True, train_readout=True, train_adapter=True),
                      dataset=dict(path=source, sha256=DATASETS[source][0], split_manifest="split.json",
                                   split_manifest_sha256="a" * 64, partition="train", bindings={"raw": {"key": "value"}}),
                      task=dict(kind="supervised", property="bandgap") if task == "bandgap" else
                           dict(kind="forcefield", supervised_outputs=["total_energy", "forces"], loss_weights={"total_energy": 1., "forces": 1.}))
        matrix["cases"].append(dict(id="seed-123--" + task + "--" + provider + "--pretrained",
            model=provider, task=task, initialization="pretrained", seed=123,
            config=config, config_sha256=canonical_digest(config)))
    return matrix


class NativeBaselineTests(unittest.TestCase):
    def test_all_four_original_heads_preserve_source_and_target_fields(self):
        matrix = fixture()
        before = copy.deepcopy(matrix)
        for provider in ("cgcnn", "alignn", "mace", "nequip"):
            with self.subTest(provider=provider):
                spec = native_baseline_config(matrix, provider)
                actual = copy.deepcopy(spec["config"])
                self.assertEqual(actual["prediction"], {"version": 1, "head_mode": "native"})
                self.assertEqual(actual["optimization"], {"train_backbone": False, "train_readout": False})
                original = next(c["config"] for c in matrix["cases"] if c["model"] == provider)
                for field in ("device", "prediction", "optimization"):
                    actual[field] = copy.deepcopy(original[field])
                actual["dataset"]["partition"] = "train"
                self.assertEqual(actual, original)
                self.assertEqual(spec["counts"]["test"], 7580 if spec["task"] == "bandgap" else 164)
        self.assertEqual(matrix, before)

    def test_nonfull_source_or_modified_graph_precision_are_rejected(self):
        changes = [lambda c: c.update(structures=10), lambda c: c.update(max_atoms=100),
                   lambda c: c.update(dtype="float64"), lambda c: c.update(graph={"name": "radius", "cutoff": 6}),
                   lambda c: c["backbone"].update(initialization="scratch"),
                   lambda c: c["dataset"].update(sha256="b" * 64),
                   lambda c: c["dataset"].update(partition="test")]
        for i, change in enumerate(changes):
            with self.subTest(change=i):
                matrix = fixture()
                case = matrix["cases"][0]
                change(case["config"])
                case["config_sha256"] = canonical_digest(case["config"])
                with self.assertRaises(ValueError):
                    native_baseline_config(matrix, "cgcnn")

    def test_wrong_original_output_is_rejected(self):
        for provider in ("cgcnn", "mace"):
            with self.subTest(provider=provider):
                matrix = fixture()
                case = next(c for c in matrix["cases"] if c["model"] == provider)
                case["config"]["task"] = {"kind": "supervised", "property": "classification"}
                case["config_sha256"] = canonical_digest(case["config"])
                with self.assertRaises(ValueError):
                    native_baseline_config(matrix, provider)

    def test_changed_config_or_registry_digest_is_rejected(self):
        for mutation in (lambda m: m["cases"][0]["config"].update(seed=456),
                         lambda m: m["registry"].update(changed=True)):
            matrix = fixture()
            mutation(matrix)
            with self.assertRaises(ValueError):
                native_baseline_config(matrix, "cgcnn")

    def test_ambiguous_or_missing_original_case_is_rejected(self):
        matrix = fixture()
        matrix["cases"].append(copy.deepcopy(matrix["cases"][0]))
        with self.assertRaises(ValueError):
            native_baseline_config(matrix, "cgcnn")
        matrix = fixture()
        matrix["cases"][0]["initialization"] = "scratch"
        with self.assertRaises(ValueError):
            native_baseline_config(matrix, "cgcnn")

    def test_other_provider_cannot_be_silently_substituted(self):
        with self.assertRaises(ValueError):
            native_baseline_config(fixture(), "megnet")

    def test_guard_precedes_runtime_and_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / "new"
            with self.assertRaisesRegex(RuntimeError, "must run through Slurm"):
                evaluate_native_baseline(fixture(), "mace", path)
            self.assertFalse(path.exists())

    def test_existing_output_is_refused_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}, clear=True):
            with self.assertRaises(FileExistsError):
                evaluate_native_baseline(fixture(), "mace", directory)


if __name__ == "__main__":
    unittest.main()
