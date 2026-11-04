"""Provenance and complete-train checks without importing a GNN or scientific runtime."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from universal_gnn.backbones.blueprints import aggregate_native_neighbor_counts
from universal_gnn.engine.initialization.policy import training_identity, validate_bound_statistics


class NeighborBindingTests(unittest.TestCase):
    def kwargs(self):
        return dict(source_sha256="a" * 64, manifest_sha256="b" * 64,
                    training_fingerprint="c" * 64, dtype="float32")

    def identity(self):
        return training_identity(dict(split_manifest="split.json", partition="train"), [2, 0], [0, 2], **self.kwargs())

    def test_requires_complete_training_membership_and_fingerprints(self):
        self.assertEqual(self.identity(), {**self.kwargs(), "declared_training_structures": 2})
        settings = dict(split_manifest="split.json", partition="train")
        for selected in ([0], [0, 0], [0, 1], [0, 2, 3], [True, 2], [-1, 2]):
            with self.subTest(selected=selected), self.assertRaisesRegex(ValueError, "complete"):
                training_identity(settings, selected, [0, 2], **self.kwargs())
        for partition in (None, "validation", "test"):
            with self.subTest(partition=partition), self.assertRaisesRegex(ValueError, "training split"):
                training_identity({**settings, "partition": partition}, [0, 2], [0, 2], **self.kwargs())
        for field, value in (("source_sha256", "a"), ("manifest_sha256", None), ("dtype", "float16")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                training_identity(settings, [0, 2], [0, 2], **{**self.kwargs(), field: value})

    def test_cached_statistics_bind_data_precision_and_native_graph(self):
        identity = self.identity()
        graphs = {"artifact_sha256": {"model": "d" * 64}, "provider_version": "original"}
        statistics = aggregate_native_neighbor_counts(
            [dict(atomic_nodes=2, active_receivers=2, directed_edges=2)] * 2,
            provider="mace", cutoff=6., **identity)
        statistics["native_graph"] = graphs
        original = copy.deepcopy(statistics)
        self.assertEqual(validate_bound_statistics(statistics, identity, provider="mace", cutoff=6., native_graph=graphs), 1.)
        for field, value in (("source_sha256", "d" * 64), ("manifest_sha256", "e" * 64),
                             ("training_fingerprint", "f" * 64), ("dtype", "float64"),
                             ("declared_training_structures", 3)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_bound_statistics(statistics, {**identity, field: value}, provider="mace", cutoff=6., native_graph=graphs)
        for graph in ({}, {**graphs, "provider_version": "changed"}):
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                validate_bound_statistics(statistics, identity, provider="mace", cutoff=6., native_graph=graph)
        with self.assertRaises(ValueError):
            validate_bound_statistics(statistics, identity, provider="mace", cutoff=4., native_graph=graphs)
        self.assertEqual(statistics, original)

    def test_metadata_imports_and_cli_guard_precede_torch(self):
        root = Path(__file__).resolve().parents[1]
        environment = {**os.environ, "PYTHONPATH": str(root / "src")}
        environment.pop("SLURM_JOB_ID", None)
        imported = subprocess.run([sys.executable, "-S", "-c", "import sys; "
                                  "import universal_gnn.engine.initialization.policy; "
                                  "import universal_gnn.engine.initialization.neighbors; "
                                  "assert not {'torch','numpy','ase','pymatgen'} & sys.modules.keys()"],
                                 env=environment, capture_output=True, text=True)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        guarded = subprocess.run([sys.executable, "-S", str(root / "scripts/prepare_native_neighbors.py"),
                                  "--config", "does-not-exist.yaml", "--output", "does-not-exist.json"],
                                 env=environment, capture_output=True, text=True)
        self.assertEqual(guarded.returncode, 2)
        self.assertIn("must run through Slurm", guarded.stderr)
        self.assertNotIn("ModuleNotFoundError", guarded.stderr)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.json"
            output.write_text("unchanged")
            refused = subprocess.run([sys.executable, "-S", str(root / "scripts/prepare_native_neighbors.py"),
                                      "--config", "does-not-exist.yaml", "--output", str(output)],
                                     env={**environment, "SLURM_JOB_ID": "guard-fixture"}, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("Output already exists", refused.stderr)
            self.assertNotIn("ModuleNotFoundError", refused.stderr)
            self.assertEqual(output.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
