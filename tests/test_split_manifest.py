import copy
import hashlib
import json
import unittest

from universal_gnn.data.splits import create_manifest, validate_manifest


class SplitManifestTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"id": f"s{i}", "group": f"g{i // 2}"} for i in range(40)]
        self.digest = hashlib.sha256(b"dataset fixture").hexdigest()

    def make(self, **kwargs):
        return create_manifest(self.records, source_sha256=self.digest, **kwargs)

    def test_seed_and_order_independence_and_exact_coverage(self):
        manifest = self.make(seed=4)
        self.assertEqual(manifest, self.make(seed=4))
        self.assertNotEqual(manifest["partitions"], self.make(seed=5)["partitions"])
        reverse = create_manifest(list(reversed(self.records)), source_sha256=self.digest, seed=4)
        def role_ids(value):
            return {role: {value["records"][i]["id"] for i in indices}
                    for role, indices in value["partitions"].items()}
        self.assertEqual(role_ids(manifest), role_ids(reverse))
        self.assertEqual(manifest["counts"], {"train": 32, "validation": 4, "test": 4})
        self.assertEqual(sum(manifest["counts"].values()), 40)
        self.assertEqual(validate_manifest(json.loads(json.dumps(manifest)),
                                          source_sha256=self.digest, source_count=40), manifest)

    def test_official_splits_and_group_leakage(self):
        official = {r["id"]: "train" if i < 32 else "validation" if i < 36 else "test"
                    for i, r in enumerate(self.records)}
        manifest = self.make(official=official)
        self.assertEqual(manifest["partitions"]["test"], list(range(36, 40)))
        official["s0"] = "test"
        with self.assertRaisesRegex(ValueError, "leakage"):
            self.make(official=official)

    def test_corrupt_hash_count_indices_and_ids(self):
        baseline = self.make()
        changes = [lambda m: m.update(source_sha256="f" * 64),
                   lambda m: m.update(source_count=41),
                   lambda m: m["counts"].update(train=1),
                   lambda m: m["records"][1].update(id=m["records"][0]["id"]),
                   lambda m: m["partitions"]["test"].append(100),
                   lambda m: m["partitions"]["test"].append(m["partitions"]["train"][0]),
                   lambda m: m["partitions"]["train"].pop(),
                   lambda m: m["partitions"].update(test=[])]
        for change in changes:
            corrupted = copy.deepcopy(baseline)
            change(corrupted)
            with self.assertRaises(ValueError):
                validate_manifest(corrupted, source_sha256=self.digest, source_count=40)

    def test_bad_ratios_small_groups_and_incomplete_official(self):
        for ratios in [(1, 0, 0), (.8, .2, .1), (.8, float("nan"), .2)]:
            with self.assertRaises(ValueError):
                self.make(ratios=ratios)
        with self.assertRaises(ValueError):
            create_manifest(self.records[:4], source_sha256=self.digest)
        with self.assertRaises(ValueError):
            self.make(official={"s0": "train"})


if __name__ == "__main__":
    unittest.main()
