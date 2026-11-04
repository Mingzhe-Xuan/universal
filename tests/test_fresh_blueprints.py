"""Original-constructor argument policies; stdlib only, no numerical model execution."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest

from universal_gnn.backbones.blueprints import (mace_constructor_config, neighbor_normalization,
                                               nequip_constructor_config)


def statistics(provider, cutoff):
    return {"version": 1, "kind": "native_neighbor_counts_v1", "provider": provider,
            "partition": "train", "dtype": "float32", "cutoff": cutoff, "structures": 2,
            "declared_training_structures": 2, "atomic_nodes": 4, "active_receivers": 2,
            "directed_edges": 12, "source_sha256": "a"*64, "manifest_sha256": "b"*64,
            "training_fingerprint": "c"*64}


class ShapeOnly:
    def __init__(self, *shape): self.shape = shape
    def __getattr__(self, field): raise AssertionError("Read pretrained statistic values: " + field)


def blueprint():
    return {"data": {"_target_": "not_a_model_loader"}, "training_module": {"model": {
        "_target_": "nequip.model.modify", "modifiers": [{"modifier": "enable_OpenEquivariance"}],
        "model": {"_target_": "nequip.model.NequIPGNNModel", "r_max": 4.5, "type_names": ["H", "O"],
                  "seed": 42, "compile_mode": "compile", "l_max": 1, "parity": False, "num_layers": 2,
                  "num_features": [128, 64], "avg_num_neighbors": 25.59,
                  "per_type_energy_shifts": {"H": -1., "O": -5.}, "per_type_energy_scales": [2., 4.],
                  "per_type_energy_shifts_trainable": False, "per_type_energy_scales_trainable": True,
                  "pair_potential": {"_target_": "nequip.nn.pair_potential.ZBL", "units": "metal"}}}}}


class FreshBlueprintTests(unittest.TestCase):
    def test_nequip_neutral_statistics_preserve_scalar_and_per_type_shapes(self):
        for value, expected in ((5., 0.), ({"H": -3., "O": -5.}, {"H": 0., "O": 0.}),
                                ([2., 4.], [0., 0.]), ([2.], [0.])):
            data = blueprint();recipe = data["training_module"]["model"]["model"]
            recipe["per_type_energy_shifts"] = value
            config, _ = nequip_constructor_config(data, statistics("nequip", 4.5), seed=123)
            self.assertEqual(config["per_type_energy_shifts"], expected)
            self.assertEqual(recipe["per_type_energy_shifts"], value)
        for value in ({"H": -3.}, {"H": -3., "Ne": -5.}, [], [1., 2., 3.], True, None, "fit"):
            data = blueprint();data["training_module"]["model"]["model"]["per_type_energy_shifts"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "per-type energy statistic"):
                nequip_constructor_config(data, statistics("nequip", 4.5), seed=123)

    def test_native_normalizers_treat_zero_degree_nodes_differently(self):
        self.assertEqual(neighbor_normalization(statistics("mace", 6.), provider="mace", cutoff=6.), 6.)
        self.assertEqual(neighbor_normalization(statistics("nequip", 4.5), provider="nequip", cutoff=4.5), 3.)

    def test_normalization_rejects_missing_partial_holdout_wrong_radius_and_counts(self):
        for field, value in (("partition", "test"), ("declared_training_structures", 3), ("atomic_nodes", 1),
                             ("directed_edges", 0), ("active_receivers", 5), ("structures", True),
                             ("version", True), ("cutoff", 5.), ("training_fingerprint", "missing"),
                             ("provider", "nequip"), ("dtype", "float16")):
            sample = statistics("mace", 6.)
            sample[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                neighbor_normalization(sample, provider="mace", cutoff=6.)
        with self.assertRaises(ValueError):
            neighbor_normalization(None, provider="mace", cutoff=6.)

    def test_mace_replaces_only_fitted_statistics_using_shapes(self):
        extracted = {"r_max": 6., "num_elements": 2, "atomic_numbers": [1, 8], "hidden_irreps": "128x0e",
                     "correlation": 3, "avg_num_neighbors": 55., "atomic_energies": ShapeOnly(1, 2),
                     "atomic_inter_scale": ShapeOnly(1), "atomic_inter_shift": ShapeOnly(1)}
        result = mace_constructor_config(extracted, statistics("mace", 6.))
        self.assertEqual(result["atomic_energies"], [[0., 0.]])
        self.assertEqual(result["atomic_inter_scale"], [1.])
        self.assertEqual(result["atomic_inter_shift"], [0.])
        self.assertEqual(result["avg_num_neighbors"], 6.)
        for key in ("r_max", "num_elements", "atomic_numbers", "hidden_irreps", "correlation"):
            self.assertEqual(result[key], extracted[key])
        self.assertEqual(extracted["avg_num_neighbors"], 55.)
        self.assertIsInstance(extracted["atomic_energies"], ShapeOnly)
        with self.assertRaisesRegex(ValueError, "extraction failed"):
            mace_constructor_config({"error": "not original MACE"}, statistics("mace", 6.))

    def test_nequip_uses_architecture_only_resets_fit_and_overrides_source_seed(self):
        source = blueprint()
        before = copy.deepcopy(source)
        kwargs, report = nequip_constructor_config(source, statistics("nequip", 4.5), seed=7)
        self.assertEqual(source, before)
        self.assertEqual(kwargs["seed"], 7)
        self.assertEqual(kwargs["compile_mode"], "eager")
        self.assertEqual(kwargs["num_features"], [128, 64])
        self.assertEqual(kwargs["num_layers"], 2)
        self.assertEqual(kwargs["type_names"], ["H", "O"])
        self.assertEqual(kwargs["r_max"], 4.5)
        self.assertEqual(kwargs["avg_num_neighbors"], 3.)
        self.assertEqual(kwargs["per_type_energy_shifts"], {"H": 0., "O": 0.})
        self.assertEqual(kwargs["per_type_energy_scales"], [1., 1.])
        self.assertFalse(kwargs["per_type_energy_shifts_trainable"])
        self.assertTrue(kwargs["per_type_energy_scales_trainable"])
        self.assertEqual(kwargs["pair_potential"], before["training_module"]["model"]["model"]["pair_potential"])
        self.assertNotIn("data", kwargs)
        self.assertNotIn("_target_", kwargs)
        self.assertEqual(report["skipped_nonpersistent_modifiers_for_eager"], ["enable_OpenEquivariance"])

    def test_nequip_refuses_loader_recipe_persistent_modification_and_bad_seed(self):
        for target in ("nequip.model.ModelFromCheckpoint", "nequip.model.ModelFromPackage", None, {}):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "original NequIPGNNModel"):
                nequip_constructor_config({"_target_": target}, statistics("nequip", 4.5), seed=7)
        modified = blueprint()
        modified["training_module"]["model"]["modifiers"] = [{"modifier": "modify_PerTypeScaleShift"}]
        with self.assertRaisesRegex(ValueError, "persistent modifier"):
            nequip_constructor_config(modified, statistics("nequip", 4.5), seed=7)
        for seed in (True, -1, 2**64):
            with self.assertRaisesRegex(ValueError, "initialization seed"):
                nequip_constructor_config(blueprint(), statistics("nequip", 4.5), seed=seed)

    def test_public_blueprint_metadata_imports_without_torch_numpy_or_yaml(self):
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]/"src")}
        subprocess.run([sys.executable, "-S", "-c", "import sys; import universal_gnn.backbones.blueprints; "
                        "assert not {'torch','numpy','yaml'} & sys.modules.keys()"], env=environment, check=True, capture_output=True)


    def test_lazy_public_encoder_aliases_keep_the_provider_class_identity(self):
        environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]/"src")}
        code = """import sys, types
import universal_gnn.backbones as package
provider = types.ModuleType('universal_gnn.backbones.invariant')
for name in package.__all__:
    setattr(provider, name, type(name, (), {}))
sys.modules[provider.__name__] = provider
for name in package.__all__:
    assert getattr(package, name) is getattr(provider, name)
    assert getattr(package, name) is getattr(provider, name)
assert 'torch' not in sys.modules
"""
        subprocess.run([sys.executable, "-S", "-c", code], env=environment, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
