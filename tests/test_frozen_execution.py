"""Pure protocol controls; fixtures do not qualify scientific training or CUDA."""

import copy
from contextlib import contextmanager, ExitStack, nullcontext
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.execution.gates import file_sha
from universal_gnn.benchmarks.execution.runner import verify_training_report
from universal_gnn.benchmarks.frozen_backbones import execution as frozen
from universal_gnn.benchmarks.frozen_backbones import training_audit as audit
from universal_gnn.benchmarks.frozen_backbones.contracts import DEFINITION_SHA
from universal_gnn.benchmarks.prediction_assessment import runtime

HERE = Path(__file__).parent
formal_fixture = runpy.run_path(str(HERE / "test_formal_execution.py"))["report_fixture"]
helpers = runpy.run_path(str(HERE / "test_prediction_assessment.py"))
audit_fixture = runpy.run_path(str(HERE / "test_frozen_readiness.py"))["audit_fixture"]
jsonl = helpers["jsonl"]


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    helpers["write"](path, value)


@contextmanager
def full_fixture(task="dielectric"):
    with formal_fixture(task) as (root, trained, gate, events):
        for config in (gate["config"], trained["config"]):
            config["optimization"]["train_backbone"] = False
        identifier = "frozen--seed-123--" + task + "--alignn"
        gate["case"].update(id=identifier, model="alignn", seed=123, run_directory=str(root),
                            python_environment="universal-official")
        gate.update(status="passed", kind="formal_frozen_backbone_execution_gate", definition_sha256=DEFINITION_SHA,
            matrix_sha256=DEFINITION_SHA, frozen_audit=audit_fixture(), git_commit="a" * 40,
            preparation=str(root / "prep"), budget_seconds=1000., reference_preparation=str(root / "reference"))
        trained.update(backbone_gradient_norms=[0.] * 3, gradient_norms=[.1] * 3)
        trained["execution"]["git_commit"] = "a" * 40
        body = dict(trainable_parameters=0, mode="eval", module_modes=dict(train=0, eval=1))
        head = dict(trainable_parameters=10, mode="train")
        trained.update(components=dict(backbone=body, readout=dict(head, mode="eval")),
            components_during_training=dict(backbone=copy.deepcopy(body), readout=head))
        last = root / "last-fixture.bin";last.write_bytes(b"last synthetic checkpoint; not loaded")
        trained["checkpoint"] = str(last)
        state = audit_fixture(6)
        checkpoints = {role: dict(path=trained[key], sha256=file_sha(trained[key]), backbone_state_sha256="a" * 64,
            readout_parameters_sha256="e" * 64, components=trained["components"],
            optimizer_groups=[dict(name="readout", parameters=["fixture"])], policy=trained["config"]["optimization"])
            for role, key in (("best", "best_checkpoint"), ("last", "checkpoint"))}
        observed = dict(protocol=audit.PROTOCOL, source_sha256=audit.training_sources(),
            actual_training_delegate="src/universal_gnn/engine/training.py", optimizer=state, checkpoints=checkpoints)
        path = root / "frozen-training-audit.json";write(path, observed)
        trained["frozen_training_audit"] = dict(path=str(path), sha256=file_sha(path), protocol=audit.PROTOCOL)
        yield root, trained, gate, events, observed


