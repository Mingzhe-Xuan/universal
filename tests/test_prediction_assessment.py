"""Protocol fixtures only: numerical model/CPU softmax acceptance belongs to Slurm."""

import copy
from contextlib import ExitStack, contextmanager, nullcontext
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.prediction_assessment import rescore_saved, verify_inference_stream
from universal_gnn.benchmarks.prediction_assessment.contracts import (
    SHAPES, UNITS, compare, full_inference_config, rounded, source_context,
)
from universal_gnn.benchmarks.prediction_assessment import runtime
from universal_gnn.benchmarks.execution.gates import canonical_digest, file_sha
from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.evaluation.metrics import BinaryClassificationMetrics, RegressionMetrics


def write(path, value):
    Path(path).write_bytes(json.dumps(value, allow_nan=False).encode())


def jsonl(path, rows):
    Path(path).write_bytes(b"".join((json.dumps(row) + "\n").encode() for row in rows))


@contextmanager
def fixture(task="bandgap", dtype="float32"):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "structures.jsonl"
        source_rows, rows = [], []
        names = ["total_energy", "forces"] if task == "forcefield" else [task]
        bindings = {name: dict(key="energy" if name == "total_energy" else name, unit=UNITS[name]) for name in names}
        for i in range(5):
            count = 1 + i % 3
            if task == "classification":
                labels = {task: i % 2}
            elif task == "forcefield":
                labels = dict(energy=0. if i == 3 else 1 / 3,
                              forces=[[0., 0., 0.] for _ in range(count)])
                if i != 3:
                    labels["forces"][0][1] = 1 / 3
            elif task == "dielectric":
                labels = {task: [[0., 0., 0.] for _ in range(3)]}
                if i != 3:
                    labels[task][0][1] = 1 / 3
            elif task == "spectrum":
                labels = {task: [0.] * 200}
                if i != 3:
                    labels[task][199] = 1 / 3
            else:
                labels = {task: 0. if i == 3 else 1 / 3}
            source_rows.append(dict(id=str(i), numbers=[14] * count, targets=labels))
            if i < 3:
                continue
            targets, predicted = {}, {}
            for name, binding in bindings.items():
                target = labels[binding["key"]]
                if name == "classification":
                    targets[name], predicted[name] = [target], [[0., 0.]]
                    continue
                if name in ["bandgap", "total_energy"]:
                    target = [[target]]
                elif name != "forces":
                    target = [target]
                targets[name] = rounded(target, dtype)
                def add(value):
                    return [add(item) for item in value] if isinstance(value, list) else rounded(value + .25, dtype)
                predicted[name] = add(targets[name])
            rows.append(dict(id=str(i), natoms=count, targets=targets, predictions=predicted))
        jsonl(source, source_rows)
        manifest = create_manifest([dict(id=str(i), group=str(i)) for i in range(5)], source_sha256=file_sha(source),
            official={str(i): "train" if i < 2 else "validation" if i == 2 else "test" for i in range(5)})
        split = root / "split.json";write(split, manifest)
        task_config = (dict(kind="forcefield", supervised_outputs=names) if task == "forcefield" else
                       dict(kind="supervised", property=task))
        if task == "spectrum":
            task_config["channels"] = 200
        config = dict(structures="all", dtype=dtype, device="cuda", seed=123, batch_size=2,
            max_atoms=None, task=task_config,
            dataset=dict(path=str(source), sha256=file_sha(source), partition="train", bindings=bindings,
                         split_manifest=str(split), split_manifest_sha256=canonical_digest(manifest)))
        checkpoint = root / "best.pt";checkpoint.write_bytes(b"not a real checkpoint; never loaded")
        last = root / "last.pt";last.write_bytes(b"retained last fixture")
        predictions = root / "test.jsonl";jsonl(predictions, rows)
        metrics = {}
        if task == "classification":
            with BinaryClassificationMetrics(root / "reference.sqlite") as accumulator:
                for row in rows:
                    accumulator.update(.5, row["targets"][task][0], predicted_class=0)
                metrics[task] = accumulator.result()
        else:
            for name in names:
                accumulator = RegressionMetrics()
                for row in rows:
                    accumulator.update(row["predictions"][name], row["targets"][name])
                metrics[name] = accumulator.result()
            if task == "forcefield":
                accumulator = RegressionMetrics()
                for row in rows:
                    accumulator.update(rounded([[row["predictions"]["total_energy"][0][0] / row["natoms"]]], dtype),
                                       rounded([[row["targets"]["total_energy"][0][0] / row["natoms"]]], dtype))
                metrics["energy_per_atom"] = {**accumulator.result(), "unit": "eV/atom"}
        report = dict(passed=True, config=config, selected_structures=2, checkpoint=str(last),
            best_checkpoint=str(checkpoint), heldout=dict(partition="test", checkpoint_role="validation_best",
                structures=2, test_structures=2, validation_structures=1, declared_train_structures=2,
                source_structures=5, source_sha256=file_sha(source), predictions=str(predictions), metrics=metrics,
                selection=dict(best_sha256=file_sha(checkpoint), tracker=dict(manifest_sha256=canonical_digest(manifest)))))
        report_path = root / "training.json";write(report_path, report)
        yield root, report_path, report, rows


