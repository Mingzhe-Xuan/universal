"""Pure protocol fixtures; real CPU softmax is separately exercised in Slurm."""

from contextlib import contextmanager, nullcontext
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.classification_assessment import select_threshold, threshold_prediction
from universal_gnn.benchmarks.classification_assessment.runtime import assess_threshold
from universal_gnn.benchmarks.execution.gates import canonical_digest, file_sha
from universal_gnn.benchmarks.prediction_assessment.contracts import full_inference_config
from universal_gnn.data.splits import create_manifest


def write(path, value):
    Path(path).write_text(json.dumps(value, allow_nan=False), encoding="utf8")


def write_rows(path, rows):
    Path(path).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf8")


def protocol_softmax(logits, dtype):
    value = logits[0][1] - logits[0][0]
    return 1 / (1 + math.exp(-value)), int(value > 0)


@contextmanager
def fixture(*, reverse_test_labels=False, dtype="float32", directory=None):
    with (tempfile.TemporaryDirectory() if directory is None else nullcontext(str(directory))) as directory:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        source = root / "source.jsonl"
        source_rows = [dict(id=str(i), numbers=[14], targets=dict(classification=(i % 2) ^ int(reverse_test_labels and i >= 4))) for i in range(6)]
        write_rows(source, source_rows)
        split = root / "split.json"
        manifest = create_manifest([dict(id=str(i), group=str(i)) for i in range(6)], source_sha256=file_sha(source),
            official={str(i): "train" if i < 2 else "validation" if i < 4 else "test" for i in range(6)})
        write(split, manifest)
        best = root / "best.pt"
        best.write_bytes(b"fixture checkpoint, must never be loaded")
        config = dict(structures="all", max_atoms=None, dtype=dtype, device="cuda", batch_size=2, seed=123,
            task=dict(kind="supervised", property="classification"),
            dataset=dict(path=str(source), sha256=file_sha(source), partition="train",
                bindings=dict(classification=dict(key="classification", unit="class")),
                split_manifest=str(split), split_manifest_sha256=canonical_digest(manifest)))
        original_metrics = dict(fixture="original heldout metrics preserved verbatim")
        trained = dict(passed=True, config=config, selected_structures=2, best_checkpoint=str(best),
            heldout=dict(partition="test", checkpoint_role="validation_best", structures=2, test_structures=2,
                declared_train_structures=2, validation_structures=2, source_structures=6,
                source_sha256=file_sha(source), metrics=dict(classification=original_metrics),
                selection=dict(best_sha256=file_sha(best), tracker=dict(manifest_sha256=canonical_digest(manifest)))))
        report = root / "training.json"
        write(report, trained)
        stream = root / "inference.jsonl"
        rows = [dict(type="metadata", structures=[], checkpoint=str(best), structure_count=6,
                     config=full_inference_config(config))]
        for i, score in enumerate([.2, .8, .1, .4, .45, .6]):
            rows.append(dict(type="prediction", id=str(i), derived={},
                predictions=dict(classification=[[0., math.log(score / (1 - score))]])))
        rows.append(dict(type="completed", structure_count=6))
        write_rows(stream, rows)
        yield root, report, stream, trained, rows


def assess(report, stream, output):
    return assess_threshold(report, stream, output, prediction_sha256=file_sha(stream), prediction_bytes=stream.stat().st_size)


