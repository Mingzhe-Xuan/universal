"""Pure metadata/config and three synthetic frame controls; no full data/model work."""

import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from test_arxiv_experiment_definitions import registry_fixture
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.execution.gates import case_spec
from universal_gnn.benchmarks.molecular import definitions as module
from universal_gnn.benchmarks.molecular import source
from universal_gnn.data.preparation.rmd17.conversion import KCAL_MOL_TO_EV, normalize_record
from universal_gnn.data.splits import create_manifest


ROOT = Path(__file__).resolve().parents[1]


def input_fixture():
    return dict(version=1, kind="arxiv_v1_complete_molecular_inputs", status="passed",
        dataset=dict(path=source.DATA_ROOT + "/structures.jsonl", sha256=source.SOURCE_SHA,
            split_manifest=source.DATA_ROOT + "/split.json", split_manifest_sha256="c" * 64),
        audit_sha256=source.AUDIT_SHA, split_file_sha256=source.SPLIT_FILE_SHA,
        counts=dict(source.COUNTS), structures=100000, source_sha256=source.SOURCE_SHA,
        atoms=900000, maximum_atoms=9, atomic_numbers_present=[1, 6, 8],
        energy_components=100000, force_components=2700000, excluded_records=0,
        official_test_cohort_count=1000, author_development_count=1000, training_rng_used_for_split=False,
        unit_conversion_factor=KCAL_MOL_TO_EV, units=dict(positions="angstrom", total_energy="eV", forces="eV/angstrom"))


class MolecularDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.primary = build_matrix(registry_fixture())
        self.inputs = input_fixture()

    def build(self, inputs=None):
        with patch.object(module, "PRIMARY_SHA", canonical_digest(self.primary)):
            return module.build_molecular_definitions(self.primary, inputs or self.inputs, repository=ROOT)

    def test_eight_original_pairs_and_one_plugin_are_separate_full_single_seed_cases(self):
        original, inputs = copy.deepcopy(self.primary), copy.deepcopy(self.inputs)
        result = self.build()
        self.assertEqual(self.primary, original)
        self.assertEqual(self.inputs, inputs)
        self.assertEqual((result["defined_training_runs"], result["official_training_runs"], result["plugin_training_runs"],
                          result["formal_training_runs"], result["training_seeds"]), (9, 8, 1, 0, [123]))
        self.assertEqual(len(result["pairs"]), 4)
        self.assertEqual(len({case["id"] for case in result["cases"]}), 9)
        for case in result["cases"]:
            config = case["config"]
            self.assertEqual(config["seed"], 123)
            self.assertEqual(config["dataset"]["split_manifest_sha256"], "c" * 64)
            self.assertNotEqual(config["dataset"]["split_manifest_sha256"], source.SPLIT_FILE_SHA)
            self.assertEqual(case["counts"], dict(train=900, validation=100, test=99000))
            self.assertEqual(case["source_structures"], 100000)
            self.assertEqual(case["evaluation_cohorts"], ["official_test_01"])
            self.assertEqual(config["structures"], "all")
            self.assertIsNone(config["max_atoms"])
            self.assertEqual((config["batch_size"], config["epochs"], config["dtype"]), (4, 300, "float32"))
            self.assertEqual(config["task"]["supervised_outputs"], ["total_energy", "forces"])
            self.assertEqual(config["evaluation"]["patience"], 30)
            self.assertEqual(case["config_sha256"], canonical_digest(config))
            self.assertEqual(case["status"], "defined_not_preflighted")
            self.assertIn("actual_cuda_capacity_100batches_and_mixed_extrema", case["required_gates"])
            if case["role"] == "official_molecular_transfer":
                expected = copy.deepcopy(case_spec(self.primary, "seed-123--forcefield--" + case["model"] + "--" + case["initialization"])["case"]["config"])
                expected["dataset"] = dict(self.inputs["dataset"], partition="train", bindings=expected["dataset"]["bindings"])
                if case["model"] in {"cgcnn", "alignn"}:
                    expected["backbone"].update(input_profile="molecular_radius", input_cutoff=6.)
                self.assertEqual(config, expected)
                self.assertTrue(case["pair_id"])
        self.assertEqual(len(self.primary["cases"]), 144)

    def test_plugin_selects_standard_contract_factories_and_records_original_code(self):
        case = self.build()["cases"][-1]
        self.assertEqual(case["role"], "directory_plugin_extension")
        self.assertEqual(case["initialization"], "scratch")
        self.assertIsNone(case["pair_id"])
        self.assertEqual(case["config"]["backbone"], dict(name="plugin:examples/custom_knn_gcn", implementation="legacy", width=16, layers=2, cutoff=6.))
        self.assertEqual(case["config"]["graph"], dict(name="plugin:examples/custom_knn_gcn", k=2))
        self.assertNotIn("initialization", case["config"]["backbone"])
        self.assertNotIn("original_weights_and_parameter_layout", case["required_gates"])
        self.assertNotIn("official_initialization_numerical", case["required_gates"])
        self.assertNotIn("original_prediction_equivalence", case["required_gates"])
        self.assertEqual(len(case["plugin"]["source_sha256"]), 3)
        for name, digest in case["plugin"]["source_sha256"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest())

    def test_wrong_primary_and_incomplete_or_reinterpreted_source_refused(self):
        with self.assertRaises(ValueError):
            module.build_molecular_definitions(self.primary, self.inputs, repository=ROOT)
        for key, value in [("version", True), ("counts", dict(train=100000, validation=0, test=0)),
                ("force_components", 270000), ("structures", 1000), ("excluded_records", 1),
                ("training_rng_used_for_split", True), ("official_test_cohort_count", 0),
                ("unit_conversion_factor", 1.), ("audit_sha256", "b" * 64), ("maximum_atoms", 8),
                ("units", dict(positions="angstrom", total_energy="kcal/mol", forces="kcal/mol/angstrom"))]:
            bad = copy.deepcopy(self.inputs);bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.build(bad)
        bad = copy.deepcopy(self.inputs);bad["dataset"]["split_manifest_sha256"] = "unknown"
        with self.assertRaises(ValueError): self.build(bad)

    def test_actual_export_has_nine_configs_and_refuses_existing_before_inspection(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"SLURM_JOB_ID": "metadata-only-unit"}), \
                patch.object(module, "PRIMARY_SHA", canonical_digest(self.primary)), \
                patch.object(module.shutil, "disk_usage", return_value=SimpleNamespace(free=100 * 1024**3)), \
                patch.object(module, "inspect_molecular_inputs", return_value=self.inputs) as inspect:
            output = Path(temporary) / "definitions"
            result = module.write_molecular_definitions(self.primary, output, repository=ROOT)
            inspect.assert_called_once_with(source.DATA_ROOT, source.RAW_ROOT)
            self.assertEqual(json.loads((output / "definitions.json").read_bytes()), result)
            self.assertEqual(len(list((output / "configs").glob("*.json"))), 9)
            for case in result["cases"]:
                self.assertEqual(json.loads((output / case["config_path"]).read_bytes()), case["config"])
            before = (output / "definitions.json").read_bytes()
            inspect.reset_mock()
            with self.assertRaises(FileExistsError): module.write_molecular_definitions(self.primary, output, repository=ROOT)
            inspect.assert_not_called()
            self.assertEqual((output / "definitions.json").read_bytes(), before)

    def test_complete_audit_and_export_without_slurm_refused_before_work(self):
        environment = {k: v for k, v in os.environ.items() if k != "SLURM_JOB_ID"}
        with patch.dict(os.environ, environment, clear=True), tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeError): source.inspect_molecular_inputs(temporary, temporary)
            with self.assertRaises(RuntimeError): module.write_molecular_definitions(self.primary, Path(temporary) / "new")
            self.assertFalse((Path(temporary) / "new").exists())

    def test_disk_reserve_refused_before_complete_source_inspection(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"SLURM_JOB_ID": "metadata-only-unit"}), \
                patch.object(module.shutil, "disk_usage", return_value=SimpleNamespace(free=19 * 1024**3)), \
                patch.object(module, "inspect_molecular_inputs") as inspect:
            with self.assertRaises(RuntimeError): module.write_molecular_definitions(self.primary, Path(temporary) / "new")
            inspect.assert_not_called()
            self.assertFalse((Path(temporary) / "new").exists())

    def test_cli_without_slurm_refused_before_reading_matrix_or_dataset(self):
        main = runpy.run_path(str(ROOT / "scripts/prepare_molecular_experiment_definitions.py"))["main"]
        environment = {k: v for k, v in os.environ.items() if k != "SLURM_JOB_ID"}
        with patch.dict(os.environ, environment, clear=True), patch("sys.argv", ["prepare", "--output", "missing-definition-dir"]):
            with self.assertRaises(SystemExit) as caught: main()
            self.assertEqual(caught.exception.code, 2)

    def test_import_requires_no_numerical_runtime(self):
        code = "import sys;sys.path.insert(0,'src');import universal_gnn.benchmarks.molecular.definitions;assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable, "-S", "-c", code], cwd=ROOT, check=True)