class FrozenExecutionTests(unittest.TestCase):
    def test_full_frozen_epoch_test_and_both_checkpoint_contracts(self):
        for task in ("forcefield", "dielectric"):
            with self.subTest(task=task), full_fixture(task) as (_, trained, gate, events, _):
                result = frozen.verify_frozen_training(trained, gate, events)
                self.assertEqual(result["test_structures"], 2)
                self.assertEqual(result["frozen_training"]["optimizer_steps"], 6)
                self.assertEqual(set(result["frozen_training"]["checkpoint_sha256"]), {"best", "last"})

    def test_default_primary_and_high_rank_policy_still_refuses_zero_body_gradient(self):
        with full_fixture() as (_, trained, gate, events, _):
            with self.assertRaises(ValueError):
                verify_training_report(trained, gate, events)
            for change in ("kind", "definition", "id", "mode", "seed", "body_flag"):
                changed = copy.deepcopy(gate)
                if change == "kind":changed["kind"] = "primary"
                elif change == "definition":changed["definition_sha256"] = "f" * 64
                elif change == "id":changed["case"]["id"] += "--scratch"
                elif change == "mode":changed["case"]["initialization"] = "scratch"
                elif change == "seed":changed["case"]["seed"] = 456
                else:changed["config"]["optimization"]["train_backbone"] = True
                with self.subTest(change=change), self.assertRaises(ValueError):
                    verify_training_report(trained, changed, events, frozen_backbone=True)

    def test_frozen_coverage_selection_and_actual_component_policy_are_required(self):
        for change in ("body_gradient", "head_gradient", "body_mode", "body_trainability", "head_mode", "missing_epoch", "missing_validation", "best"):
            with self.subTest(change=change), full_fixture() as (_, trained, gate, events, _):
                if change == "body_gradient":trained["backbone_gradient_norms"][1] = .1
                elif change == "head_gradient":trained["gradient_norms"][1] = 0.
                elif change == "body_mode":trained["components_during_training"]["backbone"]["module_modes"]["train"] = 1
                elif change == "body_trainability":trained["components"]["backbone"]["trainable_parameters"] = 1
                elif change == "head_mode":trained["components_during_training"]["readout"]["mode"] = "eval"
                elif change == "missing_epoch":events.pop()
                elif change == "missing_validation":events[0]["structures"] = 1
                else:trained["heldout"]["selection"]["tracker"]["best_epoch"] = 1
                with self.assertRaises(ValueError):frozen.verify_frozen_training(trained, gate, events)

    def test_training_audit_rejects_corruption_even_when_outer_hash_is_updated(self):
        for change in ("steps", "checks", "body", "initial_body", "readout", "best_body", "last_head", "best_head", "optimizer", "source", "delegate", "policy", "checkpoint_bytes"):
            with self.subTest(change=change), full_fixture() as (root, trained, gate, events, observed):
                if change == "steps":observed["optimizer"]["optimizer_steps"] -= 1
                elif change == "checks":observed["optimizer"]["guard_checks"] -= 1
                elif change == "body":observed["optimizer"]["backbone_state_after_sha256"] = "f" * 64
                elif change == "initial_body":gate["frozen_audit"]["backbone_state_before_sha256"] = "f" * 64
                elif change == "readout":observed["optimizer"]["readout_parameters_after_sha256"] = observed["optimizer"]["readout_parameters_before_sha256"]
                elif change == "best_body":observed["checkpoints"]["best"]["backbone_state_sha256"] = "f" * 64
                elif change == "last_head":observed["checkpoints"]["last"]["readout_parameters_sha256"] = "f" * 64
                elif change == "best_head":observed["checkpoints"]["best"]["readout_parameters_sha256"] = None
                elif change == "optimizer":observed["checkpoints"]["best"]["optimizer_groups"].append(dict(name="backbone"))
                elif change == "source":observed["source_sha256"]["src/universal_gnn/engine/training.py"] = "f" * 64
                elif change == "delegate":observed["actual_training_delegate"] = "different.py"
                elif change == "policy":observed["checkpoints"]["best"]["policy"] = dict(train_backbone=True)
                else:Path(trained["checkpoint"]).write_bytes(b"corrupt")
                path = root / "frozen-training-audit.json";write(path, observed)
                trained["frozen_training_audit"]["sha256"] = file_sha(path)
                with self.assertRaises(ValueError):frozen.verify_frozen_training(trained, gate, events)

    def test_independent_gate_is_fully_rebuilt_and_mismatches_refused(self):
        with full_fixture() as (root, _, gate, _, _), ExitStack() as stack:
            case = gate["case"];path = root / "independent.json";write(path, gate)
            stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}))
            stack.enter_context(patch.object(frozen.sys, "prefix", "/env/universal-official"))
            stack.enter_context(patch.object(frozen, "execution_spec", return_value=dict(case=case)))
            stack.enter_context(patch.object(frozen, "compatible_sources", return_value="b" * 40))
            replay = stack.enter_context(patch.object(frozen, "check_frozen_preparation", return_value=dict(gate, git_commit="b" * 40)))
            result = frozen.checked_execution_gate({}, case["id"], gate["preparation"], path, budget_seconds=1000.)
            self.assertEqual(result["independent_frozen_gate"]["sha256"], file_sha(path))
            self.assertEqual(replay.call_count, 1)
            for change in ("case", "budget", "recipe", "cuda"):
                saved = copy.deepcopy(gate)
                if change == "case":saved["case"]["id"] += "bad"
                elif change == "budget":saved["budget_seconds"] = 1.
                elif change == "recipe":saved["config"]["batch_size"] = 1
                else:saved["status"] = "failed"
                write(path, saved)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    frozen.checked_execution_gate({}, case["id"], gate["preparation"], path, budget_seconds=1000.)

    def test_login_and_duplicate_outputs_cannot_start_frozen_training(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):frozen.run_frozen_case({}, "bad", "prep", "gate", budget_seconds=10)
            with self.assertRaises(RuntimeError):frozen.frozen_context({}, "bad")
            with self.assertRaises(RuntimeError):audit.audited_training({}, "unused")
        with full_fixture() as (root, _, gate, _, _), patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), \
                patch.object(frozen, "execution_spec", return_value=dict(case=gate["case"])), \
                patch.object(frozen, "checked_execution_gate") as checker:
            with self.assertRaises(FileExistsError):frozen.run_frozen_case({}, gate["case"]["id"], "prep", "gate", budget_seconds=10)
            checker.assert_not_called()

    def test_actual_execution_hooks_retain_shared_executor_and_frozen_verifier(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), ExitStack() as stack:
            root = Path(folder) / "new"
            stack.enter_context(patch.object(frozen, "execution_spec", return_value=dict(case=dict(run_directory=str(root)))))
            gate = dict(fixture=True)
            stack.enter_context(patch.object(frozen, "checked_execution_gate", return_value=gate))
            execute = stack.enter_context(patch.object(frozen, "_run_prepared_case", return_value=dict(status="fixture")))
            frozen.run_frozen_case({}, "fixture", "prep", "gate", budget_seconds=10)
            execute.assert_called_once_with("fixture", gate, budget_seconds=10,
                training_executor=audit.audited_training, report_verifier=frozen.verify_frozen_training)

    def test_frozen_physics_uses_original_reference_probe_including_legacy_path(self):
        with full_fixture() as (root, trained, gate, _, _):
            probe = root / "original-scan/probe.json";write(probe, dict(worst_indices=[0, 2]))
            write(root / "reference/report.json", dict(graph_scan_path=str(probe.parent)))
            write(root / "prep/report.json", dict(reference_preparation=gate["reference_preparation"]))
            selection = runtime.physical_selection(dict(gate=gate, trained=trained))
            self.assertEqual(selection["ids"], ["fixture-0", "fixture-2"])
            self.assertEqual(selection["probe_sha256"], file_sha(probe))
            write(root / "prep/report.json", dict(reference_preparation="wrong"))
            with self.assertRaises(ValueError):runtime.physical_selection(dict(gate=gate, trained=trained))

    def test_complete_frozen_context_replays_training_and_binds_all_inputs(self):
        with full_fixture() as (root, trained, gate, events, _), ExitStack() as stack:
            definitions, primary = root / "definitions.json", root / "primary.json"
            settings = dict(definitions=str(definitions), primary_matrix=str(primary))
            for path in (definitions, primary, root / "prep/report.json", root / "reference/report.json"):
                write(path, dict(fixture=True))
            independent = root / "independent.json";write(independent, gate)
            gate.update(independent_frozen_gate=dict(path=str(independent), sha256=file_sha(independent)),
                        execution_definitions=str(definitions), execution_primary_matrix=str(primary))
            trained["execution"]["slurm"] = dict(SLURM_JOB_ID="123")
            verified = frozen.verify_frozen_training(trained, gate, events)
            formal = dict(status="passed", stage="complete", formal_training_runs_completed=1,
                case_id=gate["case"]["id"], matrix_sha256=DEFINITION_SHA, counts=gate["counts"],
                slurm_job_id="123", git_commit="a" * 40, **verified,
                **{k: gate["case"][k] for k in ("model", "task", "seed", "initialization")})
            for path, value in ((root / "formal-status.json", formal), (root / "report.json", trained),
                                (root / "execution-gate.json", gate), (root / "config.requested.json", gate["config"])):
                write(path, value)
            jsonl(root / "events.jsonl", events)
            spec = dict(case=gate["case"], counts=gate["counts"])
            stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}))
            stack.enter_context(patch.object(frozen.sys, "prefix", "/env/universal-official"))
            stack.enter_context(patch.object(frozen, "execution_spec", return_value=spec))
            replay = stack.enter_context(patch.object(frozen, "checked_execution_gate", return_value=copy.deepcopy(gate)))
            stack.enter_context(patch.object(frozen, "compatible_sources", return_value="a" * 40))
            context = frozen.frozen_context(settings, gate["case"]["id"])
            self.assertEqual(context["verified_training"], verified)
            self.assertEqual(context["spec"]["matrix_sha256"], DEFINITION_SHA)
            self.assertIn(str(root / "frozen-training-audit.json"), context["input_sha256"])
            self.assertIn(str(independent), context["input_sha256"])
            for change in ("job", "epochs", "audit", "recipe", "original_gate"):
                fresh = copy.deepcopy(formal)
                if change == "job":fresh["slurm_job_id"] = "456"
                elif change == "epochs":fresh["completed_epochs"] -= 1
                elif change == "audit":fresh["frozen_training"]["optimizer_steps"] -= 1
                elif change == "recipe":write(root / "config.requested.json", dict(changed=True))
                else:replay.return_value["config"]["batch_size"] = 1
                write(root / "formal-status.json", fresh)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    frozen.frozen_context(settings, gate["case"]["id"])
                write(root / "config.requested.json", gate["config"])

    def test_shared_post_then_no_model_verification_keep_frozen_physics_and_full_outputs(self):
        for task in ("forcefield", "dielectric"):
            with self.subTest(task=task), helpers["fixture"](task) as (root, path, trained, _), ExitStack() as stack:
                context = helpers["PredictionAssessmentTests"].mock_context(path, trained, task)
                context["gate"]["kind"] = "formal_frozen_backbone_execution_gate"
                physics = helpers["physics_fixture"](task, ["0", "1"])
                physics["mixed_parameter_gradient_norms"]["backbone"] = 0.
                stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}))
                stack.enter_context(patch.object(frozen, "frozen_context", return_value=context))
                stack.enter_context(patch.object(runtime, "compatible_sources", return_value="a" * 40))
                stack.enter_context(patch.object(runtime, "physical_selection", return_value=dict(indices=[0, 1], ids=["0", "1"])))
                stack.enter_context(patch.object(runtime.numerics, "peak_rss_bytes", return_value=1024))
                stack.enter_context(patch.object(runtime.numerics, "forbid_models", side_effect=nullcontext))
                physical = stack.enter_context(patch.object(runtime.numerics, "trained_physics", return_value=physics))
                def inferred(checkpoint, config, output):
                    jsonl(output, helpers["stream_rows"](trained));return dict(streamed=True, structure_count=5)
                infer = stack.enter_context(patch.object(runtime.numerics, "complete_inference", side_effect=inferred))
                frozen.postprocess_frozen_case({}, "fixture", root / "post")
                physical.reset_mock();infer.reset_mock()
                result = frozen.verify_frozen_case({}, "fixture", root / "post", root / "verify")
                self.assertEqual(result["status"], "passed")
                self.assertTrue(result["model_execution_forbidden"])
                self.assertEqual(result["inference_verification"]["structures"], 5)
                physical.assert_not_called();infer.assert_not_called()
                physics["mixed_parameter_gradient_norms"]["backbone"] = .1
                with self.assertRaises(ValueError):runtime._verify_context_physics(context, physics, dict(ids=["0", "1"]))


if __name__ == "__main__":
    unittest.main()
