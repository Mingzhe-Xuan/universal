"""Count aggregation policy; no scientific runtime or actual graph construction."""

import copy
import unittest

from universal_gnn.backbones.blueprints import aggregate_native_neighbor_counts, neighbor_normalization


class NativeNeighborCountTests(unittest.TestCase):
    def settings(self, provider="mace"):
        return dict(provider=provider, cutoff=4.5, dtype="float32", source_sha256="a" * 64,
                    manifest_sha256="b" * 64, training_fingerprint="c" * 64, declared_training_structures=3)

    def counts(self):
        return [dict(atomic_nodes=4, active_receivers=3, directed_edges=6),
                dict(atomic_nodes=2, active_receivers=2, directed_edges=2),
                dict(atomic_nodes=1, active_receivers=0, directed_edges=0)]

    def test_original_normalization_rules_include_isolated_structure(self):
        for provider, expected in (("mace", 8 / 5), ("nequip", 8 / 7)):
            with self.subTest(provider=provider):
                counts = self.counts()
                original = copy.deepcopy(counts)
                result = aggregate_native_neighbor_counts(iter(counts), **self.settings(provider))
                self.assertEqual(result["structures"], 3)
                self.assertEqual(result["atomic_nodes"], 7)
                self.assertEqual(result["active_receivers"], 5)
                self.assertEqual(result["directed_edges"], 8)
                self.assertEqual(neighbor_normalization(result, provider=provider, cutoff=4.5), expected)
                self.assertEqual(result, aggregate_native_neighbor_counts(reversed(counts), **self.settings(provider)))
                self.assertEqual(counts, original)

    def test_complete_coverage_and_provenance_are_required(self):
        for counts in (self.counts()[:2], self.counts() * 2, []):
            with self.subTest(count=len(counts)), self.assertRaises(ValueError):
                aggregate_native_neighbor_counts(counts, **self.settings())
        for setting, value in (("declared_training_structures", True), ("declared_training_structures", 0),
                               ("source_sha256", "bad"), ("dtype", "float16"), ("provider", "cgcnn")):
            with self.subTest(setting=setting), self.assertRaises(ValueError):
                aggregate_native_neighbor_counts(self.counts(), **{**self.settings(), setting: value})

    def test_per_structure_inconsistency_cannot_hide_in_valid_totals(self):
        bad = [dict(atomic_nodes=0, active_receivers=0, directed_edges=0),
               dict(atomic_nodes=1, active_receivers=2, directed_edges=2),
               dict(atomic_nodes=2, active_receivers=-1, directed_edges=2),
               dict(atomic_nodes=2, active_receivers=0, directed_edges=2),
               dict(atomic_nodes=2, active_receivers=2, directed_edges=1),
               dict(atomic_nodes=2, active_receivers=1, directed_edges=-1),
               dict(atomic_nodes=True, active_receivers=1, directed_edges=1), {}]
        for count in bad:
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "per-structure"):
                aggregate_native_neighbor_counts([count, *self.counts()[1:]], **self.settings())
        isolated = [dict(atomic_nodes=1, active_receivers=0, directed_edges=0)] * 3
        with self.assertRaises(ValueError):
            aggregate_native_neighbor_counts(isolated, **self.settings())


if __name__ == "__main__":
    unittest.main()
