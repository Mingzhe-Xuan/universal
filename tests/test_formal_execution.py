"""Pure protocol controls; fixture reports never represent numerical training."""

import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.execution import case_spec, check_preparation, run_formal_case
from universal_gnn.benchmarks.execution.gates import checked_config, check_artifact_identity
from universal_gnn.benchmarks.experiments.registry import NEQUIP_ARCHITECTURE
from universal_gnn.benchmarks.execution.runner import allocation_budget, duration_seconds, verify_training_report

registry_fixture = runpy.run_path(str(Path(__file__).with_name("test_arxiv_experiment_definitions.py")))["registry_fixture"]


@contextmanager
def report_fixture(task="bandgap"):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source.jsonl"
        source.write_text("synthetic protocol fixture; not scientific structures", encoding="utf-8")
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest = dict(records=[dict(id="fixture-" + str(i)) for i in range(7)],
                        partitions=dict(train=[0, 1, 2], validation=[3, 4], test=[5, 6]))
        manifest_path = root / "split.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        config = dict(seed=123, structures="all", max_atoms=None, device="cuda", dtype="float32",
                      epochs=3, batch_size=2, evaluation=dict(patience=2, min_delta=0.),
                      backbone=dict(name="alignn", implementation="official", initialization="pretrained"),
                      dataset=dict(path=str(source), sha256=source_sha, split_manifest=str(manifest_path),
                                   split_manifest_sha256=canonical_digest(manifest), partition="train"),
                      prediction=dict(version=1, head_mode="reset", readout=dict(
                          name="node_mlp" if task == "forcefield" else "graph_mlp", pooling="sum" if task == "forcefield" else "mean",
                          hidden_features=[4], activation="silu")),
                      optimization=dict(train_backbone=True, train_readout=True),
                      task=dict(kind="forcefield") if task == "forcefield" else dict(kind="supervised", property=task))
        actual = copy.deepcopy(config)
        actual["dataset"].update(selection="first", selection_seed=123)
        actual["prediction"]["adapter"] = dict(name="none", version=1)
        actual["prediction"]["readout"].update(bias=True, feature_processing=dict(name="none", version=1))
        actual["resolved_components"] = dict(backbone_cutoff=5.)
        checkpoint = root / "best-fixture.bin"
        checkpoint.write_bytes(b"synthetic checkpoint identity fixture; never deserialized")
        shapes = dict(bandgap=[[1.25]], classification=[[.1, .9]], dielectric=[[[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]], spectrum=[[.1] * 200])
        rows = []
        for index in [5, 6]:
            if task == "forcefield":
                row = dict(id="fixture-" + str(index), natoms=2,
                           predictions=dict(total_energy=[[1.25]], forces=[[0., 0., 0.], [0., 0., 0.]]),
                           targets=dict(total_energy=[[1.]], forces=[[0., 0., 0.], [0., 0., 0.]]))
            else:
                row = dict(id="fixture-" + str(index), predictions={task: shapes[task]},
                           targets={task: [1] if task == "classification" else copy.deepcopy(shapes[task])})
            rows.append(row)
        predictions = root / "predictions.jsonl"
        predictions.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        history = [dict(epoch=i, loss=1. / i) for i in [1, 2, 3]]
        events = [row for h in history for row in [dict(event="validation", structures=2, **h),
                  dict(event="epoch", structures=3, minibatches=2, **h)]]
        tracker = dict(history=history, best_epoch=3, best_loss=1. / 3, bad_epochs=0,
                       manifest_sha256=canonical_digest(manifest))
        trained = dict(passed=True, checkpoint_reload=True, completed_epochs=3, requested_epochs=3,
                       selected_structures=3, available_structures=7,
                       resume=dict(path=None, kind="none", completed_epochs_before=0),
                       history=[1., .5, .3], backbone_gradient_norms=[1., 1., 1.], config=actual,
                       execution=dict(official=dict(initialization="pretrained", parameter_coverage=1.)),
                       reload_verification=dict(state_exact=True, deterministic_algorithms=True),
                       best_checkpoint=str(checkpoint), heldout=dict(structures=2, test_structures=2,
                           validation_structures=2, declared_train_structures=3, source_structures=7,
                           partition="test", checkpoint_role="validation_best", source_sha256=source_sha,
                           predictions=str(predictions), selection=dict(tracker=tracker,
                               best_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())))
        gate = dict(config=config, counts=dict(train=3, validation=2, test=2), source_structures=7,
                    backbone_cutoff=5., case=dict(task=task, initialization="pretrained"))
        yield root, trained, gate, events


class FormalExecutionTests(unittest.TestCase):
    def test_all120_predictive_cases_preserve_the_full144_matrix(self):
        matrix = build_matrix(registry_fixture())
        for task in ["classification", "bandgap", "dielectric", "spectrum", "forcefield"]:
            for provider in ["cgcnn", "alignn", "mace", "nequip"]:
                for mode in ["pretrained", "scratch"]:
                    for seed in [123, 456, 789]:
                        with self.subTest(task=task, provider=provider, mode=mode, seed=seed):
                            case = case_spec(matrix, f"seed-{seed}--{task}--{provider}--{mode}")
                            self.assertEqual(case["case"]["config"]["structures"], "all")
                            self.assertEqual(case["case"]["config"]["epochs"], 300)
                            self.assertGreater(case["counts"]["train"], 1000)

    def test_partial_matrix_changed_recipe_and_generation_are_rejected(self):
        matrix = build_matrix(registry_fixture())
        case = "seed-123--bandgap--cgcnn--pretrained"
        partial = copy.deepcopy(matrix)
        partial["cases"].pop()
        with self.assertRaises(ValueError):
            case_spec(partial, case)
        changed = copy.deepcopy(matrix)
        item = next(c for c in changed["cases"] if c["id"] == case)
        item["config"]["epochs"] = 3
        item["config_sha256"] = canonical_digest(item["config"])
        with self.assertRaises(ValueError):
            case_spec(changed, case)
        with self.assertRaisesRegex(ValueError, "Generation"):
            case_spec(matrix, "seed-123--generation--cgcnn--pretrained")

    def test_native_calibration_must_match_whole_training_source(self):
        spec = case_spec(build_matrix(registry_fixture()), "seed-123--forcefield--mace--scratch")
        original = spec["case"]["config"]
        actual = copy.deepcopy(original)
        actual["batch_size"] = 2
        actual["backbone"]["neighbor_statistics"] = dict(structures=1309, declared_training_structures=1309,
            partition="train", source_sha256=original["dataset"]["sha256"],
            manifest_sha256=original["dataset"]["split_manifest_sha256"], dtype="float32")
        checked_config(actual, original, 2, spec["counts"])
        for key, value in [("structures", 64), ("partition", "test"), ("source_sha256", "b" * 64)]:
            with self.subTest(field=key):
                changed = copy.deepcopy(actual)
                changed["backbone"]["neighbor_statistics"][key] = value
                with self.assertRaises(ValueError):
                    checked_config(changed, original, 2, spec["counts"])

    def test_five_saved_output_formats_are_verified(self):
        for task in ["bandgap", "classification", "dielectric", "spectrum", "forcefield"]:
            with self.subTest(task=task), report_fixture(task) as (_, trained, gate, events):
                proof = verify_training_report(trained, gate, events)
                self.assertEqual(proof["test_structures"], 2)

    def test_nequip_scratch_adds_only_its_pinned_constructor_blueprint(self):
        artifacts = {"package.zip": {"sha256": "a" * 64}, NEQUIP_ARCHITECTURE[0]: {"sha256": "b" * 64}}
        graph = dict(artifact_sha256={"package": "a" * 64})
        check_artifact_identity(dict(initialization="pretrained", sha256={"package": "a" * 64}), graph, artifacts, "nequip")
        scratch = dict(initialization="scratch", sha256={"package": "a" * 64, "blueprint": "b" * 64})
        check_artifact_identity(scratch, graph, artifacts, "nequip")
        for key, value in [("package", "c" * 64), ("blueprint", "c" * 64), ("unknown", "b" * 64)]:
            with self.subTest(field=key):
                changed = copy.deepcopy(scratch)
                changed["sha256"][key] = value
                with self.assertRaises(ValueError):
                    check_artifact_identity(changed, graph, artifacts, "nequip")

    def test_truncated_epochs_validation_initialization_and_config_are_rejected(self):
        for mutation in ["epoch", "validation", "gradients", "head", "resume", "best"]:
            with self.subTest(mutation=mutation), report_fixture() as (_, trained, gate, events):
                if mutation == "epoch":
                    events.pop()
                elif mutation == "validation":
                    events[0]["structures"] = 1
                elif mutation == "gradients":
                    trained["backbone_gradient_norms"][0] = 0.
                elif mutation == "head":
                    trained["config"]["prediction"]["head_mode"] = "native"
                elif mutation == "resume":
                    trained["resume"]["kind"] = "weights_only"
                else:
                    trained["heldout"]["selection"]["tracker"]["best_epoch"] = 1
                with self.assertRaises(ValueError):
                    verify_training_report(trained, gate, events)

    def test_complete_ids_finite_values_shapes_and_best_bytes_are_required(self):
        for mutation in ["id", "nan", "shape", "bestbytes", "sourcebytes"]:
            with self.subTest(mutation=mutation), report_fixture() as (root, trained, gate, events):
                path = Path(trained["heldout"]["predictions"])
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                if mutation == "id":
                    rows[1]["id"] = rows[0]["id"]
                elif mutation == "nan":
                    rows[0]["predictions"]["bandgap"] = [[float("nan")]]
                elif mutation == "shape":
                    rows[0]["predictions"]["bandgap"] = [1.25]
                elif mutation == "bestbytes":
                    Path(trained["best_checkpoint"]).write_bytes(b"changed")
                else:
                    (root / "source.jsonl").write_text("changed")
                path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
                with self.assertRaises(ValueError):
                    verify_training_report(trained, gate, events)

    def test_actual_gpu_allocation_and_remaining_time_are_required(self):
        detail = "AllocTRES=cpu=2,mem=64G,gres/gpu=1 TimeLimit=01:00:00 RunTime=00:10:00"
        with patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), patch("subprocess.check_output", return_value=detail):
            self.assertEqual(allocation_budget(4000, 1000), 3000)
            with self.assertRaises(RuntimeError):
                allocation_budget(4000, 2500)
        with patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), patch("subprocess.check_output", return_value=detail.replace(",gres/gpu=1", "")):
            with self.assertRaises(RuntimeError):
                allocation_budget(4000, 1000)
        self.assertEqual(duration_seconds("1-02:03:04"), 93784)
        with self.assertRaises(ValueError):
            duration_seconds("00:61:00")

    def test_guards_refuse_login_and_existing_output_before_runtime(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Slurm"):
                check_preparation({}, "unused", "unused", budget_seconds=10)
            with self.assertRaisesRegex(RuntimeError, "Slurm"):
                run_formal_case({}, "unused", "unused", budget_seconds=10)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), patch(
                "universal_gnn.benchmarks.execution.runner.case_spec", return_value=dict(case=dict(run_directory=directory))):
            with self.assertRaises(FileExistsError):
                run_formal_case({}, "unused", "unused", budget_seconds=10)


if __name__ == "__main__":
    unittest.main()
