"""Whole-matrix definitions and immutable input fixtures; no numerical/model execution."""

from collections import Counter
import copy
import hashlib
import json
import runpy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from universal_gnn.benchmarks.experiments.registry import DATASETS, MODELS, NEQUIP_ARCHITECTURE, PROFILES, canonical_digest, inspect_dataset
from universal_gnn.benchmarks.experiments.recipes import TASKS, build_matrix, write_matrix
from universal_gnn.data.splits import create_manifest
from universal_gnn.properties import property_spec


def registry_fixture():
    datasets, artifacts = {}, {}
    for name, (sha, counts) in DATASETS.items():
        datasets[name] = dict(path=f"data/arxiv-v1/{name}/structures.jsonl", sha256=sha,
                              split_manifest=f"data/arxiv-v1/{name}/split.json", split_manifest_sha256="a" * 64,
                              structures=sum(counts), split_counts=dict(zip(("train", "validation", "test"), counts)))
    for model in MODELS:
        files = dict(PROFILES[model]["files"])
        if model == "nequip": files[NEQUIP_ARCHITECTURE[0]] = NEQUIP_ARCHITECTURE[1]
        artifacts[model] = dict(source=PROFILES[model]["source"], files={name:dict(sha256=sha, bytes=1) for name,sha in files.items()})
    return dict(version=1, kind="arxiv_v1_full_inputs", datasets=datasets, artifacts=artifacts)


