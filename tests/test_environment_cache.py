import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("ugnn_environment_cache", Path(__file__).resolve().parents[1] /
                                             "scripts/recover_environment_cache.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cache_key, recover_resource = module.cache_key, module.recover_resource


class EnvironmentCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.payload = b"PK\x03\x04small verified wheel fixture"
        self.url = "https://files.pythonhosted.org/packages/example-1.0-py3-none-any.whl"
        self.resource = {"filename": "example-1.0-py3-none-any.whl", "size": len(self.payload),
                         "sha256": hashlib.sha256(self.payload).hexdigest(), "cache_urls": [self.url]}

    def tearDown(self):
        self.temporary.cleanup()

    def cache_path(self, version="http-v2", suffix=".body"):
        key = cache_key(self.url)
        path = self.root / "cache" / version / Path(*key[:5]) / (key + suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def recover(self, **kwargs):
        return recover_resource(self.resource, self.root / "cache", self.root / "wheels",
                                min_free_bytes=kwargs.get("min_free_bytes", 0))

    def test_modern_cache_exact_digest_and_existing_destination(self):
        path = self.cache_path()
        path.write_bytes(self.payload)
        result = self.recover()
        self.assertEqual(result["status"], "recovered")
        self.assertEqual((self.root / "wheels" / self.resource["filename"]).read_bytes(), self.payload)
        self.assertEqual(path.read_bytes(), self.payload)
        self.assertEqual(self.recover()["status"], "verified_existing")

    def test_legacy_cache_and_mismatch_not_overwritten(self):
        from pip._vendor import msgpack

        path = self.cache_path("http", "")
        original = b"cc=4," + msgpack.packb({"response": {"body": self.payload}}, use_bin_type=True)
        path.write_bytes(original)
        result = self.recover()
        self.assertEqual(result["mode"], "legacy_copy")
        self.assertEqual(path.read_bytes(), original)
        destination = self.root / "wheels" / self.resource["filename"]
        destination.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "destination"):
            self.recover()
        self.assertEqual(destination.read_bytes(), b"corrupt")

    def test_missing_or_corrupt_cache_stays_explicit(self):
        self.assertEqual(self.recover()["status"], "missing")
        path = self.cache_path()
        path.write_bytes(b"wrong bytes")
        result = self.recover()
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["checks"][0]["status"], "digest_or_size_mismatch")
        self.assertFalse((self.root / "wheels" / self.resource["filename"]).exists())

    def test_keys_urls_paths_and_reserve(self):
        from pip._vendor.cachecontrol.controller import CacheController

        for url in [self.url, self.url + "#sha256=ignored", "https://download.pytorch.org"]:
            expected = hashlib.sha224(CacheController.cache_url(url).encode()).hexdigest()
            self.assertEqual(cache_key(url), expected)
        self.cache_path().write_bytes(self.payload)
        with self.assertRaises(OSError):
            self.recover(min_free_bytes=10**20)
        self.resource["filename"] = "../escape.whl"
        with self.assertRaises(ValueError):
            self.recover()
        for url in ["http://files.pythonhosted.org/x", "https://example.com/x", "https://user:pass@files.pythonhosted.org/x"]:
            with self.assertRaises(ValueError):
                cache_key(url)


if __name__ == "__main__":
    unittest.main()
