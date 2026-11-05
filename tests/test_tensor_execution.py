"""Synthetic protocol controls; actual models/numerical acceptance run in Slurm."""

import copy
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.supplemental_tensors import execution as tensor
from universal_gnn.benchmarks.supplemental_tensors.gate import DEFINITION_SHA, checked_tensor_physics
from universal_gnn.benchmarks.prediction_assessment import runtime
from universal_gnn.benchmarks.prediction_assessment.contracts import SHAPES, UNITS, full_inference_config, rounded
from universal_gnn.benchmarks.prediction_assessment.rescoring import rescore_saved
from universal_gnn.benchmarks.prediction_assessment.streaming import verify_inference_stream
from universal_gnn.benchmarks.execution.gates import canonical_digest, file_sha
from universal_gnn.benchmarks.execution.runner import verify_training_report
from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.evaluation.metrics import RegressionMetrics
from universal_gnn.properties import property_spec

helpers = runpy.run_path(str(Path(__file__).with_name("test_prediction_assessment.py")))
formal_fixture = runpy.run_path(str(Path(__file__).with_name("test_formal_execution.py")))["report_fixture"]
physics_fixture = runpy.run_path(str(Path(__file__).with_name("test_tensor_preparation_gate.py")))["physics"]
write, jsonl = helpers["write"], helpers["jsonl"]


def nested(shape, value=0.):
    return value if not shape else [nested(shape[1:], value) for _ in range(shape[0])]


@contextmanager
def raw_fixture(task):
    with helpers["fixture"]() as (root, path, trained, rows):
        config = trained["config"]
        config["task"] = dict(kind="supervised", property=task)
        config["dataset"]["bindings"] = {task: dict(key=task, unit=UNITS[task])}
        records = [json.loads(line) for line in Path(config["dataset"]["path"]).read_text().splitlines()]
        for record in records:
            values = nested(SHAPES[task][1:])
            if record["id"] != "3":
                leaf = values
                for _ in range(len(SHAPES[task]) - 3):
                    leaf = leaf[0]
                leaf[0][1] = 1 / 3
            record["targets"] = {task: values}
        jsonl(config["dataset"]["path"], records)
        source_sha = file_sha(config["dataset"]["path"])
        manifest = create_manifest([dict(id=str(i), group=str(i)) for i in range(5)], source_sha256=source_sha,
            official={str(i): "train" if i < 2 else "validation" if i == 2 else "test" for i in range(5)})
        write(config["dataset"]["split_manifest"], manifest)
        config["dataset"].update(sha256=source_sha, split_manifest_sha256=canonical_digest(manifest))
        accumulator = RegressionMetrics()
        for row, record in zip(rows, records[3:]):
            value = rounded([record["targets"][task]], "float32")
            def predict(v):
                return [predict(x) for x in v] if isinstance(v, list) else rounded(v + .25, "float32")
            row.update(targets={task: value}, predictions={task: predict(value)})
            accumulator.update(row["predictions"][task], value)
        jsonl(trained["heldout"]["predictions"], rows)
        trained["heldout"].update(source_sha256=source_sha, metrics={task: accumulator.result()})
        trained["heldout"]["selection"]["tracker"]["manifest_sha256"] = canonical_digest(manifest)
        write(path, trained)
        yield root, path, trained, rows


def stream_records(trained, task):
    result = [dict(type="metadata", structures=[], checkpoint=trained["best_checkpoint"],
                   config=full_inference_config(trained["config"]), structure_count=5)]
    result += [dict(type="prediction", id=str(i), predictions={task: nested(SHAPES[task])}, derived={}) for i in range(5)]
    return result + [dict(type="completed", structure_count=5)]