class ThresholdSelectionTests(unittest.TestCase):
    def choose(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            return select_threshold(rows, Path(directory) / "validation.sqlite")

    def test_validation_optimum_and_threshold_equality(self):
        selected = self.choose([("n", .1, 0), ("p", .4, 1)])
        self.assertEqual(selected["rule"], dict(kind="score_at_least", value=.4))
        self.assertEqual(selected["balanced_accuracy"], 1)
        self.assertEqual(threshold_prediction(.4, selected["rule"]), 1)
        self.assertEqual(threshold_prediction(.39, selected["rule"]), 0)
        self.assertFalse(selected["test_labels_used_for_selection"])

    def test_ties_move_together_and_nearest_half_is_preferred(self):
        selected = self.choose([("n", .7, 0), ("p", .7, 1)])
        self.assertEqual(selected["rule"], dict(kind="score_at_least", value=.5))
        self.assertEqual(selected["confusion_matrix_true_by_predicted"], [[0, 1], [0, 1]])
        self.assertEqual(selected["balanced_accuracy"], .5)

    def test_extreme_zero_and_one_are_candidates(self):
        selected = self.choose([("n", 0, 0), ("p", 1, 1)])
        self.assertEqual(selected["rule"]["value"], .5)
        self.assertEqual(selected["balanced_accuracy"], 1)
        self.assertEqual(threshold_prediction(1, dict(kind="all_negative", value=None)), 0)

    def test_equal_distance_tie_prefers_higher_threshold(self):
        selected = self.choose([("p0", .75, 1), ("n0", .6, 0), ("p1", .25, 1), ("n1", .1, 0)])
        self.assertEqual(selected["rule"]["value"], .75)
        self.assertEqual(selected["balanced_accuracy"], .75)

    def test_exact_objective_and_input_order_invariance(self):
        rows = [(str(i), score, label) for i, (score, label) in enumerate([(.1, 0), (.2, 1), (.6, 1), (.8, 0), (.9, 1)])]
        a, b = self.choose(rows), self.choose(reversed(rows))
        self.assertEqual(a, b)
        self.assertEqual(a["objective_denominator"], 12)
        self.assertEqual(a["objective_numerator"], 9)
        self.assertEqual(a["rule"]["value"], .2)

    def test_empty_single_class_repeated_ids_and_invalid_values_rejected(self):
        cases = [[], [("n", .1, 0)], [("n", .1, 0), ("n", .8, 1)],
                 [("n", True, 0), ("p", .4, 1)], [("n", math.nan, 0), ("p", .4, 1)],
                 [("n", math.inf, 0), ("p", .4, 1)], [("n", -.1, 0), ("p", .4, 1)],
                 [("n", 1.1, 0), ("p", .4, 1)], [("n", .1, False), ("p", .4, 1)],
                 [("", .1, 0), ("p", .4, 1)]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.choose(rows)

    def test_existing_spool_and_invalid_frozen_rules_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.sqlite"
            path.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                select_threshold([], path)
            self.assertEqual(path.read_bytes(), b"keep")
        for rule in [{}, dict(kind="score_at_least", value=True), dict(kind="unknown", value=.5)]:
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                threshold_prediction(.5, rule)


class ThresholdAssessmentTests(unittest.TestCase):
    def test_complete_assessment_uses_validation_and_preserves_original_inputs(self):
        with fixture() as (root, report, stream, trained, _), patch(
                "universal_gnn.benchmarks.classification_assessment.runtime.class_observation", side_effect=protocol_softmax):
            before = {path: path.read_bytes() for path in [report, stream, Path(trained["best_checkpoint"])]}
            result = assess(report, stream, root / "out")
            self.assertEqual((result["validation_structures"], result["test_structures"], result["source_structures"]), (2, 2, 6))
            self.assertAlmostEqual(result["selection"]["rule"]["value"], .4)
            self.assertEqual(result["selection"]["balanced_accuracy"], 1)
            self.assertEqual(result["metrics"]["balanced_accuracy"], .5)
            self.assertEqual(result["same_stream_argmax_metrics"]["balanced_accuracy"], 1)
            self.assertEqual(result["metrics"]["roc_auc"], result["same_stream_argmax_metrics"]["roc_auc"])
            self.assertEqual(result["unchanged_original_heldout_metrics"], trained["heldout"]["metrics"]["classification"])
            self.assertTrue((root / "out/selection.json").is_file())
            self.assertEqual(result["selection_sha256"], file_sha(root / "out/selection.json"))
            self.assertEqual(result["formal_training_runs"], 0)
            self.assertFalse(result["model_execution_performed"])
            for path, value in before.items():
                self.assertEqual(path.read_bytes(), value)

    def test_counterfactual_test_labels_do_not_change_validation_selection(self):
        selections, test_metrics = [], []
        for reverse in [False, True]:
            with fixture(reverse_test_labels=reverse) as (root, report, stream, _, _), patch(
                    "universal_gnn.benchmarks.classification_assessment.runtime.class_observation", side_effect=protocol_softmax):
                result = assess(report, stream, root / "out")
                selections.append(result["selection"])
                test_metrics.append(result["metrics"])
        self.assertEqual(selections[0], selections[1])
        self.assertNotEqual(test_metrics[0]["roc_auc"], test_metrics[1]["roc_auc"])

    def test_selection_file_is_frozen_before_test_softmax(self):
        with fixture() as (root, report, stream, _, rows):
            test_logits = [row["predictions"]["classification"] for row in rows if row.get("id") in {"4", "5"}]
            def observed(logits, dtype):
                if logits in test_logits:
                    self.assertTrue((root / "out/selection.json").exists())
                return protocol_softmax(logits, dtype)
            with patch("universal_gnn.benchmarks.classification_assessment.runtime.class_observation", side_effect=observed):
                assess(report, stream, root / "out")

    def test_wrong_sha_best_and_incomplete_or_reordered_streams_refused(self):
        for mode in ["sha", "best", "truncated", "reordered"]:
            with self.subTest(mode=mode), fixture() as (root, report, stream, trained, rows):
                digest, size = file_sha(stream), stream.stat().st_size
                if mode == "sha":
                    digest = "0" * 64
                elif mode == "best":
                    Path(trained["best_checkpoint"]).write_bytes(b"changed")
                else:
                    altered = rows[:-1] if mode == "truncated" else [rows[0], rows[2], rows[1], *rows[3:]]
                    write_rows(stream, altered)
                    digest, size = file_sha(stream), stream.stat().st_size
                with self.assertRaises(ValueError):
                    assess_threshold(report, stream, root / "out", prediction_sha256=digest, prediction_bytes=size)
                self.assertFalse((root / "out/report.json").exists())

    def test_existing_destination_refused_without_changes(self):
        with fixture() as (root, report, stream, _, _):
            (root / "out").mkdir()
            (root / "out/sentinel").write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                assess(report, stream, root / "out")
            self.assertEqual((root / "out/sentinel").read_bytes(), b"keep")

    def test_selection_or_checkpoint_mutation_during_test_is_rejected(self):
        for mode in ["selection", "checkpoint"]:
            with self.subTest(mode=mode), fixture() as (root, report, stream, trained, rows):
                test_logits = rows[5]["predictions"]["classification"]
                def observed(logits, dtype):
                    if logits == test_logits:
                        target = root / "out/selection.json" if mode == "selection" else Path(trained["best_checkpoint"])
                        target.write_bytes(b"changed during test")
                    return protocol_softmax(logits, dtype)
                with patch("universal_gnn.benchmarks.classification_assessment.runtime.class_observation", side_effect=observed):
                    with self.assertRaisesRegex(ValueError, "changed"):
                        assess(report, stream, root / "out")
                self.assertFalse((root / "out/report.json").exists())

    def test_fresh_import_and_cli_help_do_not_load_numeric_libraries(self):
        code = ("import sys;sys.path.insert(0,'src');"
                "import universal_gnn.benchmarks.classification_assessment.runtime;"
                "assert 'torch' not in sys.modules and 'numpy' not in sys.modules")
        subprocess.run([sys.executable, "-S", "-c", code], check=True)
        result = subprocess.run([sys.executable, "-S", "scripts/evaluate_classification_threshold.py", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--prediction-sha256", result.stdout)

    def test_cli_refuses_execution_outside_slurm(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", [
                "evaluate_classification_threshold.py", "--report", "absent", "--predictions", "absent",
                "--prediction-sha256", "0" * 64, "--prediction-bytes", "1", "--output", "unused"]):
            with self.assertRaisesRegex(RuntimeError, "Slurm"):
                runpy.run_path("scripts/evaluate_classification_threshold.py", run_name="__main__")

    def test_cli_refuses_dirty_source_before_reading_inputs(self):
        with patch.dict(os.environ, {"SLURM_JOB_ID": "fixture", "CUDA_VISIBLE_DEVICES": ""}), patch.object(sys, "argv", [
                "evaluate_classification_threshold.py", "--report", "absent", "--predictions", "absent",
                "--prediction-sha256", "0" * 64, "--prediction-bytes", "1", "--output", "unused"]), \
                patch("subprocess.check_output", side_effect=["fixture-commit", " M source.py"]):
            with self.assertRaisesRegex(RuntimeError, "clean tracked source"):
                runpy.run_path("scripts/evaluate_classification_threshold.py", run_name="__main__")


if __name__ == "__main__":
    unittest.main()
