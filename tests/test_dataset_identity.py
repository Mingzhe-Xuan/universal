import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from universal_gnn.data.identity import check_expected_digest, validate_dataset_digest
from universal_gnn.data.splits import create_manifest
from universal_gnn.data.splits.loading import load_partition


class Source:
    sha256 = hashlib.sha256(b"exact-jsonl-fixture").hexdigest()
    identifiers = [f"record-{index}" for index in range(6)]

    def __len__(self):
        return len(self.identifiers)


class DatasetIdentityTests(unittest.TestCase):
    def test_source_override_clears_inherited_pins_and_keeps_explicit_new_pins(self):
        from universal_gnn.engine.configuration import resolve_dataset_settings

        base = dict(backbone=dict(name="gcn"), task=dict(kind="supervised", property="bandgap"),
                    dataset=dict(path="old.jsonl", sha256="a" * 64, split_manifest="old-split.json",
                                 split_manifest_sha256="b" * 64, partition="train"))
        changed = resolve_dataset_settings({}, base=base["dataset"], source_override="new.jsonl")
        self.assertEqual(changed, {"path": "new.jsonl"})
        file_override = resolve_dataset_settings({"path": "new.jsonl", "sha256": "c" * 64}, base=base["dataset"])
        self.assertEqual(file_override, {"path": "new.jsonl", "sha256": "c" * 64})
        matching = resolve_dataset_settings({}, base=base["dataset"], source_override="old.jsonl")
        self.assertEqual(matching, base["dataset"])

    def test_file_bytes_and_index_reuse_without_new_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json";path.write_bytes(b"fixed source")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            validate_dataset_digest(dict(path=path, sha256=digest))
            validate_dataset_digest(dict(path="does-not-exist.jsonl", sha256=digest), actual_sha256=digest)
            path.write_bytes(b"changed source")
            with self.assertRaisesRegex(ValueError, "immutable"):
                validate_dataset_digest(dict(path=path, sha256=digest))

    def test_invalid_plugin_hash_and_optional_fields_fail_explicitly(self):
        validate_dataset_digest({})
        for digest in (True, "bad", "A" * 64):
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, "lowercase"):
                validate_dataset_digest(dict(path="not-read.json", sha256=digest))
        with self.assertRaisesRegex(ValueError, "plugin"):
            validate_dataset_digest(dict(path="plugin:/fixture", sha256="a" * 64), actual_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "requires"):
            load_partition(Source(), dict(split_manifest_sha256="a" * 64))

    def test_canonical_manifest_pin_allows_formatting_and_rejects_changed_assignments(self):
        source = Source()
        manifest = create_manifest([dict(id=name, group=name) for name in source.identifiers], source_sha256=source.sha256)
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "split.json";path.write_text(json.dumps(manifest, indent=4))
            settings = dict(path="indexed.jsonl", sha256=source.sha256, split_manifest=path,
                            split_manifest_sha256=digest, partition="train")
            selected, _, actual = load_partition(source, settings)
            self.assertEqual(actual, digest)
            self.assertEqual(selected, manifest["partitions"]["train"])
            path.write_text(json.dumps(manifest, sort_keys=True))
            self.assertEqual(load_partition(source, settings)[2], digest)
            changed = copy.deepcopy(manifest)
            changed["partitions"]["train"][0], changed["partitions"]["test"][0] = changed["partitions"]["test"][0], changed["partitions"]["train"][0]
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "immutable"):
                load_partition(source, settings)
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "dataset.sha256"):
                load_partition(source, {**settings, "sha256": "f" * 64})


if __name__ == "__main__":
    unittest.main()
