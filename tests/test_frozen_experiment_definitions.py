"""Pure frozen protocol fixtures; never evidence of actual frozen model training."""
import copy
from contextlib import ExitStack, contextmanager, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.frozen_backbones import definitions as module
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments import recipes
from universal_gnn.benchmarks.experiments.registry import canonical_digest, inspect_dataset
from universal_gnn.benchmarks.execution.gates import case_spec, file_sha
from universal_gnn.data.splits import create_manifest

registry_fixture = runpy.run_path(str(Path(__file__).with_name("test_arxiv_experiment_definitions.py")))["registry_fixture"]


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, allow_nan=False).encode())


@contextmanager
def sources():
    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
        root = Path(folder); previous = Path.cwd(); os.chdir(root); stack.callback(os.chdir, previous)
        registry = registry_fixture(); datasets = {}; paths = {}
        for task, name in (("dielectric", "gmtnet-dielectric"), ("forcefield", "mlearn-forcefield")):
            directory = Path("data/arxiv-v1") / name; directory.mkdir(parents=True)
            rows = []
            for i in range(3):
                targets = (dict(dielectric=[[0., 0., 0.], [0., 0. if i == 0 else 1 / 3, 0.], [0., 0., 0.]]) if task == "dielectric" else
                           dict(energy=0. if i == 0 else i + .125, forces=[[0., .125 * i, 0.], [0., 0., 0.]]))
                rows.append(dict(id=task + str(i), numbers=[14, 14], targets=targets))
            path = directory / "structures.jsonl"
            path.write_bytes(b"".join((json.dumps(row) + "\n").encode() for row in rows))
            sha = file_sha(path)
            manifest = create_manifest([dict(id=row["id"], group=row["id"]) for row in rows], source_sha256=sha, official={row["id"]: role for row, role in
                zip(rows, ("train", "validation", "test"))})
            write(directory / "split.json", manifest)
            write(directory / "audit.json", dict(dataset_sha256=sha, split_counts=manifest["counts"], counts=dict(written_records=3), maximum_atoms=2))
            datasets[name] = (sha, (1, 1, 1))
            registry["datasets"][name] = inspect_dataset(root, name, datasets[name]); paths[task] = path
        stack.enter_context(patch.dict(recipes.DATASETS, datasets))
        primary = build_matrix(registry)
        stack.enter_context(patch.object(module, "PRIMARY_SHA", canonical_digest(primary)))
        stack.enter_context(patch.object(module, "DATASETS", datasets))
        yield root, primary, paths


