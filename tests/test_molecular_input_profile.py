"""Pure profile/checkpoint metadata tests; original model tests run in Slurm."""

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest

from universal_gnn.backbones.official.molecular.profiles import configure_profile, graph_provenance, resolve_profile


class MolecularInputProfileTests(unittest.TestCase):
    def test_default_official_metadata_and_original_artifact_are_unchanged(self):
        for provider in ["cgcnn", "alignn"]:
            artifact = {"files": {"original": b"weights"}}
            before = copy.deepcopy(artifact)
            self.assertEqual(configure_profile(provider, artifact), dict(version=1, name="official"))
            self.assertEqual(artifact, before)
            self.assertEqual(configure_profile(provider, artifact, name="official"), dict(version=1, name="official"))

    def test_default_molecular_radius_has_all_neighbors_no_pbc_and_no_architecture_knob(self):
        profile = resolve_profile("cgcnn", {}, name="molecular_radius")
        self.assertEqual(profile, dict(version=1, name="molecular_radius", cutoff=6., all_neighbors=True, pbc="none"))
        self.assertEqual(resolve_profile("alignn", {}, name="molecular_radius", cutoff=4.25)["cutoff"], 4.25)
        self.assertNotIn("max_neighbors", profile)

    def test_unknown_profiles_providers_and_invalid_radius_fail(self):
        for name in ["radius", "legacy", {}, True, 1]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                resolve_profile("cgcnn", {}, name=name)
        for provider in ["mace", "nequip", "unknown"]:
            with self.assertRaises(ValueError):
                resolve_profile(provider, {}, name="molecular_radius")
        for radius in [0, -1, True, float("inf"), float("nan"), "6"]:
            with self.subTest(radius=radius), self.assertRaises(ValueError):
                resolve_profile("alignn", {}, name="molecular_radius", cutoff=radius)
        with self.assertRaisesRegex(ValueError, "requires"):
            resolve_profile("cgcnn", {}, cutoff=6.)

    def test_embedded_profile_roundtrip_and_explicit_change_rejection(self):
        artifact = {}
        expected = configure_profile("cgcnn", artifact, name="molecular_radius", cutoff=5.5)
        self.assertEqual(configure_profile("cgcnn", artifact), expected)
        self.assertEqual(configure_profile("cgcnn", artifact, name="molecular_radius"), expected)
        for options in [dict(name="official"), dict(name="molecular_radius", cutoff=6.)]:
            with self.assertRaisesRegex(ValueError, "differs"):
                configure_profile("cgcnn", copy.deepcopy(artifact), **options)

    def test_implementation_is_source_bound_with_platform_independent_line_endings(self):
        artifact = {}
        configure_profile("alignn", artifact, name="molecular_radius")
        implementation = artifact["input_profile_implementation"]
        self.assertEqual(implementation["version"], 1)
        self.assertEqual(implementation["source_line_endings"], "LF")
        self.assertEqual(len(implementation["source_sha256"]), 5)
        base = Path(__file__).resolve().parents[1] / "src/universal_gnn"
        for name, expected in implementation["source_sha256"].items():
            raw = (base / name).read_bytes()
            self.assertEqual(hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(), expected)
            self.assertEqual(hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n").replace(b"\r\n", b"\n")).hexdigest(), expected)
        tampered = copy.deepcopy(artifact)
        tampered["input_profile_implementation"]["source_sha256"][next(iter(implementation["source_sha256"]))] = "0" * 64
        with self.assertRaisesRegex(ValueError, "implementation differs"):
            configure_profile("alignn", tampered)

    def test_incomplete_embedded_metadata_is_not_silently_relabelled_official(self):
        artifact = {}
        configure_profile("cgcnn", artifact, name="molecular_radius")
        for name in ["input_profile", "input_profile_implementation"]:
            incomplete = copy.deepcopy(artifact)
            incomplete.pop(name)
            with self.assertRaisesRegex(ValueError, "together"):
                configure_profile("cgcnn", incomplete)

    def test_embedded_version_neighbor_pbc_and_cutoff_tampering_fail(self):
        artifact = {}
        configure_profile("alignn", artifact, name="molecular_radius")
        for key, value in [("version", 2), ("version", True), ("all_neighbors", False),
                           ("pbc", "periodic"), ("cutoff", True), ("cutoff", 0.), ("unexpected", 1)]:
            tampered = copy.deepcopy(artifact)
            tampered["input_profile"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                configure_profile("alignn", tampered)

    def test_graph_provenance_exposes_profile_without_mutating_checkpoint(self):
        class Backbone:
            pass
        backbone = Backbone()
        backbone.official_artifact = {}
        backbone.input_profile = configure_profile("cgcnn", backbone.official_artifact, name="molecular_radius")
        result = graph_provenance(backbone, {"original": "value"})
        self.assertEqual(result["input_profile"], backbone.input_profile)
        result["input_profile"]["cutoff"] = 100.
        self.assertEqual(backbone.input_profile["cutoff"], 6.)
        backbone.input_profile = dict(version=1, name="official")
        self.assertEqual(graph_provenance(backbone, {"original": "value"}), {"original": "value"})

    def test_metadata_import_requires_no_torch_numpy_or_original_packages(self):
        repository = Path(__file__).resolve().parents[1]
        environment = {**os.environ, "PYTHONPATH": str(repository / "src")}
        code = ("import sys; from universal_gnn.backbones.official.molecular.profiles import resolve_profile; "
                "assert resolve_profile('cgcnn',{},name='molecular_radius')['cutoff']==6.; "
                "assert not {'torch','numpy','cgcnn','alignn'} & sys.modules.keys()")
        subprocess.run([sys.executable, "-S", "-c", code], check=True, env=environment, capture_output=True)


if __name__ == "__main__":
    unittest.main()
