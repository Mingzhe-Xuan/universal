import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.generative.protocol import (condition_indices, corruption_seed,
    fit_volume_prior, require_corruption_compatible, wasserstein_1d)


def cube(edge):
    return {"numbers": [14], "cell": [[edge, 0., 0.], [0., edge, 0.], [0., 0., edge]]}


class GenerationProtocolTests(unittest.TestCase):
    def test_resume_inherits_only_derived_defaults_and_rejects_changed_sampling(self):
        from universal_gnn.engine.generative.protocol import generation_resume_config
        import copy

        config = {"task": {"sampling": {"steps": 50, "inner_steps": 2}}}
        saved = copy.deepcopy(config)
        saved["task"]["sampling"]["volume_per_atom"] = 14.
        saved["generation_prior"] = {"sampling_volume_source": "train_fit", "statistics": {"volume_per_atom": 14.}}
        original = copy.deepcopy(config)
        self.assertEqual(generation_resume_config(config, saved), saved)
        self.assertEqual(config, original)
        for key, value in (("steps", 2), ("inner_steps", 1), ("volume_per_atom", 15.), ("seed", 999)):
            changed = copy.deepcopy(config);changed["task"]["sampling"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "same declared generation sampling"):
                generation_resume_config(changed, saved)
        explicit = copy.deepcopy(saved);explicit["generation_prior"] = {"explicit": "retain for subsequent verification"}
        self.assertEqual(generation_resume_config(explicit, saved), explicit)
    def test_fresh_epoch_noise_is_reproducible_and_independent_of_minibatch_order(self):
        config = {"seed": 42}
        first = corruption_seed(config, "material-A", 0, epoch=0)
        self.assertEqual(first, corruption_seed(config, "material-A", 85, epoch=0))
        self.assertNotEqual(first, corruption_seed(config, "material-A", 0, epoch=1))
        self.assertNotEqual(first, corruption_seed(config, "material-B", 0, epoch=0))
        self.assertNotEqual(first, corruption_seed({"seed": 43}, "material-A", 0, epoch=0))
        self.assertTrue(0 <= first < 2**63)

    def test_validation_test_and_draws_are_separate_fixed_noise_streams(self):
        values = [corruption_seed({}, "same-id", 0, phase=phase, draw=draw)
                  for phase in ("train_evaluation", "validation", "test") for draw in range(3)]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(values[0], corruption_seed({}, "same-id", 11))
        self.assertEqual(values[3], corruption_seed({}, "same-id", 2, phase="validation"))
        for settings in ({"epoch": -1}, {"epoch": 0, "phase": "validation"}, {"draw": True}, {"phase": "invalid"}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                corruption_seed({}, "same-id", 0, **settings)

    def test_legacy_objective_preserved_and_resume_does_not_silently_switch(self):
        legacy = {"seed": 42, "generation_corruption": "per_structure_v1"}
        self.assertEqual(corruption_seed(legacy, "x", 5, epoch=0), 48)
        self.assertEqual(corruption_seed(legacy, "x", 5, epoch=12), 48)
        self.assertEqual(require_corruption_compatible(legacy, legacy, full_resume=True), "per_structure_v1")
        with self.assertRaisesRegex(ValueError, "same generation corruption"):
            require_corruption_compatible(legacy, {}, full_resume=True)
        with self.assertRaisesRegex(ValueError, "Unversioned"):
            require_corruption_compatible({}, {}, full_resume=True)
        self.assertEqual(require_corruption_compatible(legacy, {}, full_resume=False), "per_epoch_structure_v2")
        with self.assertRaisesRegex(ValueError, "Unknown"):
            corruption_seed({"generation_corruption": "typo"}, "x", 0)

    def test_prior_is_geometric_mean_per_atom_with_log_population_spread(self):
        prior = fit_volume_prior(iter([cube(2.), cube(4.)]), training_fingerprint="a" * 64)
        self.assertAlmostEqual(prior["volume_per_atom"], math.sqrt(8. * 64.))
        self.assertAlmostEqual(prior["log_volume_per_atom_std"], math.log(8.) / 2)
        self.assertEqual(prior["structures"], 2)
        self.assertEqual(prior["fitted_partition"], "train")
        value = cube(4.)
        value["numbers"] = [14, 14]
        self.assertAlmostEqual(fit_volume_prior([value], training_fingerprint="b"*64)["volume_per_atom"], 32.)
        value["cell"][0][0] *= -1
        self.assertAlmostEqual(fit_volume_prior([value], training_fingerprint="b"*64)["volume_per_atom"], 32.)

    def test_prior_never_silently_skips_invalid_training_geometry(self):
        for value in (cube(0.), cube(float("nan")), {"numbers": [], "cell": cube(2.)["cell"]},
                      {"numbers": [True], "cell": cube(2.)["cell"]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                fit_volume_prior([value], training_fingerprint="a"*64)
        with self.assertRaisesRegex(ValueError, "nonempty"):
            fit_volume_prior([], training_fingerprint="a"*64)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            fit_volume_prior([cube(2.)], training_fingerprint="missing")

    def test_fixed_conditions_have_no_replacement_and_are_stable_across_order(self):
        identifiers = [f"id-{i}" for i in range(20)]
        first = condition_indices(identifiers, count=10, seed=7)
        reverse = list(reversed(identifiers))
        again = condition_indices(reverse, count=10, seed=7)
        self.assertEqual([identifiers[i] for i in first], [reverse[i] for i in again])
        self.assertEqual(len(set(first)), 10)
        self.assertNotEqual(first, condition_indices(identifiers, count=10, seed=8))
        for ids, count in ((identifiers, 21), (identifiers, 0), (["a", "a"], 1), ([""], 1)):
            with self.assertRaises(ValueError):
                condition_indices(ids, count=count, seed=7)

    def test_wasserstein_handles_unequal_sizes_repeated_values_and_units(self):
        self.assertEqual(wasserstein_1d([0.], [2.]), 2.)
        self.assertEqual(wasserstein_1d([0., 2.], [1.]), 1.)
        self.assertAlmostEqual(wasserstein_1d([0., 0., 4.], [0., 2.]), 1.)
        self.assertEqual(wasserstein_1d([2., 1., 1.], [1., 2., 1.]), 0.)
        for left, right in (([], [1.]), ([True], [1.]), ([float("inf")], [1.])):
            with self.assertRaises(ValueError):
                wasserstein_1d(left, right)

    def test_prior_script_uses_complete_train_only_and_binds_actual_identity(self):
        spec = importlib.util.spec_from_file_location("generation_prior_fixture", Path(__file__).resolve().parents[1] / "scripts/prepare_generation_prior.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            records = [{"id": f"id-{i}", **cube(2. if i < 12 else 1000.)} for i in range(16)]
            roles = {row["id"]: "train" if i < 12 else "validation" if i < 14 else "test" for i, row in enumerate(records)}
            def files():
                source = root / "structures.jsonl"
                source.write_text("".join(json.dumps(row) + "\n" for row in records))
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                manifest = create_manifest([{"id": row["id"], "group": row["id"]} for row in records], source_sha256=digest, official=roles)
                path = root / "split.json"
                path.write_text(json.dumps(manifest))
                return source, path
            source, manifest = files()
            result = module.prepare_prior(source, manifest, root / "prior.json")
            self.assertEqual(result["prior"]["structures"], 12)
            self.assertAlmostEqual(result["prior"]["volume_per_atom"], 8.)
            self.assertEqual(result["heldout_structures_used_for_fit"], 0)
            for row in records[12:]:
                row["cell"] = cube(10000.)["cell"]
            source, manifest = files()
            again = module.prepare_prior(source, manifest, root / "again.json")
            self.assertEqual(result["prior"]["volume_per_atom"], again["prior"]["volume_per_atom"])
            self.assertNotEqual(result["prior"]["training_fingerprint"], again["prior"]["training_fingerprint"])
            with self.assertRaises(FileExistsError):
                module.prepare_prior(source, manifest, root / "again.json")
            changed = json.loads(manifest.read_text())
            changed["records"][0]["id"] = "wrong-source-id"
            manifest.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "identity/order"):
                module.prepare_prior(source, manifest, root / "bad.json")
            self.assertFalse((root / "bad.json").exists())

    def test_protocol_has_no_site_dependencies_and_cli_rejects_non_slurm(self):
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        environment.pop("SLURM_JOB_ID", None)
        code = "import sys; from universal_gnn.engine.generative.protocol import corruption_seed; print(corruption_seed({},'id',0,epoch=2)); assert not {'torch','numpy','ase'} & sys.modules.keys()"
        outputs = []
        for hash_seed in ("1", "17"):
            value = subprocess.run([sys.executable, "-S", "-c", code], env={**environment, "PYTHONHASHSEED": hash_seed}, text=True, capture_output=True, check=True)
            outputs.append(value.stdout)
        self.assertEqual(outputs[0], outputs[1])
        value = subprocess.run([sys.executable, "-S", "scripts/prepare_generation_prior.py", "none.jsonl", "none.json", "--output", "none-prior.json"], env=environment, text=True, capture_output=True)
        self.assertNotEqual(value.returncode, 0)
        self.assertIn("must run through Slurm", value.stderr)


if __name__ == "__main__":
    unittest.main()