class FrozenExperimentDefinitions(unittest.TestCase):
    def test_eight_exact_original_pretrained_recipes_only_freeze_backbone(self):
        primary = build_matrix(registry_fixture()); before = copy.deepcopy(primary)
        with patch.object(module, "PRIMARY_SHA", canonical_digest(primary)):
            result = module.build_frozen_definitions(primary)
        self.assertEqual(primary, before)
        self.assertEqual((result["defined_training_runs"], result["formal_training_runs"], result["training_seeds"]), (8, 0, [123]))
        self.assertEqual(len({case["id"] for case in result["cases"]}), 8)
        for case in result["cases"]:
            original = case_spec(primary, case["reference_finetune_case"])["case"]
            expected = copy.deepcopy(original["config"]); expected["optimization"]["train_backbone"] = False
            self.assertEqual(case["config"], expected)
            self.assertEqual(case["config_sha256"], canonical_digest(expected))
            self.assertTrue(case["config"]["optimization"]["train_readout"])
            self.assertEqual(case["initialization"], "pretrained")
            self.assertEqual(case["config"]["epochs"], 300)
            self.assertEqual(case["config"]["evaluation"], dict(patience=30, min_delta=0.))
            self.assertTrue(case["run_directory"].startswith("runs/arxiv-v1/frozen-cases/"))
            self.assertEqual(case["status"], "defined_not_preflighted")
            self.assertTrue(case["reference_scratch_case"].endswith("--scratch"))

    def test_wrong_primary_and_mutated_original_recipe_are_refused(self):
        primary = build_matrix(registry_fixture())
        with self.assertRaises(ValueError): module.build_frozen_definitions(primary)
        target = next(c for c in primary["cases"] if c["id"] == "seed-123--dielectric--mace--pretrained")
        target["config"]["optimization"]["train_readout"] = False
        target["config_sha256"] = canonical_digest(target["config"])
        with patch.object(module, "PRIMARY_SHA", canonical_digest(primary)), self.assertRaises(ValueError):
            module.build_frozen_definitions(primary)

    def test_complete_source_keeps_zero_labels_and_all_force_components(self):
        with sources() as (root, primary, paths):
            result = module.inspect_frozen_inputs(primary)
            self.assertEqual(result["dielectric"]["finite_raw_components"], dict(dielectric=27))
            self.assertEqual(result["forcefield"]["finite_raw_components"], dict(total_energy=3, forces=18))
            for task in module.TASKS:
                self.assertEqual(result[task]["structures"], 3)
                self.assertEqual(result[task]["filtered_structures"], 0)
                self.assertEqual(result[task]["maximum_atoms"], 2)
                self.assertEqual(result[task]["atoms"], 6)
                self.assertEqual(result[task]["whole_zero_labels"], {key: 1 for key in result[task]["finite_raw_components"]})

    def test_changed_source_split_or_original_audit_is_refused(self):
        for change in ("source", "split", "audit"):
            with self.subTest(change=change), sources() as (root, primary, paths):
                path = paths["dielectric"]
                if change == "source": path.write_bytes(path.read_bytes() + b"\n")
                else: write(path.parent / ("split.json" if change == "split" else "audit.json"), {})
                with self.assertRaises((ValueError, KeyError)): module.inspect_frozen_inputs(primary)

    def test_raw_shapes_finite_atoms_and_label_keys_cannot_be_bypassed_by_repinning_fixture_source(self):
        for change in ("shape", "nan", "atoms", "missing"):
            with self.subTest(change=change), sources() as (root, primary, paths):
                path = paths["forcefield"]; rows = [json.loads(line) for line in path.read_bytes().splitlines()]
                if change == "shape": rows[0]["targets"]["forces"] = [[0., 0., 0.]]
                elif change == "nan": rows[0]["targets"]["energy"] = float("nan")
                elif change == "atoms": rows[0]["numbers"] = [True, 14]
                else: rows[0]["targets"].pop("energy")
                path.write_bytes(b"".join((json.dumps(row) + "\n").encode() for row in rows)); sha = file_sha(path)
                manifest = create_manifest([dict(id=row["id"], group=row["id"]) for row in rows], source_sha256=sha, official={row["id"]: role for row, role in zip(rows, ("train", "validation", "test"))})
                write(path.parent / "split.json", manifest)
                write(path.parent / "audit.json", dict(dataset_sha256=sha, split_counts=manifest["counts"], counts=dict(written_records=3), maximum_atoms=2))
                expected = inspect_dataset(root, "mlearn-forcefield", (sha, (1, 1, 1)))
                registry = copy.deepcopy(primary["registry"]); registry["datasets"]["mlearn-forcefield"] = expected
                with patch.dict(recipes.DATASETS, {"mlearn-forcefield": (sha, (1, 1, 1))}), \
                        patch.dict(module.DATASETS, {"mlearn-forcefield": (sha, (1, 1, 1))}):
                    updated = build_matrix(registry)
                    with patch.object(module, "PRIMARY_SHA", canonical_digest(updated)), self.assertRaises((ValueError, KeyError)):
                        module.inspect_frozen_inputs(updated)

    def test_export_is_fresh_and_never_invokes_training(self):
        with sources() as (root, primary, paths):
            result = module.write_frozen_definitions(primary, root / "output")
            self.assertEqual(result, json.loads((root / "output/definitions.json").read_bytes()))
            self.assertEqual(len(list((root / "output/configs").glob("*.json"))), 8)
            for case in result["cases"]: self.assertEqual(json.loads((root / "output" / case["config_path"]).read_bytes()), case["config"])
            with self.assertRaises(FileExistsError): module.write_frozen_definitions(primary, root / "output")

    def test_cli_requires_slurm_before_source_work(self):
        script = str(Path(__file__).resolve().parents[1] / "scripts/prepare_frozen_experiment_definitions.py")
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", [script, "--output", "unused"]), redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error: runpy.run_path(script, run_name="__main__")
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__": unittest.main()