class MolecularSourceRecordTests(unittest.TestCase):
    def setUp(self):
        self.rows = [normalize_record(i, numbers=[6, 6, 8, 1, 1, 1, 1, 1, 1],
            positions=[[float(j), float(i), j / 7] for j in range(9)], energy=-1000. + i,
            forces=[[0. if i == 0 else .2, 0., 0.] for _ in range(9)], old_index=100 + i) for i in range(3)]

    def scan(self, rows, *, manifest_rows=None, expected_count=3, expected_sha=None):
        raw = b"".join((json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=True) + "\n").encode() for row in rows)
        digest = hashlib.sha256(raw).hexdigest()
        records = manifest_rows or [dict(id=row["id"], group=row["metadata"]["geometry_sha256"]) for row in self.rows]
        manifest = create_manifest(records, source_sha256=expected_sha or digest, seed=0,
            official={r["id"]: role for r, role in zip(records, ("train", "validation", "test"))})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "structures.jsonl";path.write_bytes(raw)
            return source._inspect_records(path, manifest, source_sha256=expected_sha or digest, source_count=expected_count)

    def test_complete_source_counts_raw_units_geometry_groups_and_zero_labels(self):
        result, records = self.scan(self.rows)
        self.assertEqual((result["structures"], result["atoms"], result["energy_components"], result["force_components"]), (3, 27, 3, 81))
        self.assertEqual(result["whole_zero_force_records"], 1)
        self.assertEqual(result["excluded_records"], 0)
        self.assertEqual(result["atomic_numbers_present"], [1, 6, 8])
        self.assertEqual(records, [dict(id=r["id"], group=r["metadata"]["geometry_sha256"]) for r in self.rows])

    def test_forged_or_nonfinite_geometry_targets_metadata_and_periodicity_refused(self):
        mutations = [lambda r: r.update(schema_version=True), lambda r: r.update(id="wrong-source-id"),
            lambda r: r.update(numbers=[True] * 9), lambda r: r.update(pbc=[True, False, False]),
            lambda r: r.update(pbc=[0, 0, 0]), lambda r: r["positions"][0].__setitem__(0, float("nan")),
            lambda r: r["cell"][0].__setitem__(0, 2.), lambda r: r["targets"].update(energy=True),
            lambda r: r["targets"].update(forces=[[0., 0., 0.]]), lambda r: r["targets"].update(stress=[]),
            lambda r: r.update(metadata="wrong"), lambda r: r["metadata"].update(source_index=0),
            lambda r: r["metadata"].update(old_index=100), lambda r: r["metadata"].update(geometry_sha256="a" * 64),
            lambda r: r["metadata"].update(label_field="old labels"),
            lambda r: r["metadata"].update(archive_sha256="b" * 64)]
        for i, mutation in enumerate(mutations):
            rows = copy.deepcopy(self.rows);mutation(rows[1])
            with self.subTest(mutation=i), self.assertRaises(ValueError): self.scan(rows)

    def test_truncation_unregistered_byte_hash_and_unlabelled_extra_frames_refused(self):
        with self.assertRaises(ValueError): self.scan(self.rows[:-1])
        with self.assertRaises(ValueError): self.scan(self.rows, expected_sha="d" * 64)
        with self.assertRaises(ValueError): self.scan(self.rows + [copy.deepcopy(self.rows[-1])])


if __name__ == "__main__":
    unittest.main()
