import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("ugnn_wheel_archive", Path(__file__).resolve().parents[1] /
                                             "scripts/restore_offline_wheels.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OfflineWheelArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.content = b"PK\x03\x04tiny public wheel fixture"
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            entry = tarfile.TarInfo("example-1.0-py3-none-any.whl")
            entry.size = len(self.content)
            archive.addfile(entry, io.BytesIO(self.content))
        data = buffer.getvalue()
        (self.root / "chunk").write_bytes(data)
        self.manifest = {"version": 1, "archive": {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()},
                         "chunks": [{"filename": "chunk", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}],
                         "wheels": [{"filename": entry.name, "size": len(self.content), "sha256": hashlib.sha256(self.content).hexdigest()}]}
        self.path = self.root / "manifest.json"

    def tearDown(self):
        self.temporary.cleanup()

    def restore(self, **kwargs):
        self.path.write_text(json.dumps(self.manifest))
        return module.restore(self.path, self.root, self.root / "combined.tar", self.root / "wheels",
                              min_free_bytes=kwargs.get("min_free_bytes", 0))

    def test_verified_archive_roundtrip_and_idempotent_restore(self):
        self.assertEqual(self.restore()["verified_wheels"], 1)
        wheel = self.root / "wheels" / self.manifest["wheels"][0]["filename"]
        self.assertEqual(wheel.read_bytes(), self.content)
        self.assertEqual(self.restore()["verified_wheels"], 1)

    def test_corrupt_chunk_never_exposes_wheel(self):
        (self.root / "chunk").write_bytes(b"partial")
        with self.assertRaises(ValueError):
            self.restore()
        self.assertFalse((self.root / "wheels").exists())

    def test_mismatched_member_or_existing_output_fails(self):
        self.restore()
        wheel = self.root / "wheels" / self.manifest["wheels"][0]["filename"]
        wheel.write_bytes(b"conflicting wheel")
        with self.assertRaises(ValueError):
            self.restore()
        self.assertEqual(wheel.read_bytes(), b"conflicting wheel")
        self.manifest["wheels"][0]["filename"] = "different.whl"
        with self.assertRaises(ValueError):
            self.restore()

    def test_path_duplicate_and_reserve_rejection(self):
        with self.assertRaises(OSError):
            self.restore(min_free_bytes=10**20)
        self.manifest["chunks"].append(dict(self.manifest["chunks"][0]))
        with self.assertRaises(ValueError):
            self.restore()
        self.manifest["chunks"] = self.manifest["chunks"][:1]
        self.manifest["wheels"][0]["filename"] = "../escape.whl"
        with self.assertRaises(ValueError):
            self.restore()


if __name__ == "__main__":
    unittest.main()