class ArxivDefinitionTests(unittest.TestCase):
    def test_complete_144_cartesian_product_and_full_input_protocol(self):
        source = registry_fixture();original = copy.deepcopy(source)
        matrix = build_matrix(source)
        self.assertEqual(matrix["expected_training_runs"], len(matrix["cases"]))
        self.assertEqual(len(matrix["cases"]), 144)
        self.assertEqual(len(matrix["pairs"]), 72)
        self.assertEqual(len({case["id"] for case in matrix["cases"]}), 144)
        self.assertEqual(Counter(case["seed"] for case in matrix["cases"]), {123:48,456:48,789:48})
        self.assertEqual(Counter(case["task"] for case in matrix["cases"]), {task:24 for task in TASKS})
        self.assertEqual(matrix["completed_training_runs"], 0)
        self.assertEqual(matrix["status"], "prepared_not_launched")
        for case in matrix["cases"]:
            config = case["config"]
            self.assertEqual(config["structures"], "all")
            self.assertEqual(config["device"], "cuda")
            self.assertEqual(config["dtype"], "float32")
            self.assertIsNone(config["max_atoms"])
            self.assertNotIn("graph", config)
            self.assertEqual(set(config["backbone"]), {"name","implementation","initialization"})
            self.assertEqual(config["backbone"]["implementation"], "official")
            self.assertEqual(config["dataset"]["partition"], "train")
            self.assertEqual(len(config["dataset"]["sha256"]), 64)
            self.assertEqual(len(config["dataset"]["split_manifest_sha256"]), 64)
            self.assertEqual(case["config_sha256"], canonical_digest(config))
            self.assertIn("paired_cuda_capacity", case["required_gates"])
            self.assertIn("whole_backbone_update", case["required_gates"])
            self.assertEqual(config["evaluation"], dict(patience=30, min_delta=0.))
            if case["task"] == "generation":
                self.assertNotIn("prediction", config);self.assertNotIn("optimization", config)
                self.assertNotIn("volume_per_atom", config["task"]["sampling"])
                self.assertEqual(config["generation_corruption"], "per_epoch_structure_v2")
                self.assertEqual(case["generation_quality"]["samples"], 1000)
            else:
                self.assertEqual(config["prediction"]["head_mode"], "reset")
                self.assertTrue(config["optimization"]["train_backbone"])
                self.assertTrue(config["optimization"]["train_readout"])
                if case["task"] == "forcefield":
                    self.assertEqual(config["task"]["supervised_outputs"], ["total_energy","forces"])
                    self.assertEqual(config["prediction"]["readout"]["pooling"], "sum")
                    self.assertNotIn("stress", config["dataset"]["bindings"])
                else:
                    spec = property_spec(case["task"], channels=config["task"].get("channels"))
                    self.assertEqual(config["dataset"]["bindings"][case["task"]]["unit"], spec.unit)
        self.assertEqual(source, original)

    def test_forcefield_definitions_satisfy_the_actual_runtime_supervision_contract(self):
        contract = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'src/universal_gnn/tasks/supervision.py'))
        matrix = build_matrix(registry_fixture())
        self.assertEqual(matrix['definition_revision'], 2)
        cases = [case for case in matrix['cases'] if case['task'] == 'forcefield']
        self.assertEqual(len(cases), 24)
        for case in cases:
            config = case['config']
            outputs = contract['supervised_outputs'](config)
            self.assertEqual(outputs, ('total_energy', 'forces'))
            self.assertEqual(set(config['task']['loss_weights']), set(outputs))
            self.assertEqual(set(config['dataset']['bindings']), set(outputs))
            self.assertEqual(config['dataset']['bindings']['total_energy'], dict(key='energy', unit='eV'))
        with self.assertRaises(ValueError):
            contract['supervised_outputs']({'task': {'kind':'forcefield', 'supervised_outputs':['energy','forces']}})
    def test_pairs_share_every_task_setting_except_whole_backbone_initialization(self):
        matrix = build_matrix(registry_fixture())
        cases = {case["id"]:case for case in matrix["cases"]}
        for pair in matrix["pairs"]:
            first, second = [copy.deepcopy(cases[name]["config"]) for name in pair["cases"]]
            self.assertEqual({first["backbone"].pop("initialization"), second["backbone"].pop("initialization")}, {"pretrained","scratch"})
            self.assertEqual(first, second)
        same_gap = [case["config"]["dataset"] for case in matrix["cases"] if case["task"] in ("classification","bandgap")]
        self.assertEqual(len({row["sha256"] for row in same_gap}), 1)
        self.assertEqual(len({row["split_manifest_sha256"] for row in same_gap}), 1)

    def test_partial_corrupt_registry_and_invalid_budget_cannot_be_prepared(self):
        for mutation in ("missing_dataset","source","manifest","counts","artifact","boolean_version"):
            source = registry_fixture()
            if mutation == "missing_dataset":source["datasets"].pop("perov5")
            elif mutation == "source":source["datasets"]["jarvis-gap"]["sha256"] = "f" * 64
            elif mutation == "manifest":source["datasets"]["jarvis-gap"]["split_manifest_sha256"] = "bad"
            elif mutation == "counts":source["datasets"]["jarvis-gap"]["split_counts"]["train"] = 10
            elif mutation == "boolean_version":source["version"] = True
            else:source["artifacts"]["mace"]["files"]["mace/small.model"]["sha256"] = "f" * 64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):build_matrix(source)
        for options in (dict(seeds=[1,1]),dict(seeds=[True]),dict(epochs=0),dict(learning_rate=float('nan')),dict(patience=0)):
            with self.subTest(options=options), self.assertRaises(ValueError):build_matrix(registry_fixture(), **options)

    def test_outputs_are_complete_and_existing_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            matrix = build_matrix(registry_fixture())
            output = Path(directory)/"definitions"
            path = write_matrix(matrix, output)
            self.assertEqual(len(list((output/"configs").glob('*.json'))), 144)
            self.assertEqual(json.loads(path.read_text())["expected_training_runs"], 144)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(FileExistsError):write_matrix(matrix, output)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            tampered = copy.deepcopy(matrix)
            tampered["cases"][0]["config"]["structures"] = 10
            with self.assertRaisesRegex(ValueError, "recorded digest"):
                write_matrix(tampered, Path(directory)/"tampered")
            self.assertFalse((Path(directory)/"tampered").exists())

    def test_actual_tiny_source_and_manifest_are_checked_without_loading_structures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);path = root/"data/arxiv-v1/fixture";path.mkdir(parents=True)
            source = path/"structures.jsonl"
            source.write_bytes(b'{"id":"a"}\n{"id":"b"}\n{"id":"c"}\n')
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest = create_manifest([dict(id=name,group=name) for name in ('a','b','c')], source_sha256=sha,
                                       official=dict(a="train",b="validation",c="test"))
            split = path/"split.json";split.write_text(json.dumps(manifest))
            audit = dict(dataset_sha256=sha,split_counts=manifest["counts"],counts=dict(written_records=3),maximum_atoms=1)
            (path/"audit.json").write_text(json.dumps(audit))
            checked = inspect_dataset(root,"fixture",(sha,(1,1,1)))
            self.assertEqual(checked["split_manifest_sha256"], canonical_digest(manifest))
            changed = copy.deepcopy(manifest);changed["records"][0]["id"] = "other"
            split.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,"IDs/order"):inspect_dataset(root,"fixture",(sha,(1,1,1)))
            split.write_text(json.dumps(manifest));source.write_bytes(source.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,"bytes/count"):inspect_dataset(root,"fixture",(sha,(1,1,1)))

    def test_metadata_and_cli_guard_require_no_torch(self):
        root = Path(__file__).resolve().parents[1]
        environment={**os.environ,"PYTHONPATH":str(root/"src")};environment.pop("SLURM_JOB_ID",None)
        imported=subprocess.run([sys.executable,"-S","-c","import sys; import universal_gnn.benchmarks.experiments.recipes; assert 'torch' not in sys.modules"],
                                env=environment,capture_output=True,text=True)
        self.assertEqual(imported.returncode,0,imported.stderr)
        guarded=subprocess.run([sys.executable,"-S",str(root/"scripts/prepare_arxiv_matrix.py"),"--output","not-created"],
                               env=environment,capture_output=True,text=True)
        self.assertEqual(guarded.returncode,2)
        self.assertIn("must run through Slurm",guarded.stderr)


if __name__ == "__main__":
    unittest.main()
