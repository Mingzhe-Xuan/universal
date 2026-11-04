"""Pure controls for full generation protocol and phase separation."""

import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.registry import DATASETS, canonical_digest
from universal_gnn.benchmarks.generation.preparation import (
    generation_spec, phase_probes, prepare_generation_pair, verify_resolved,
)
from universal_gnn.benchmarks.probes.schedule import schedule_settings


def matrix_fixture(provider="mace"):
    matrix = dict(version=1, kind="arxiv_v1_primary_matrix", definition_revision=2,
                  registry={}, registry_sha256=canonical_digest({}), cases=[], pairs=[])
    pair = "seed-123--generation--" + provider
    for mode in ("pretrained", "scratch"):
        config = dict(seed=123, structures="all", max_atoms=None, device="cuda", dtype="float32",
                      batch_size=16, epochs=300, evaluation=dict(patience=30, min_delta=0.),
                      backbone=dict(name=provider, implementation="official", initialization=mode),
                      dataset=dict(path="data/arxiv-v1/perov5/structures.jsonl", sha256=DATASETS["perov5"][0],
                                   split_manifest="split.json", partition="train"),
                      task=dict(kind="generation", sampling=dict(steps=100, inner_steps=2)),
                      generation_corruption="per_epoch_structure_v2", validate_sampling=False)
        matrix["cases"].append(dict(id=pair + "--" + mode, pair_id=pair, task="generation",
            initialization=mode, config=config, config_sha256=canonical_digest(config),
            generation_quality=dict(samples=1000, draws_per_condition=5, seed=456,
                                    interpretation="conditional geometry only; no DFT stability claim"),
            sampling_preflight=dict(warmup_batches=1, measure_batches=5, initial_batch_size=4),
            preflight=dict(warmup_batches=2, measure_batches=100, initial_batch_size=16)))
    matrix["pairs"].append(dict(id=pair, cases=[c["id"] for c in matrix["cases"]]))
    return matrix, pair


def prior_fixture():
    return dict(sampling_volume_source="train_fit", statistics=dict(
        structures=11356, fitted_partition="train", training_fingerprint="a" * 64, volume_per_atom=14.129))


class GenerationPairPreparationTests(unittest.TestCase):
    def test_four_original_providers_and_all_training_records(self):
        for provider in ("cgcnn", "alignn", "mace", "nequip"):
            with self.subTest(provider=provider):
                matrix, pair = matrix_fixture(provider)
                snapshot = copy.deepcopy(matrix)
                spec = generation_spec(matrix, pair)
                self.assertEqual(spec["counts"], dict(train=11356, validation=3787, test=3785))
                self.assertEqual(spec["quality"]["samples"], 1000)
                spec["configs"]["pretrained"]["batch_size"] = 1
                self.assertEqual(matrix, snapshot)

    def test_changed_scientific_recipe_is_rejected_even_with_rehashed_case(self):
        changes = [lambda c: c["task"]["sampling"].update(steps=20),
                   lambda c: c.update(dtype="float64"), lambda c: c.update(epochs=3),
                   lambda c: c.update(structures=64), lambda c: c.update(max_atoms=5),
                   lambda c: c.update(generation_corruption="per_structure_v1"),
                   lambda c: c["dataset"].update(sha256="b" * 64),
                   lambda c: c.update(validate_sampling=True)]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                matrix, pair = matrix_fixture()
                for case in matrix["cases"]:
                    change(case["config"])
                    case["config_sha256"] = canonical_digest(case["config"])
                with self.assertRaises(ValueError):
                    generation_spec(matrix, pair)

    def test_quality_and_sampling_budgets_cannot_shrink(self):
        for field, key, value in [("generation_quality", "samples", 8),
                                  ("generation_quality", "draws_per_condition", 1),
                                  ("sampling_preflight", "measure_batches", 1),
                                  ("preflight", "measure_batches", 10)]:
            with self.subTest(field=field, key=key):
                matrix, pair = matrix_fixture()
                matrix["cases"][0][field][key] = value
                with self.assertRaises(ValueError):
                    generation_spec(matrix, pair)

    def test_sampling_probe_keeps_every_worst_case_and_training_probe(self):
        probe = dict(indices=list(range(9)), worst_indices=list(range(8)),
                     warmup_batches=2, measure_batches=100, coverage={"structures": 11356})
        snapshot = copy.deepcopy(probe)
        sample = phase_probes(probe, dict(warmup_batches=1, measure_batches=5))
        self.assertEqual(sample["worst_indices"], probe["worst_indices"])
        self.assertEqual(schedule_settings(sample, 4)["measure_batches"], 9)
        sample["coverage"]["structures"] = 1
        self.assertEqual(probe, snapshot)

    def test_resolved_prior_and_separate_batches_preserve_frozen_recipe(self):
        matrix, pair = matrix_fixture("alignn")
        config = generation_spec(matrix, pair)["configs"]["pretrained"]
        prior = prior_fixture()
        for batch in (16, 4, 2, 1):
            actual = copy.deepcopy(config)
            actual.update(batch_size=batch, generation_prior=prior)
            actual["task"]["sampling"]["volume_per_atom"] = prior["statistics"]["volume_per_atom"]
            verify_resolved(actual, config, batch, prior, 11356)
        self.assertEqual(config["batch_size"], 16)
        self.assertNotIn("generation_prior", config)

    def test_partial_or_wrong_source_native_statistics_are_rejected(self):
        matrix, pair = matrix_fixture()
        config = generation_spec(matrix, pair)["configs"]["scratch"]
        prior = prior_fixture()
        actual = copy.deepcopy(config)
        actual.update(batch_size=4, generation_prior=prior)
        actual["task"]["sampling"]["volume_per_atom"] = prior["statistics"]["volume_per_atom"]
        stats = dict(structures=11356, declared_training_structures=11356,
                     source_sha256=config["dataset"]["sha256"], dtype="float32")
        actual["backbone"]["neighbor_statistics"] = stats
        verify_resolved(actual, config, 4, prior, 11356)
        for key, value in [("structures", 64), ("declared_training_structures", 64),
                           ("source_sha256", "c" * 64), ("dtype", "float64")]:
            with self.subTest(key=key):
                wrong = copy.deepcopy(actual)
                wrong["backbone"]["neighbor_statistics"][key] = value
                with self.assertRaises(ValueError):
                    verify_resolved(wrong, config, 4, prior, 11356)

    def test_resolved_steps_learning_rule_and_prior_cannot_change(self):
        matrix, pair = matrix_fixture("cgcnn")
        config = generation_spec(matrix, pair)["configs"]["pretrained"]
        prior = prior_fixture()
        actual = copy.deepcopy(config)
        actual.update(batch_size=4, generation_prior=prior)
        actual["task"]["sampling"]["volume_per_atom"] = prior["statistics"]["volume_per_atom"]
        changes = [lambda c: c["task"]["sampling"].update(steps=10),
                   lambda c: c.update(learning_rate=99),
                   lambda c: c["generation_prior"]["statistics"].update(structures=64),
                   lambda c: c["backbone"].update(neighbor_statistics={"structures": 11356})]
        for i, change in enumerate(changes):
            with self.subTest(change=i):
                wrong = copy.deepcopy(actual)
                change(wrong)
                with self.assertRaises(ValueError):
                    verify_resolved(wrong, config, 4, prior, 11356)

    def test_slurm_guard_precedes_output_and_runtime(self):
        matrix, pair = matrix_fixture()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            output = Path(directory) / "not-created"
            with self.assertRaisesRegex(RuntimeError, "must run through Slurm"):
                prepare_generation_pair(matrix, pair, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