@contextmanager
def pair_fixture():
    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
        root = Path(folder)
        stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "protocol-fixture"}))
        stack.enter_context(patch.object(tensor.sys, "prefix", "/fixture/universal-official"))
        stack.enter_context(patch.object(tensor, "compatible_sources", return_value="b" * 40))
        pair = "rank34--seed-123--piezoelectric--alignn"
        specs, gates = {}, {}
        preparation = root / "prep"
        for mode in ("pretrained", "scratch"):
            identifier = pair + "--" + mode
            case = dict(id=identifier, pair_id=pair, task="piezoelectric", model="alignn", seed=123,
                        initialization=mode, python_environment="universal-official", tensor_shape=[3, 3, 3],
                        run_directory=str(root / mode))
            specs[identifier] = dict(case=case, counts=dict(train=3, validation=1, test=1))
            gates[mode] = dict(status="passed", kind="independent_supplemental_tensor_execution_gate",
                case=case, config=dict(synthetic=True), counts=specs[identifier]["counts"], definition_sha256=DEFINITION_SHA,
                matrix_sha256=DEFINITION_SHA, budget_seconds=1000., common_batch_size=4,
                preparation=str(preparation), git_commit="a" * 40)
            write(root / ("gate-" + mode + ".json"), gates[mode])
        parent = dict(status="passed", stage="complete", kind="independent_supplemental_pair_preparation",
            pair_id=pair, definition_sha256=DEFINITION_SHA, seed=123, model="alignn", task="piezoelectric",
            formal_training_runs=0, new_training_jobs=0, counts=dict(train=3, validation=1, test=1),
            budget_seconds=1000., common_batch_size=4, git_commit="a" * 40,
            gates={m: dict(case_id=g["case"]["id"], status="passed", sha256=file_sha(root / ("gate-" + m + ".json")))
                   for m, g in gates.items()})
        write(root / "report.json", parent)
        stack.enter_context(patch.object(tensor, "selected_case", side_effect=lambda settings, identifier: copy.deepcopy(specs[identifier])))
        rebuild = stack.enter_context(patch.object(tensor, "check_tensor_preparation", return_value=dict(gates["pretrained"], git_commit="b" * 40)))
        yield root, pair + "--pretrained", preparation, gates, parent, rebuild