def stream_rows(report):
    config = report["config"]
    source = [json.loads(line) for line in Path(config["dataset"]["path"]).read_text().splitlines()]
    task = "forcefield" if config["task"]["kind"] == "forcefield" else config["task"]["property"]
    rows = [dict(type="metadata", structures=[], checkpoint=report["best_checkpoint"],
                 config=full_inference_config(config), structure_count=len(source))]
    for record in source:
        if task == "forcefield":
            values = dict(total_energy=[[0.]], forces=[[0., 0., 0.]] * len(record["numbers"]),
                          stress=[[[0.] * 3 for _ in range(3)]])
        elif task == "dielectric":
            values = {task: [[[0.] * 3 for _ in range(3)]]}
        else:
            values = {task: [[0.] * SHAPES[task][-1]]}
        rows.append(dict(type="prediction", id=record["id"], predictions=values, derived={}))
    return rows + [dict(type="completed", structure_count=len(source))]


def physics_fixture(task, ids):
    if task == "forcefield":
        names = {"forces_finite_difference": (.02, .002, True), "stress_finite_difference": (.02, .002, True),
                 "net_force": (0, 2e-5, True)}
        names.update({"translation_" + k: (.001, .0002, True) for k in ["total_energy", "forces", "stress"]})
        names.update({"rotation_" + k: (.001, .0002, True) for k in ["energy", "forces", "stress"]})
        names.update({mode + "_batch_" + k: (2e-4, 2e-5, True)
                      for mode in ["train", "eval"] for k in ["total_energy", "forces", "stress"]})
    else:
        names = dict(response_auxiliary_finite_difference=(2e-4, 2e-5, True), translation_response=(.001, .0002, True),
                     eval_batch_response=(2e-4, 2e-5, True), rotation_response_covariance=(.001, .0002, False),
                     rotation_fixed_frame_invariance=(.001, .0002, True))
    result = dict(passed=True, device="cpu", dtype="torch.float32", structure_ids=ids,
                  geometry_tolerance=dict(rtol=.001, atol=.0002), mixed_parameter_gradient_norms=dict(backbone=.1, readout=.2),
                  checks={name: dict(rtol=r, atol=a, required=required, passed=True, max_abs_error=0.)
                          for name, (r, a, required) in names.items()})
    if task == "dielectric":
        result["response"] = dict(guarantee="fixed_frame_components", no_symmetry_projection=True)
    return result


