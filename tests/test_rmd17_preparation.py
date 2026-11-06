"""Source integrity, units and full declared MD split without neural dependencies."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.data.preparation.rmd17 import prepare_rmd17
from universal_gnn.data.preparation.rmd17.conversion import KCAL_MOL_TO_EV, _write_records, normalize_record
from universal_gnn.data.preparation.rmd17.partitions import build_manifest, frame_id, parse_indices
from universal_gnn.data.preparation.rmd17.source import SOURCE_FILES, read_arrays, verify_sources
from universal_gnn.data.splits import validate_manifest


def row(index):
    return normalize_record(index, numbers=[1], positions=[[index * .01, -1., 2.]],
                            energy=-100. + index, forces=[[0., 0., 0.]] if index == 0 else [[0., 1., -1.]], old_index=index + 10000)


def groups(count=2005):
    return [dict(id=frame_id(i), group=f"geometry:{i}") for i in range(count)]


class RMD17PreparationTests(unittest.TestCase):
    def test_pinned_original_author_files_sizes_and_hashes(self):
        self.assertEqual(set(SOURCE_FILES), {"rmd17_ethanol.npz", "readme.txt", "index_train_01.csv", "index_test_01.csv"})
        self.assertEqual(SOURCE_FILES["rmd17_ethanol.npz"]["bytes"], 67201791)
        self.assertEqual(SOURCE_FILES["rmd17_ethanol.npz"]["sha256"],
                         "0824d78c687b8ede25f7162c54c5c6434cfe37f9f859ee8f223c60379d7d5cf9")
        for value in SOURCE_FILES.values():
            self.assertEqual(len(value["sha256"]), 64)
            self.assertEqual(len(value["md5"]), 32)

    def test_source_fixture_hash_and_size_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            raw = b"original fixture"
            expected = {"file": dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), md5=hashlib.md5(raw).hexdigest())}
            with patch("universal_gnn.data.preparation.rmd17.source.SOURCE_FILES", expected):
                (path / "file").write_bytes(raw)
                self.assertEqual(verify_sources(path), expected)
                (path / "file").write_bytes(b"x" * len(raw))
                with self.assertRaisesRegex(ValueError, "checksum"):
                    verify_sources(path)
                (path / "file").write_bytes(raw + b" ")
                with self.assertRaisesRegex(ValueError, "size"):
                    verify_sources(path)
                (path / "file").write_bytes(raw)
                with patch.object(Path, "is_symlink", return_value=True), self.assertRaisesRegex(ValueError, "symlink"):
                    verify_sources(path)

    def test_official_csv_exact_count_unique_range_and_integer_contract(self):
        self.assertEqual(parse_indices("2\n0\n", source_count=3, expected_count=2), [2, 0])
        for text in ["2\n2\n", "0\n3\n", "-1\n0\n", "0.0\n1\n", "0\n", "True\n1\n", "０\n1\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_indices(text, source_count=3, expected_count=2)

    def test_units_total_energy_force_sign_zero_and_no_old_labels(self):
        value = normalize_record(0, numbers=[1, 8], positions=[[0., -2., 1.], [1., 2., -1.]],
                                 energy=-1., forces=[[1., -1., 0.], [0., 0., 0.]], old_index=42)
        self.assertAlmostEqual(KCAL_MOL_TO_EV, .04336410424180094, places=16)
        self.assertEqual(value["targets"]["energy"], -KCAL_MOL_TO_EV)
        self.assertEqual(value["targets"]["forces"], [[KCAL_MOL_TO_EV, -KCAL_MOL_TO_EV, 0.], [0., 0., 0.]])
        self.assertEqual(set(value["targets"]), {"energy", "forces"})
        self.assertEqual(value["metadata"]["old_index"], 42)
        zero = normalize_record(0, numbers=[1], positions=[[0., 0., 0.]], energy=0., forces=[[0., 0., 0.]], old_index=1)
        self.assertEqual(zero["targets"], dict(energy=0., forces=[[0., 0., 0.]]))

    def test_positions_remain_unwrapped_with_nonperiodic_identity_placeholder(self):
        value = row(501)
        self.assertEqual(value["positions"], [[5.01, -1., 2.]])
        self.assertEqual(value["pbc"], [False] * 3)
        self.assertEqual(value["cell"], [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        again = row(501)
        self.assertEqual(value["metadata"]["geometry_sha256"], again["metadata"]["geometry_sha256"])

    def test_invalid_shapes_boolean_nonfinite_labels_and_indices_rejected(self):
        kwargs = dict(numbers=[1], positions=[[0., 0., 0.]], energy=1., forces=[[1., 0., 0.]], old_index=0)
        for field, value in [("energy", float("nan")), ("energy", True), ("numbers", [True]),
                             ("forces", [[float("inf"), 0., 0.]]), ("forces", []), ("positions", [[0., 0.]]),
                             ("old_index", -1), ("old_index", True)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                normalize_record(0, **{**kwargs, field: value})
        for index in [-1, True, 1.5]:
            with self.assertRaises(ValueError):
                frame_id(index)

    def test_entire_source_partition_and_original_test_cohort_are_retained(self):
        records = groups()
        train, test = list(range(1000)), list(range(1000, 2000))
        result = build_manifest(records, source_sha256="a" * 64, official_train=train, official_test=test)
        self.assertEqual(result["counts"], dict(train=900, validation=100, test=1005))
        self.assertEqual(set(result["partitions"]["train"]) | set(result["partitions"]["validation"]), set(train))
        self.assertEqual(result["partitions"]["test"], list(range(1000, 2005)))
        self.assertEqual(result["evaluation_cohorts"], dict(official_test_01=test))
        self.assertFalse(result["protocol"]["training_rng_used"])
        self.assertFalse(result["protocol"]["temporal_independence_claimed"])
        validate_manifest(result, source_sha256="a" * 64, source_count=2005)

    def test_split_determinism_does_not_consult_labels_or_training_rng(self):
        records = groups()
        original = build_manifest(records, source_sha256="a" * 64, official_train=list(range(1000)), official_test=list(range(1000, 2000)))
        changed = copy.deepcopy(records)
        for i, value in enumerate(changed):
            value.update(targets=dict(energy=-1.e20 * i), seed=789)
        again = build_manifest(changed, source_sha256="b" * 64, official_train=list(range(999, -1, -1)), official_test=list(range(1000, 2000)))
        self.assertEqual(original["partitions"], again["partitions"])
        self.assertEqual(original["evaluation_cohorts"], again["evaluation_cohorts"])

    def test_bad_official_lists_and_changed_source_order_fail_closed(self):
        records = groups()
        for train, test in [(list(range(999)), list(range(1000, 2000))),
                            (list(range(1000)), list(range(999, 1999))),
                            ([0] * 1000, list(range(1000, 2000))),
                            (list(range(1000)), list(range(1000, 1999)) + [2005])]:
            with self.assertRaises(ValueError):
                build_manifest(records, source_sha256="a" * 64, official_train=train, official_test=test)
        records.reverse()
        with self.assertRaisesRegex(ValueError, "ordering"):
            build_manifest(records, source_sha256="a" * 64, official_train=list(range(1000)), official_test=list(range(1000, 2000)))

    def test_exact_geometry_cross_development_test_is_rejected_without_drop(self):
        records = groups()
        records[1000]["group"] = records[0]["group"]
        with self.assertRaisesRegex(ValueError, "Group leakage"):
            build_manifest(records, source_sha256="a" * 64, official_train=list(range(1000)), official_test=list(range(1000, 2000)))

    def test_stream_writer_is_full_deterministic_and_preserves_all_zeros(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            saved = []
            for folder in ["first", "second"]:
                out = root / folder
                out.mkdir()
                audit = _write_records(out, (row(i) for i in range(2005)), expected_count=2005,
                    official_train=list(range(1000)), official_test=list(range(1000, 2000)))
                raw = (out / "structures.jsonl").read_bytes()
                self.assertEqual(audit["dataset_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(audit["source_records"], 2005)
                self.assertEqual(audit["excluded_records"], 0)
                self.assertEqual(audit["whole_zero_force_records"], 1)
                self.assertEqual(audit["split_counts"], dict(train=900, validation=100, test=1005))
                self.assertFalse((out / "structures.jsonl.partial").exists())
                self.assertEqual(len(raw.splitlines()), 2005)
                self.assertEqual(json.loads(raw.splitlines()[100])["targets"]["energy"], 0.)
                self.assertEqual(json.loads(raw.splitlines()[0])["targets"]["forces"], [[0., 0., 0.]])
                saved.append((raw, (out / "split.json").read_bytes()))
            self.assertEqual(saved[0], saved[1])
            with self.assertRaises(FileExistsError):
                _write_records(root / "first", [], expected_count=2005, official_train=[], official_test=[])

    def test_incomplete_or_duplicate_old_frames_never_write_success_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for mode in ["count", "duplicate"]:
                out = root / mode
                out.mkdir()
                rows = [row(i) for i in range(3)]
                if mode == "duplicate":
                    rows[1]["metadata"]["old_index"] = rows[0]["metadata"]["old_index"]
                with self.assertRaisesRegex(ValueError, "count|unique"):
                    _write_records(out, rows, expected_count=4, official_train=[], official_test=[])
                self.assertFalse((out / "audit.json").exists())
                self.assertFalse((out / "structures.jsonl").exists())
                self.assertTrue((out / "structures.jsonl.partial").exists())

    def test_full_api_and_cli_refuse_login_without_loading_numerical_packages(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Slurm"):
                prepare_rmd17("unused", "unused")
            with self.assertRaisesRegex(RuntimeError, "Slurm"):
                read_arrays("unused")
        environment = {key: value for key, value in os.environ.items() if key != "SLURM_JOB_ID"}
        script = Path(__file__).resolve().parents[1] / "scripts/prepare_rmd17.py"
        completed = subprocess.run([sys.executable, "-S", str(script), "--raw", "unused", "--output", "unused"],
                                   capture_output=True, text=True, env=environment)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("requires Slurm", completed.stderr)
        environment["PYTHONPATH"] = str(script.parents[1] / "src")
        code = ("import sys; from universal_gnn.data.preparation.rmd17 import prepare_rmd17; "
                "from universal_gnn.data.preparation.rmd17.source import read_arrays; "
                "assert not {'numpy','torch'} & sys.modules.keys()")
        subprocess.run([sys.executable, "-S", "-c", code], check=True, env=environment, capture_output=True)

    def test_full_api_failure_report_and_fresh_output_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "failed"
            with patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), patch(
                    "universal_gnn.data.preparation.rmd17.conversion.verify_sources", side_effect=ValueError("bad checksum")):
                with self.assertRaisesRegex(ValueError, "checksum"):
                    prepare_rmd17("unused", output)
                self.assertEqual(json.loads((output / "report.json").read_bytes())["status"], "failed")
                self.assertFalse((output / "audit.json").exists())
                with self.assertRaises(FileExistsError):
                    prepare_rmd17("unused", output)


if __name__ == "__main__":
    unittest.main()
