import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from universal_gnn.data.splits import create_manifest
from universal_gnn.data.splits.loading import load_partition
from universal_gnn.engine.evaluation.selection import ValidationTracker
from universal_gnn.engine.evaluation.heldout import (HoldoutEvaluation, candidate_path, file_sha256,
                                                   finite_json, verified_best)


class ValidationProtocolTests(unittest.TestCase):
    def test_true_minimum_and_independent_stopping_threshold(self):
        tracker = ValidationTracker("source", patience=2, min_delta=.1)
        self.assertTrue(tracker.update(1, 1.))
        self.assertTrue(tracker.update(2, .96))
        self.assertFalse(tracker.should_stop)
        self.assertTrue(tracker.update(3, .94))
        self.assertTrue(tracker.should_stop)
        self.assertEqual(tracker.state["best_epoch"], 3)
        self.assertEqual(tracker.state["best_loss"], .94)
        self.assertTrue(tracker.update(4, .8))
        self.assertFalse(tracker.should_stop)

    def test_continuation_replays_and_rejects_tampering(self):
        tracker = ValidationTracker("source", patience=3)
        for epoch, loss in enumerate([1., .8, .9], 1):
            tracker.update(epoch, loss)
        saved = tracker.snapshot()
        resumed = ValidationTracker("source", patience=3, state=saved)
        self.assertEqual(saved, resumed.snapshot())
        for epoch, loss in enumerate([.7, .75], 4):
            self.assertEqual(tracker.update(epoch, loss), resumed.update(epoch, loss))
        self.assertEqual(tracker.snapshot(), resumed.snapshot())
        corrupt = copy.deepcopy(saved)
        corrupt["best_epoch"] = 3
        with self.assertRaises(ValueError):
            ValidationTracker("source", patience=3, state=corrupt)
        with self.assertRaises(ValueError):
            ValidationTracker("different", patience=3, state=saved)
        with self.assertRaises(ValueError):
            ValidationTracker("source", patience=4, state=saved)
        self.assertEqual(saved["best_epoch"], 2)

    def test_invalid_protocol_or_loss(self):
        for options in ({"patience": 0}, {"patience": True}, {"min_delta": float("nan")}, {"min_delta": -1}):
            with self.assertRaises(ValueError):
                ValidationTracker("source", **options)
        tracker = ValidationTracker("source")
        for epoch, loss, error in [(2, 1, ValueError), (1, float("inf"), FloatingPointError),
                                    (1, -1, FloatingPointError)]:
            with self.assertRaises(error):
                tracker.update(epoch, loss)
        self.assertEqual(finite_json([[1., float("nan")], [float("inf"), 0.]]), [[1., None], [None, 0.]])

    def test_source_bound_partition_protocol(self):
        records = [{"id": str(i), "group": str(i)} for i in range(10)]
        class Source:
            sha256 = hashlib.sha256(b"fixture").hexdigest()
            identifiers = [str(i) for i in range(10)]
            def __len__(self):
                return 10
        source = Source()
        manifest = create_manifest(records, source_sha256=source.sha256)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "split.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            settings = {"split_manifest": str(path), "partition": "train"}
            indices, loaded, digest = load_partition(source, settings)
            self.assertEqual(indices, manifest["partitions"]["train"])
            self.assertEqual(loaded, manifest)
            self.assertEqual(len(digest), 64)
            test, _, same_digest = load_partition(source, settings, partition="test")
            self.assertFalse(set(test) & set(indices))
            self.assertEqual(same_digest, digest)
            source.identifiers = list(reversed(source.identifiers))
            with self.assertRaisesRegex(ValueError, "source order"):
                load_partition(source, settings)
            with self.assertRaises(ValueError):
                load_partition(source, {"split_manifest": str(path)})
        self.assertEqual(list(load_partition(source, {})[0]), list(range(10)))
        with self.assertRaises(ValueError):
            load_partition(source, {"partition": "test"})

    def test_best_last_commit_crash_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            best = Path(directory) / "checkpoint.best.pt"
            candidate = candidate_path(best)
            best.write_bytes(b"old best weights")
            old = {"best_checkpoint": str(best), "best_sha256": file_sha256(best)}
            candidate.write_bytes(b"new best weights")
            new = {"best_checkpoint": str(best), "best_sha256": file_sha256(candidate)}
            self.assertEqual(verified_best(old), best)
            self.assertEqual(verified_best(new), candidate)
            manager = HoldoutEvaluation.__new__(HoldoutEvaluation)
            manager.best_checkpoint = best
            manager.best_sha256 = new["best_sha256"]
            manager.tracker = ValidationTracker("fixture")
            manager.finalize_best()
            self.assertEqual(verified_best(new), best)
            self.assertFalse(candidate.exists())
            with self.assertRaises(ValueError):
                verified_best(old)


if __name__ == "__main__":
    unittest.main()