class PredictionAssessmentTests(unittest.TestCase):
    def setUp(self):
        process_cost=patch.object(runtime.numerics,"peak_rss_bytes",return_value=1024)
        process_cost.start();self.addCleanup(process_cost.stop)

    def test_all_five_saved_formats_raw_labels_and_metric_populations(self):
        for task in ["bandgap", "classification", "dielectric", "spectrum", "forcefield"]:
            with self.subTest(task=task), fixture(task) as (root, path, report, rows), \
                    patch("universal_gnn.benchmarks.prediction_assessment.rescoring.class_observation", return_value=(.5, 0)) as softmax:
                before = path.read_bytes()
                result = rescore_saved(path, root / "out")
                self.assertEqual(result["metrics"], report["heldout"]["metrics"])
                self.assertEqual(result["structures"], 2)
                self.assertEqual(result["source_structures"], 5)
                self.assertEqual(result["formal_training_runs"], 0)
                self.assertEqual(path.read_bytes(), before)
                if task == "classification":
                    self.assertEqual(softmax.call_count, 2)
                    softmax.assert_called_with([[0., 0.]], "float32")
                    self.assertEqual(result["metrics"][task]["roc_auc"], .5)
                    self.assertEqual(result["metrics"][task]["confusion_matrix_true_by_predicted"], [[1, 0], [1, 0]])
                if task == "dielectric":
                    self.assertEqual(result["tensor_groups"]["groups"]["zero"]["metrics"]["structures"], 1)
                    self.assertEqual(result["tensor_groups"]["component_label_groups"]["nonzero"]["finite_elements"], 1)
                    self.assertEqual(result["tensor_groups"]["overall"]["metrics"], report["heldout"]["metrics"][task])

    def test_float64_preserves_unrounded_original_labels(self):
        with fixture(dtype="float64") as (root, path, report, rows):
            self.assertEqual(rows[1]["targets"]["bandgap"], [[1 / 3]])
            self.assertNotEqual(rows[1]["targets"]["bandgap"], [[rounded(1 / 3, "float32")]])
            self.assertEqual(rescore_saved(path, root / "out")["dtype"], "float64")

    def test_explicit_legacy_diagnostic_metrics_keep_every_original_observation(self):
        for extra_missing in [False,True]:
            with self.subTest(extra_missing=extra_missing),fixture("classification") as (root,path,report,rows), \
                    patch("universal_gnn.benchmarks.prediction_assessment.rescoring.class_observation",return_value=(.5,0)):
                reference=report["heldout"]["metrics"]["classification"]
                for key in ["balanced_accuracy","balanced_accuracy_policy"]:reference.pop(key)
                if extra_missing:reference.pop("accuracy")
                write(path,report)
                with self.assertRaises(ValueError):rescore_saved(path,root/"strict")
                if extra_missing:
                    with self.assertRaises(ValueError):rescore_saved(path,root/"legacy",allow_legacy_classification=True)
                else:
                    result=rescore_saved(path,root/"legacy",allow_legacy_classification=True)
                    self.assertEqual(result["additional_legacy_classification_fields"],["balanced_accuracy","balanced_accuracy_policy"])
                    self.assertEqual(result["metrics"]["classification"]["balanced_accuracy"],.5)
                    self.assertEqual({key:result["metrics"]["classification"][key] for key in reference},reference)

    def test_test_order_count_target_shape_and_population_corruption_rejected(self):
        for change in ["duplicate", "missing", "reverse", "foreign", "target", "shape", "nonfinite", "bool",
                       "natoms", "output", "population", "metric", "relative"]:
            with self.subTest(change=change), fixture() as (root, path, report, rows):
                if change == "duplicate": rows.append(copy.deepcopy(rows[0]))
                elif change == "missing": rows.pop()
                elif change == "reverse": rows.reverse()
                elif change == "foreign": rows[0]["id"] = "0"
                elif change == "target": rows[1]["targets"]["bandgap"] = [[1 / 3]]
                elif change == "shape": rows[0]["predictions"]["bandgap"] = [1.]
                elif change == "nonfinite": rows[0]["predictions"]["bandgap"] = [[float("nan")]]
                elif change == "bool": rows[0]["predictions"]["bandgap"] = [[True]]
                elif change == "natoms": rows[0]["natoms"] += 1
                elif change == "output": rows[0]["predictions"]["other"] = [[0.]]
                elif change == "population": report["heldout"]["metrics"]["bandgap"]["finite_elements"] -= 1
                elif change == "relative": report["heldout"]["metrics"]["bandgap"]["relative_error_structures"] = 0
                else: report["heldout"]["metrics"]["bandgap"]["mae"] += .01
                jsonl(report["heldout"]["predictions"], rows);write(path, report)
                with self.assertRaises(ValueError): rescore_saved(path, root / "out")
                self.assertFalse((root / "out/report.json").exists())

    def test_source_manifest_and_unsupported_label_transforms_rejected(self):
        for change in ["source_bytes", "source_order", "manifest", "binding", "unit", "dtype", "subset", "counts", "selection"]:
            with self.subTest(change=change), fixture() as (root, path, report, rows):
                config = report["config"]
                if change == "source_bytes":
                    with Path(config["dataset"]["path"]).open("ab") as stream: stream.write(b"\n")
                elif change == "source_order":
                    source = Path(config["dataset"]["path"]);lines=source.read_bytes().splitlines(keepends=True)
                    source.write_bytes(b"".join(reversed(lines)))
                elif change == "manifest":
                    manifest=json.loads((root / "split.json").read_text());manifest["records"][0]["id"]="replaced"
                    write(root / "split.json", manifest)
                elif change == "binding": config["dataset"]["bindings"]["bandgap"]["factor"] = 2.
                elif change == "unit": config["dataset"]["bindings"]["bandgap"]["unit"] = "meV"
                elif change == "dtype": config["dtype"] = "float16"
                elif change == "subset": config["structures"] = 2
                elif change == "counts": report["selected_structures"] = 1
                else: report["heldout"]["selection"]["tracker"]["manifest_sha256"] = "0" * 64
                write(path, report)
                with self.assertRaises(ValueError): rescore_saved(path, root / "out")

    def test_class_labels_cannot_be_boolean_and_no_input_changes_mid_score(self):
        for change in ["target_bool", "raw_bool", "mutation"]:
            with self.subTest(change=change), fixture("classification") as (root, path, report, rows):
                if change == "target_bool":
                    rows[0]["targets"]["classification"] = [True];jsonl(report["heldout"]["predictions"], rows)
                if change == "raw_bool":
                    source = Path(report["config"]["dataset"]["path"])
                    records = [json.loads(x) for x in source.read_text().splitlines()];records[3]["targets"]["classification"] = True
                    jsonl(source, records)
                def fake_softmax(*args):
                    if change == "mutation":
                        with path.open("ab") as stream: stream.write(b" ")
                    return .5, 0
                with patch("universal_gnn.benchmarks.prediction_assessment.rescoring.class_observation", side_effect=fake_softmax):
                    with self.assertRaises(ValueError): rescore_saved(path, root / "out")

    def test_every_ordered_inference_shape_is_finite_and_complete(self):
        for task in ["bandgap", "classification", "dielectric", "spectrum", "forcefield"]:
            with self.subTest(task=task), fixture(task) as (root, path, report, _):
                output=root / "inference.jsonl";jsonl(output, stream_rows(report))
                result=verify_inference_stream(path, output, expected_sha256=file_sha(output), expected_bytes=output.stat().st_size)
                self.assertEqual(result["structures"], 5)
                self.assertTrue(result["all_ordered_ids_match_source"] and result["completion_marker_verified"])
                if task == "forcefield":
                    self.assertEqual(result["finite_prediction_elements"], dict(total_energy=5, forces=27, stress=45))

    def test_inference_corruption_is_rejected_even_with_matching_updated_file_hash(self):
        for change in ["missing_header", "checkpoint", "dtype", "partition", "batch", "missing", "duplicate", "order",
                       "early_marker", "no_marker", "after_marker", "shape", "nonfinite", "derived", "count", "hash", "bytes"]:
            with self.subTest(change=change), fixture() as (root, path, report, _):
                rows=stream_rows(report)
                if change == "missing_header": rows.pop(0)
                elif change == "checkpoint": rows[0]["checkpoint"] = str(root / "last.pt")
                elif change == "dtype": rows[0]["config"]["dtype"] = "float64"
                elif change == "partition": rows[0]["config"]["dataset"]["partition"] = "test"
                elif change == "batch": rows[0]["config"]["batch_size"] = 3
                elif change == "missing": rows.pop(2)
                elif change == "duplicate": rows.insert(2, copy.deepcopy(rows[1]))
                elif change == "order": rows[1],rows[2]=rows[2],rows[1]
                elif change == "early_marker": rows.insert(1, dict(type="completed", structure_count=5))
                elif change == "no_marker": rows.pop()
                elif change == "after_marker": rows.append(copy.deepcopy(rows[-1]))
                elif change == "shape": rows[1]["predictions"]["bandgap"] = [0.]
                elif change == "nonfinite": rows[1]["predictions"]["bandgap"] = [[float("inf")]]
                elif change == "derived": rows[1]["derived"] = dict(unrequested=[0.])
                elif change == "count": rows[0]["structure_count"] = 4
                output=root / "stream.jsonl";jsonl(output, rows)
                with self.assertRaises(ValueError):
                    verify_inference_stream(path, output, expected_sha256="0"*64 if change=="hash" else file_sha(output),
                        expected_bytes=output.stat().st_size + (1 if change=="bytes" else 0))

    def test_physics_keeps_distinct_response_force_tolerances_and_all_geometry_checks(self):
        for task in ["forcefield", "dielectric"]:
            selection=dict(ids=["0", "1"])
            good=physics_fixture(task, selection["ids"])
            runtime.verify_physics(good, task, selection)
            for change in ["required", "check", "tolerance", "geometry", "gradient", "id"]:
                with self.subTest(task=task,change=change):
                    bad=copy.deepcopy(good);key=next(iter(bad["checks"]))
                    if change=="required": bad["checks"][key]["required"]=False
                    elif change=="check": bad["checks"].pop(key)
                    elif change=="tolerance": bad["checks"][key]["atol"] *= 10
                    elif change=="geometry": bad["geometry_tolerance"]["rtol"] *= 10
                    elif change=="gradient": bad["mixed_parameter_gradient_norms"]["backbone"]=0.
                    else: bad["structure_ids"].reverse()
                    with self.assertRaises(ValueError):runtime.verify_physics(bad, task, selection)

    def test_safety_existing_output_and_cli_slurm_guard(self):
        with fixture() as (root, path, report, rows):
            (root / "existing").mkdir();(root / "existing/keep").write_text("keep")
            with self.assertRaises(FileExistsError):rescore_saved(path, root / "existing")
            self.assertEqual((root / "existing/keep").read_text(), "keep")
            with patch.dict(os.environ, {}, clear=True):
                for function,args in [(runtime.postprocess_case, ({},"case",root/"out")),
                                      (runtime.verify_case, ({},"case",root/"post",root/"verify"))]:
                    with self.assertRaisesRegex(RuntimeError,"Slurm"):function(*args)
                with patch.object(sys,"argv",["assess_prediction.py","post","--output",str(root/"cli")]):
                    with self.assertRaises(SystemExit) as error:
                        runpy.run_path(str(Path(__file__).resolve().parents[1]/"scripts/assess_prediction.py"),run_name="__main__")
                    self.assertEqual(error.exception.code,2)
            self.assertFalse((root / "out").exists())

    def test_separate_post_and_saved_validation_stage_boundaries_for_all_tasks(self):
        for task in ["bandgap", "classification", "dielectric", "spectrum", "forcefield"]:
            with self.subTest(task=task), fixture(task) as (root,path,report,rows), ExitStack() as stack:
                context=self.mock_context(path, report, task)
                stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}))
                stack.enter_context(patch.object(runtime,"formal_context",return_value=context))
                stack.enter_context(patch.object(runtime,"compatible_sources",return_value="a"*40))
                stack.enter_context(patch.object(runtime,"physical_selection",return_value=dict(indices=[0,1],ids=["0","1"])))
                stack.enter_context(patch.object(runtime.numerics,"forbid_models",side_effect=nullcontext))
                stack.enter_context(patch("universal_gnn.benchmarks.prediction_assessment.rescoring.class_observation",return_value=(.5,0)))
                physical=stack.enter_context(patch.object(runtime.numerics,"trained_physics",return_value=physics_fixture(task,["0","1"])))
                def inferred(checkpoint,config,output):
                    self.assertEqual(checkpoint,report["best_checkpoint"])
                    self.assertEqual(config,report["config"])
                    jsonl(output, stream_rows(report))
                    return dict(streamed=True,structure_count=5)
                model_inference=stack.enter_context(patch.object(runtime.numerics,"complete_inference",side_effect=inferred))
                post=runtime.postprocess_case({},"fixture",root/"post")
                self.assertEqual(post["stage"],"awaiting_independent_validation")
                self.assertFalse(post["independent_output_verified"])
                self.assertEqual(physical.call_count,int(task in ["forcefield","dielectric"]))
                physical.reset_mock();model_inference.reset_mock()
                verified=runtime.verify_case({},"fixture",root/"post",root/"verification")
                self.assertEqual((verified["status"],verified["stage"]),("passed","complete"))
                self.assertTrue(verified["model_execution_forbidden"])
                self.assertEqual(verified["metrics"],report["heldout"]["metrics"])
                self.assertEqual(verified["inference_verification"]["structures"],5)
                self.assertEqual((physical.call_count,model_inference.call_count),(0,0))

    @staticmethod
    def mock_context(path, report, task):
        paths=[str(path),report["best_checkpoint"],report["checkpoint"],report["heldout"]["predictions"],
               report["config"]["dataset"]["path"],report["config"]["dataset"]["split_manifest"]]
        return dict(trained=report,report_path=path,git_commit="a"*40,
                    input_sha256={p:file_sha(p) for p in paths}, verified_training=dict(completed_epochs=3),
                    spec=dict(matrix_sha256="b"*64),gate=dict(case=dict(task=task),source_structures=5))

    def test_post_keeps_failed_physics_and_refuses_changed_checkpoint(self):
        for change in ["physics","checkpoint"]:
            with self.subTest(change=change),fixture("forcefield") as (root,path,report,rows),ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}))
                context=self.mock_context(path,report,"forcefield")
                stack.enter_context(patch.object(runtime,"formal_context",return_value=context))
                stack.enter_context(patch.object(runtime,"physical_selection",return_value=dict(indices=[0,1],ids=["0","1"])))
                physics=physics_fixture("forcefield",["0","1"])
                if change=="physics":physics["checks"]["net_force"]["passed"]=False
                stack.enter_context(patch.object(runtime.numerics,"trained_physics",return_value=physics))
                def infer(checkpoint,config,output):
                    jsonl(output,stream_rows(report));Path(checkpoint).write_bytes(b"mutated")
                    return dict(streamed=True,structure_count=5)
                inference=stack.enter_context(patch.object(runtime.numerics,"complete_inference",side_effect=infer))
                with self.assertRaises(ValueError):runtime.postprocess_case({},"fixture",root/"failed")
                failed=json.loads((root/"failed/report.json").read_text())
                self.assertEqual(failed["status"],"failed")
                self.assertTrue((root/"failed/trained-best-physics.json").is_file())
                self.assertEqual(inference.call_count,int(change=="checkpoint"))

    def test_independent_stage_rejects_changed_parent_evidence(self):
        for change in ["case","metric","raw_rescore","physics","inputs","stream","validator_source"]:
            with self.subTest(change=change),fixture("forcefield") as (root,path,report,rows),ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}))
                stack.enter_context(patch.object(runtime,"formal_context",return_value=self.mock_context(path,report,"forcefield")))
                stack.enter_context(patch.object(runtime,"compatible_sources",return_value="a"*40))
                stack.enter_context(patch.object(runtime,"physical_selection",return_value=dict(indices=[0,1],ids=["0","1"])))
                stack.enter_context(patch.object(runtime.numerics,"forbid_models",side_effect=nullcontext))
                stack.enter_context(patch.object(runtime.numerics,"trained_physics",return_value=physics_fixture("forcefield",["0","1"])))
                def infer(checkpoint,config,output):
                    jsonl(output,stream_rows(report));return dict(streamed=True,structure_count=5)
                stack.enter_context(patch.object(runtime.numerics,"complete_inference",side_effect=infer))
                runtime.postprocess_case({},"fixture",root/"post")
                parent_path=root/"post/report.json";parent=json.loads(parent_path.read_text())
                if change=="case":parent["case_id"]="wrong"
                elif change=="metric":parent["metrics"]["forces"]["mae"] += .1
                elif change=="inputs":parent["input_sha256"][str(path)]="0"*64
                elif change=="raw_rescore":(root/"post/heldout/report.json").write_bytes(b"{}")
                elif change=="physics":(root/"post/trained-best-physics.json").write_bytes(b"{}")
                elif change=="validator_source":parent["physical_validator_sha256"]={"wrong.py":"0"*64}
                else:
                    with (root/"post/all-source-predictions.jsonl").open("ab") as stream:stream.write(b"\n")
                write(parent_path,parent)
                with self.assertRaises(ValueError):runtime.verify_case({},"fixture",root/"post",root/"independent")
                self.assertEqual(json.loads((root/"independent/report.json").read_text())["status"],"failed")

    def test_formal_context_runs_original_complete_training_verifier_and_scope_guard(self):
        old_fixture=runpy.run_path(str(Path(__file__).with_name("test_formal_execution.py")))["report_fixture"]
        for change in [None,"events","requested","scope"]:
            with self.subTest(change=change),old_fixture() as (root,trained,gate,events),ExitStack() as stack:
                identifier="seed-123--bandgap--alignn--pretrained"
                case=dict(id=identifier,task="bandgap",seed=123,model="alignn",initialization="pretrained",
                          python_environment="universal-official",run_directory=str(root))
                if change=="scope":case["seed"]=456;case["id"]=identifier.replace("123","456")
                scope=json.loads((Path(__file__).resolve().parents[1]/"configs/arxiv_v1_scope.json").read_text())
                spec=dict(case=case,matrix_sha256=scope["base_matrix_sha256"],counts=gate["counts"])
                gate.update(case=case,preparation=str(root/"prep"),budget_seconds=1000,matrix_sha256=spec["matrix_sha256"])
                formal=dict(status="passed",stage="complete",formal_training_runs_completed=1,case_id=case["id"],
                            matrix_sha256=spec["matrix_sha256"],counts=gate["counts"],git_commit="b"*40,
                            **{k:case[k] for k in ["model","task","seed","initialization"]})
                (root/"prep").mkdir();write(root/"prep/report.json",{})
                trained["execution"]["git_commit"]="b"*40
                trained["checkpoint"]=str(root/"last.pt");(root/"last.pt").write_bytes(b"retained last")
                write(root/"report.json",trained);write(root/"formal-status.json",formal)
                write(root/"execution-gate.json",gate)
                requested=copy.deepcopy(gate["config"])
                if change=="requested":requested["batch_size"]=1
                write(root/"config.requested.json",requested)
                jsonl(root/"events.jsonl",events[1:] if change=="events" else events)
                stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}))
                stack.enter_context(patch.object(runtime,"case_spec",return_value=spec))
                stack.enter_context(patch.object(runtime.sys,"prefix","/fixtures/universal-official"))
                stack.enter_context(patch.object(runtime,"compatible_sources",return_value="a"*40))
                prepared=stack.enter_context(patch.object(runtime,"check_preparation",return_value=gate))
                if change:
                    with self.assertRaises(ValueError):runtime.formal_context({},case["id"])
                    if change=="scope":prepared.assert_not_called()
                else:
                    result=runtime.formal_context({},case["id"])
                    self.assertEqual(result["verified_training"]["completed_epochs"],3)
                    self.assertEqual(result["verified_training"]["test_structures"],2)
                    self.assertEqual(result["input_sha256"][trained["checkpoint"]],file_sha(trained["checkpoint"]))

    def test_independent_guard_blocks_model_loads_and_forwards(self):
        from types import SimpleNamespace
        from universal_gnn.benchmarks.prediction_assessment.numerics import forbid_models
        class FakeModule:
            def __call__(self):raise AssertionError("Original model call was reached")
        fake=SimpleNamespace(load=lambda:None,jit=SimpleNamespace(load=lambda:None),nn=SimpleNamespace(Module=FakeModule))
        with patch.dict(sys.modules,{"torch":fake}),forbid_models():
            for function in [fake.load,fake.jit.load,FakeModule()]:
                with self.assertRaisesRegex(RuntimeError,"must not load or run"):function()

    def test_cli_rejects_mixed_formal_and_diagnostic_arguments(self):
        from contextlib import redirect_stderr
        from io import StringIO
        script=str(Path(__file__).resolve().parents[1]/"scripts/assess_prediction.py")
        cases=[["post","--diagnostic"],["verify","--matrix","matrix.json","--matrix-sha256","0"*64,"--case","case"],
               ["rescore","--training-report","training.json"],
               ["rescore","--diagnostic","--training-report","training.json","--case","case"],
               ["post","--matrix","matrix.json","--matrix-sha256","0"*64,"--case","case","--postprocessing","post"],
               ["post","--matrix","matrix.json","--matrix-sha256","0"*64,"--case","case","--allow-legacy-classification"]]
        for arguments in cases:
            with self.subTest(arguments=arguments),patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}), \
                    patch.object(sys,"argv",[script,*arguments,"--output","unused"]),redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as error:runpy.run_path(script,run_name="__main__")
                self.assertEqual(error.exception.code,2)


if __name__ == "__main__":
    unittest.main()