class TensorExecutionTests(unittest.TestCase):
    def test_shapes_and_units_match_registered_cartesian_properties(self):
        for task in ("piezoelectric", "elastic"):
            spec = property_spec(task)
            self.assertEqual(SHAPES[task], (1, *spec.shape))
            self.assertEqual(UNITS[task], spec.unit)

    def test_both_full_raw_formats_include_zero_nonzero_and_every_component(self):
        for task in ("piezoelectric", "elastic"):
            with self.subTest(task=task), raw_fixture(task) as (root, path, trained, rows):
                result = rescore_saved(path, root / "rescore")
                self.assertEqual(result["metrics"], trained["heldout"]["metrics"])
                groups = result["tensor_groups"]
                self.assertEqual(groups["shape"], list(SHAPES[task][1:]))
                for group in ("zero", "nonzero"):
                    self.assertEqual(groups["groups"][group]["metrics"]["structures"], 1)
                self.assertEqual(groups["component_label_groups"]["nonzero"]["finite_elements"], 1)
                self.assertEqual(sum(groups["overall"]["component_finite_counts"]), 2 * (27 if task == "piezoelectric" else 81))
                output = root / "all.jsonl"
                jsonl(output, stream_records(trained, task))
                verified = verify_inference_stream(path, output, expected_sha256=file_sha(output), expected_bytes=output.stat().st_size)
                self.assertEqual(verified["structures"], 5)

    def test_raw_tensor_rejects_wrong_unit_axis_target_id_and_metric(self):
        for task in ("piezoelectric", "elastic"):
            for change in ("unit", "shape", "target", "id", "metric"):
                with self.subTest(task=task, change=change), raw_fixture(task) as (root, path, trained, rows):
                    if change == "unit":
                        trained["config"]["dataset"]["bindings"][task]["unit"] = "wrong"
                    elif change == "metric":
                        trained["heldout"]["metrics"][task]["mae"] += .1
                    elif change == "shape":
                        rows[0]["predictions"][task] = [[0.] * (27 if task == "piezoelectric" else 81)]
                    elif change == "id":
                        rows.reverse()
                    else:
                        rows[0]["targets"][task] = nested(SHAPES[task], .125)
                    jsonl(trained["heldout"]["predictions"], rows)
                    write(path, trained)
                    with self.assertRaises(ValueError):
                        rescore_saved(path, root / "rejected")

    def test_training_verifier_accepts_only_complete_rank3_and_rank4_shapes(self):
        for task in ("piezoelectric", "elastic"):
            with self.subTest(task=task), formal_fixture("dielectric") as (root, trained, gate, events):
                for config in (trained["config"], gate["config"]):
                    config["task"]["property"] = task
                gate["case"]["task"] = task
                rows = [dict(id="fixture-" + str(i), predictions={task: nested(SHAPES[task])},
                             targets={task: nested(SHAPES[task])}) for i in (5, 6)]
                jsonl(trained["heldout"]["predictions"], rows)
                self.assertEqual(verify_training_report(trained, gate, events)["test_structures"], 2)
                rows[0]["predictions"][task] = nested((1, 3, 3))
                jsonl(trained["heldout"]["predictions"], rows)
                with self.assertRaises(ValueError):
                    verify_training_report(trained, gate, events)

    def test_cpu_physics_preserves_rank_parity_original_tolerances_and_provider(self):
        for rank in (3, 4):
            for model in ("cgcnn", "alignn", "mace", "nequip"):
                case = dict(tensor_shape=[3] * rank, model=model)
                report = physics_fixture(case, ["0", "1"])
                report["device"] = "cpu"
                checked_tensor_physics(report, case, ["0", "1"], device="cpu")
                with self.assertRaises(ValueError):
                    checked_tensor_physics(report, case, ["0", "1"])
                for change in ("parity", "gradient", "tolerance", "numeric", "device", "provider"):
                    bad = copy.deepcopy(report)
                    if change == "parity": bad["response"]["inversion_parity"] *= -1
                    elif change == "gradient": bad["mixed_parameter_gradient_norms"]["backbone"] = 0.
                    elif change == "tolerance": bad["checks"]["response_auxiliary_finite_difference"]["atol"] *= 2
                    elif change == "numeric": bad["response"]["numeric"] = nested((1, *case["tensor_shape"]), .5)
                    elif change == "device": bad["device"] = "cuda:0"
                    else: bad["response"]["guarantee"] = "SO3_cartesian"
                    with self.subTest(rank=rank, model=model, change=change), self.assertRaises(ValueError):
                        checked_tensor_physics(bad, case, ["0", "1"], device="cpu")

    def test_pair_gate_rebuild_requires_both_hashed_gates_and_preserves_budget(self):
        with pair_fixture() as (root, identifier, prep, gates, parent, rebuild):
            result = tensor.checked_pair_gate({}, identifier, prep, root, budget_seconds=1000.)
            self.assertEqual(result["git_commit"], "b" * 40)
            self.assertEqual(len(result["independent_pair_gate"]["input_sha256"]), 3)
            rebuild.assert_called_once()

    def test_pair_gate_rejects_incomplete_wrong_case_budget_or_changed_saved_evidence(self):
        for change in ("status", "seed", "mode", "hash", "budget", "preparation", "rebuilt"):
            with self.subTest(change=change), pair_fixture() as (root, identifier, prep, gates, parent, rebuild):
                if change == "status": parent["status"] = "running"
                elif change == "seed": parent["seed"] = 456
                elif change == "mode": parent["gates"].pop("scratch")
                elif change == "hash": (root / "gate-scratch.json").write_bytes(b"{}")
                elif change == "budget": parent["budget_seconds"] = 1001
                elif change == "preparation": prep = root / "other"
                else: rebuild.return_value["common_batch_size"] = 2
                write(root / "report.json", parent)
                with self.assertRaises(ValueError):
                    tensor.checked_pair_gate({}, identifier, prep, root, budget_seconds=1000.)

    def test_training_does_not_execute_before_independent_gate_or_rerun_outputs(self):
        with pair_fixture() as (root, identifier, prep, gates, parent, rebuild), \
                patch.object(tensor, "_run_prepared_case", return_value={"status": "passed"}) as train:
            result = tensor.run_tensor_case({}, identifier, prep, root, budget_seconds=1000.)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(train.call_args.kwargs, dict(budget_seconds=1000.))
            (root / "pretrained").mkdir()
            train.reset_mock()
            with self.assertRaises(FileExistsError): tensor.run_tensor_case({}, identifier, prep, root, budget_seconds=1000.)
            train.assert_not_called()
        with pair_fixture() as (root, identifier, prep, gates, parent, rebuild), \
                patch.object(tensor, "_run_prepared_case") as train:
            parent["status"] = "failed"; write(root / "report.json", parent)
            with self.assertRaises(ValueError): tensor.run_tensor_case({}, identifier, prep, root, budget_seconds=1000.)
            train.assert_not_called()

    def test_context_replays_full_training_and_binds_original_gate_inputs(self):
        for change in (None, "events", "requested", "formal", "gate"):
            with self.subTest(change=change), formal_fixture("dielectric") as (root, trained, gate, events), ExitStack() as stack:
                task = "piezoelectric"
                identifier = "rank34--seed-123--piezoelectric--alignn--pretrained"
                for config in (trained["config"], gate["config"]): config["task"]["property"] = task
                case = dict(id=identifier, task=task, seed=123, model="alignn", initialization="pretrained",
                            python_environment="universal-official", run_directory=str(root), tensor_shape=[3, 3, 3])
                rows = [dict(id="fixture-" + str(i), targets={task: nested(SHAPES[task])},
                             predictions={task: nested(SHAPES[task])}) for i in (5, 6)]
                jsonl(trained["heldout"]["predictions"], rows)
                settings = dict(definitions=str(root / "definitions.json"), primary_matrix=str(root / "primary.json"))
                for path in settings.values(): write(path, {})
                preparation = root / "prep"; preparation.mkdir(); write(preparation / "report.json", {})
                claim = root / "claim"; claim.mkdir()
                for name in ("job.json", "terminal.json"): write(claim / name, {})
                (claim / "request.sh").write_bytes(b"fixture request; never executed")
                independent = root / "independent"; independent.mkdir(); write(independent / "report.json", {})
                gate.update(case=case, kind="independent_supplemental_tensor_execution_gate", definition_sha256=DEFINITION_SHA,
                    matrix_sha256=DEFINITION_SHA, git_commit="b" * 40, budget_seconds=1000., preparation=str(preparation),
                    preparation_receipt=dict(receipt=str(claim / "job.json")),
                    independent_pair_gate=dict(directory=str(independent), input_sha256={str(independent / "report.json"): file_sha(independent / "report.json")}),
                    execution_definitions=settings["definitions"], execution_primary_matrix=settings["primary_matrix"])
                trained["execution"]["git_commit"] = "b" * 40
                trained["checkpoint"] = str(root / "last.pt"); (root / "last.pt").write_bytes(b"fixture last checkpoint")
                formal = dict(status="passed", stage="complete", formal_training_runs_completed=1, case_id=identifier,
                    counts=gate["counts"], matrix_sha256=DEFINITION_SHA, git_commit="b" * 40,
                    **{key: case[key] for key in ("model", "task", "seed", "initialization")})
                if change == "formal": formal["seed"] = 456
                write(root / "formal-status.json", formal); write(root / "report.json", trained)
                saved_gate = copy.deepcopy(gate)
                if change == "gate": saved_gate["common_batch_size"] = 1
                write(root / "execution-gate.json", saved_gate)
                requested = copy.deepcopy(gate["config"])
                if change == "requested": requested["batch_size"] = 1
                write(root / "config.requested.json", requested)
                jsonl(root / "events.jsonl", events[1:] if change == "events" else events)
                stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}))
                stack.enter_context(patch.object(tensor.sys, "prefix", "/fixture/universal-official"))
                stack.enter_context(patch.object(tensor, "selected_case", return_value=dict(case=case, counts=gate["counts"], matrix_sha256=DEFINITION_SHA)))
                stack.enter_context(patch.object(tensor, "compatible_sources", return_value="b" * 40))
                stack.enter_context(patch.object(tensor, "checked_pair_gate", return_value=gate))
                if change:
                    with self.assertRaises(ValueError): tensor.tensor_context(settings, identifier)
                else:
                    context = tensor.tensor_context(settings, identifier)
                    self.assertEqual(context["verified_training"]["test_structures"], 2)
                    for path in (claim / "terminal.json", claim / "request.sh", independent / "report.json", root / "definitions.json"):
                        self.assertEqual(context["input_sha256"][str(path)], file_sha(path))

    def test_separate_post_and_no_model_acceptance_cover_both_ranks_and_providers(self):
        for task in ("piezoelectric", "elastic"):
            for model in ("alignn", "mace"):
                with self.subTest(task=task, model=model), raw_fixture(task) as (root, path, trained, rows), ExitStack() as stack:
                    stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}))
                    context = helpers["PredictionAssessmentTests"].mock_context(path, trained, task)
                    case = context["gate"]["case"]
                    case.update(model=model, tensor_shape=list(SHAPES[task][1:]))
                    stack.enter_context(patch.object(tensor, "tensor_context", return_value=context))
                    stack.enter_context(patch.object(runtime, "compatible_sources", return_value="a" * 40))
                    stack.enter_context(patch.object(runtime, "physical_selection", return_value=dict(indices=[0, 1], ids=["0", "1"])))
                    stack.enter_context(patch.object(runtime.numerics, "peak_rss_bytes", return_value=1024))
                    stack.enter_context(patch.object(runtime.numerics, "forbid_models", side_effect=nullcontext))
                    physics = physics_fixture(case, ["0", "1"]); physics["device"] = "cpu"
                    physical = stack.enter_context(patch.object(runtime.numerics, "trained_physics", return_value=physics))
                    def infer(checkpoint, config, output):
                        jsonl(output, stream_records(trained, task)); return dict(streamed=True, structure_count=5)
                    inference = stack.enter_context(patch.object(runtime.numerics, "complete_inference", side_effect=infer))
                    post = tensor.postprocess_tensor_case({}, "fixture", root / "post")
                    self.assertEqual(post["stage"], "awaiting_independent_validation")
                    physical.reset_mock(); inference.reset_mock()
                    verified = tensor.verify_tensor_case({}, "fixture", root / "post", root / "verified")
                    self.assertEqual(verified["status"], "passed")
                    self.assertTrue(verified["model_execution_forbidden"])
                    physical.assert_not_called(); inference.assert_not_called()
                    bad = copy.deepcopy(physics); bad["response"]["inversion_parity"] *= -1
                    write(root / "post/trained-best-physics.json", bad)
                    with self.assertRaises(ValueError):
                        tensor.verify_tensor_case({}, "fixture", root / "post", root / "rejected")

    def test_cli_requires_slurm_and_stage_specific_explicit_inputs(self):
        script = str(Path(__file__).resolve().parents[1] / "scripts/run_tensor_case.py")
        for args, job in [(["train"], "fixture"), (["post"], "fixture"),
                          (["verify", "--output", "unused"], "fixture"),
                          (["post", "--output", "unused", "--preparation", "prep"], "fixture"),
                          (["train", "--preparation", "p", "--independent-gate", "g", "--budget-seconds", "1"], None)]:
            with self.subTest(args=args, job=job), patch.dict(os.environ, {"SLURM_JOB_ID": job} if job else {}, clear=True), \
                    patch.object(sys, "argv", [script, *args, "--case", "fixture"]), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as error: runpy.run_path(script, run_name="__main__")
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
