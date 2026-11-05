"""Pure frozen-readiness protocol fixtures, not numerical readiness evidence."""

import copy
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.execution.gates import canonical_digest, file_sha
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.frozen_backbones import definitions as definitions_module
from universal_gnn.benchmarks.frozen_backbones import contracts, readiness, worker
from universal_gnn.benchmarks.prediction_assessment.runtime import verify_physics

HERE = Path(__file__).parent
registry_fixture = runpy.run_path(str(HERE / "test_arxiv_experiment_definitions.py"))["registry_fixture"]
physics_fixture = runpy.run_path(str(HERE / "test_prediction_assessment.py"))["physics_fixture"]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf8")


@contextmanager
def definitions_fixture():
    primary = build_matrix(registry_fixture())
    with patch.object(definitions_module, "PRIMARY_SHA", canonical_digest(primary)):
        definitions = definitions_module.build_frozen_definitions(primary)
        yield primary, definitions


def audit_fixture(steps=102):
    return dict(protocol=worker.PROTOCOL, optimizer_steps=steps, guard_checks=2 * steps + 2,
        backbone_optimizer_parameters=0, backbone_requires_grad_parameters=0,
        backbone_gradients_absent=True, frozen_modules_eval=True, state_exact_after_every_step=True,
        readout_parameters_changed=True, changed_optimizer_arithmetic=False, changed_rng=False,
        instrumentation_source_sha256=file_sha(Path(worker.__file__)),
        delegate_source_sha256=file_sha(Path(worker.probe_worker.__file__)),
        backbone_state_before_sha256="a" * 64, backbone_state_after_sha256="a" * 64,
        readout_state_before_sha256="b" * 64, readout_state_after_sha256="c" * 64,
        readout_parameters_before_sha256="d" * 64, readout_parameters_after_sha256="e" * 64,
        optimizer_groups=["readout"], minimum_readout_gradient_norm=.1, maximum_readout_gradient_norm=.2)


@contextmanager
def capacity_fixture():
    with tempfile.TemporaryDirectory() as folder, definitions_fixture() as (primary, definitions):
        root = Path(folder)
        case = definitions["cases"][0]
        config = copy.deepcopy(case["config"])
        probe = dict(indices=[0, 1, 2], worst_indices=[0, 1], warmup_batches=2, measure_batches=100,
                     coverage=dict(verified_full_training_scan=True, structures=3))
        sample = dict(version=1, status="passed", stage="complete", phase="train", batch_size=4,
            selected_training_structures=3, measured_batches=100, measured_structures=400,
            coverage=probe["coverage"], completed_worst_indices=[0, 1], all_declared_worst_cases_completed=True,
            worst_case_policy="homogeneous_full_batch_v1", elapsed_seconds=10., frozen_audit=audit_fixture())
        path = root / "attempt-01-b4"
        write(path / "request.json", dict(config=config, probe=probe, phase="train"))
        write(path / "result.json", sample)
        report = dict(version=1, status="passed", passed=True, phase="train", config=config, probe=probe,
            initial_batch_size=4, final_batch_size=4, effective_batch_size=4, gradient_accumulation_steps=1,
            attempts=[dict(directory=str(path), batch_size=4, status="passed", returncode=0, worker=sample)])
        write(root / "report.json", report)
        yield dict(root=root, primary=primary, definitions=definitions, case=case, config=config, probe=probe,
                   worker=sample, report=report, counts=dict(train=3, validation=1, test=1))


def physics(task="forcefield", device="cuda:0"):
    result = physics_fixture(task, ["first", "second"])
    result["device"] = device
    result["mixed_parameter_gradient_norms"]["backbone"] = 0.
    result["frozen_state"] = dict(backbone_state_before_sha256="a" * 64, backbone_state_after_sha256="a" * 64,
                                 backbone_gradients_absent=True, frozen_modules_eval=True)
    return result


@contextmanager
def readiness_fixture():
    with capacity_fixture() as f, ExitStack() as stack:
        before = Path.cwd();os.chdir(f["root"]);stack.callback(os.chdir, before)
        config = f["config"];counts = f["counts"];case = copy.deepcopy(f["case"])
        case.update(counts=counts, source_structures=5)
        spec = dict(case=case, config=config, counts=counts, source_structures=5, primary_sha256="a" * 64)
        reference_config = copy.deepcopy(config);reference_config["optimization"]["train_backbone"] = True
        reference = dict(status="passed", git_commit="a" * 40, config=reference_config,
                         backbone_cutoff=8., case=dict(id=case["reference_finetune_case"]))
        probe = f["probe"]
        probe["coverage"]["graph_definition"] = dict(artifact_sha256=dict(checkpoint="f" * 64))
        matrix = dict(registry=dict(artifacts={case["model"]: dict(files={"fixture.bin": dict(sha256="f" * 64)})}))
        execution = dict(git_commit="a" * 40, official=dict(initialization="pretrained", parameter_coverage=1., sha256=dict(checkpoint="f" * 64)))
        sample = f["worker"];sample.update(execution=execution, versions=dict(torch="fixture"))
        prep = f["root"] / "prepared";cap = prep / "capacity"
        report = f["report"];report["attempts"][0]["directory"] = str(cap / "attempt-01-b4")
        write(cap / "report.json", report)
        write(cap / "attempt-01-b4/result.json", sample)
        write(cap / "attempt-01-b4/request.json", dict(config=config, probe=probe, phase="train"))
        manifest = dict(records=[dict(id=name) for name in ["first", "second", "third", "val", "test"]], partitions=dict(train=[0, 1, 2]))
        write(Path(config["dataset"]["split_manifest"]), manifest)
        definitions = f["root"] / "definitions.json";inputs = dict(fixture_complete_input_audit=True)
        write(definitions, dict(full_input_audit=inputs))
        value = physics("dielectric");value["execution"] = execution
        for name, data in [("physics.json", value), ("full-input-audit.json", inputs), ("config.requested.json", config), ("reference-gate.json", reference)]:
            write(prep / name, data)
        prepared = dict(kind="full_frozen_backbone_preparation", status="passed", stage="complete", case_id=case["id"],
            definition_sha256=contracts.DEFINITION_SHA, frozen_training_ready=True, cuda_acceptance=True,
            gpu_allocation=dict(gpus=1, evidence="AllocTRES", node_list="fixture-node"),
            formal_training_runs=0, formal_training_launched=False, counts=counts, source_structures=5,
            reference_preparation="source-bound-original-reference", git_commit="a" * 40,
            reference_gate_sha256=file_sha(prep / "reference-gate.json"), input_audit_sha256=file_sha(prep / "full-input-audit.json"),
            physics_sha256=file_sha(prep / "physics.json"), config_sha256=file_sha(prep / "config.requested.json"),
            capacity_sha256=file_sha(cap / "report.json"), probed_train_only_seconds=30., matched_reference_batch=4)
        write(prep / "report.json", prepared)
        stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}))
        stack.enter_context(patch.object(readiness, "selected_case", return_value=spec))
        stack.enter_context(patch.object(readiness, "reference_context", return_value=(matrix, reference, config, probe)))
        stack.enter_context(patch.object(readiness, "installed_versions", return_value=dict(torch="fixture")))
        stack.enter_context(patch.object(readiness, "compatible_sources", return_value="a" * 40))
        yield dict(prep=prep, definitions=definitions, case=case, config=config, report=prepared, physics=value)


class FrozenReadinessTests(unittest.TestCase):
    def test_independent_gate_requires_own_frozen_capacity_physics_and_matched_reference(self):
        with readiness_fixture() as f:
            result = readiness.check_frozen_preparation(f["case"]["id"], f["prep"], definitions=f["definitions"], budget_seconds=100)
            self.assertEqual(result["kind"], "formal_frozen_backbone_execution_gate")
            self.assertFalse(result["config"]["optimization"]["train_backbone"])
            self.assertEqual(result["frozen_audit"]["optimizer_steps"], 102)
            self.assertEqual(result["common_batch_size"], 4)

    def test_independent_gate_refuses_unfinished_cuda_fingerprint_policy_source_and_budget_tampering(self):
        for mutation in ("unfinished", "allocation", "cuda", "bytes", "physics", "artifact", "versions", "matched_batch", "budget"):
            with self.subTest(mutation=mutation), readiness_fixture() as f, ExitStack() as stack:
                budget = 100
                if mutation == "unfinished":f["report"]["stage"] = "frozen_capacity"
                elif mutation == "allocation":f["report"]["gpu_allocation"]["gpus"] = 0
                elif mutation == "cuda":f["report"]["cuda_acceptance"] = False
                elif mutation == "bytes":
                    (f["prep"] / "config.requested.json").write_text("{}")
                elif mutation == "physics":
                    f["physics"]["mixed_parameter_gradient_norms"]["backbone"] = 1.
                    write(f["prep"] / "physics.json", f["physics"])
                    f["report"]["physics_sha256"] = file_sha(f["prep"] / "physics.json")
                elif mutation == "artifact":
                    f["physics"]["execution"]["official"]["parameter_coverage"] = .5
                    write(f["prep"] / "physics.json", f["physics"])
                    f["report"]["physics_sha256"] = file_sha(f["prep"] / "physics.json")
                elif mutation == "versions":
                    stack.enter_context(patch.object(readiness, "installed_versions", return_value=dict(torch="changed")))
                elif mutation == "matched_batch":
                    f["report"]["matched_reference_batch"] = 2
                else:budget = 1
                write(f["prep"] / "report.json", f["report"])
                with self.assertRaises(ValueError):
                    readiness.check_frozen_preparation(f["case"]["id"], f["prep"], definitions=f["definitions"], budget_seconds=budget)

    def test_eight_closed_cases_preserve_exact_original_recipes_and_scope(self):
        with definitions_fixture() as (primary, definitions):
            for case in definitions["cases"]:
                spec = contracts.frozen_case_spec(primary, definitions, case["id"])
                self.assertEqual(spec["case"], case)
                self.assertFalse(spec["config"]["optimization"]["train_backbone"])
                self.assertEqual(spec["config"]["seed"], 123)
                worker.check_request(dict(config=spec["config"], phase="train"))
            for identifier in ["seed-123--forcefield--mace--pretrained", "frozen--seed-456--forcefield--mace", "unknown"]:
                with self.assertRaises(ValueError):
                    contracts.frozen_case_spec(primary, definitions, identifier)

    def test_changed_definitions_or_reference_recipe_are_rejected(self):
        with definitions_fixture() as (primary, definitions):
            case = definitions["cases"][0]
            bad = copy.deepcopy(definitions);bad["cases"][0]["config"]["epochs"] = 3
            with self.assertRaises(ValueError):
                contracts.frozen_case_spec(primary, bad, case["id"])
            spec = contracts.frozen_case_spec(primary, definitions, case["id"])
            config = copy.deepcopy(case["config"]);config["optimization"]["train_backbone"] = True
            reference = dict(status="passed", case=dict(id=case["reference_finetune_case"]), config=config,
                counts=spec["counts"], source_structures=spec["source_structures"], matrix_sha256=spec["primary_sha256"], common_batch_size=4)
            self.assertEqual(contracts.frozen_config(spec, reference), case["config"])
            reference["config"]["prediction"]["head_mode"] = "native"
            with self.assertRaises(ValueError):
                contracts.frozen_config(spec, reference)

    def test_worker_refuses_partial_sources_other_policies_or_generation_before_torch(self):
        with definitions_fixture() as (_, definitions):
            config = definitions["cases"][0]["config"]
            changes = [("structures", 10), ("max_atoms", 5), ("dtype", "float64"), ("seed", 456), ("device", "cpu")]
            for key, value in changes:
                bad = copy.deepcopy(config);bad[key] = value
                with self.assertRaises(ValueError):worker.check_request(dict(config=bad, phase="train"))
            for section, key, value in [("optimization", "train_backbone", True), ("optimization", "train_readout", False),
                                       ("backbone", "initialization", "scratch"), ("prediction", "head_mode", "native")]:
                bad = copy.deepcopy(config);bad[section][key] = value
                with self.assertRaises(ValueError):worker.check_request(dict(config=bad, phase="train"))
            with self.assertRaises(ValueError):worker.check_request(dict(config=config, phase="sample"))

    def test_frozen_audit_requires_exact_state_and_every_step_guard(self):
        audit = audit_fixture()
        args = dict(instrumentation_sha256=audit["instrumentation_source_sha256"], delegate_sha256=audit["delegate_source_sha256"])
        self.assertEqual(contracts.checked_audit(audit, 102, **args), audit)
        for key, value in [("optimizer_steps", 101), ("guard_checks", 204), ("backbone_optimizer_parameters", 1),
                ("backbone_requires_grad_parameters", 1), ("backbone_gradients_absent", False), ("frozen_modules_eval", False),
                ("state_exact_after_every_step", False), ("backbone_state_after_sha256", "f" * 64),
                ("readout_parameters_after_sha256", audit["readout_parameters_before_sha256"]),
                ("minimum_readout_gradient_norm", 0.), ("maximum_readout_gradient_norm", float("inf")),
                ("optimizer_groups", ["backbone", "readout"]), ("changed_rng", True),
                ("instrumentation_source_sha256", "f" * 64), ("delegate_source_sha256", "f" * 64)]:
            changed = dict(audit, **{key: value})
            with self.subTest(field=key), self.assertRaises(ValueError):
                contracts.checked_audit(changed, 102, **args)

    def test_complete_single_frozen_capacity_is_not_a_fake_initialization_pair(self):
        with capacity_fixture() as f:
            result = contracts.frozen_capacity(f["root"], f["config"], f["probe"], f["counts"])
            self.assertEqual(result["common_batch_size"], 4)
            self.assertEqual(result["worker"]["frozen_audit"]["optimizer_steps"], 102)
            self.assertEqual(result["seconds_per_batch"], .1)

    def test_capacity_rejects_truncated_batches_wrong_worst_coverage_or_source(self):
        for key, value in [("selected_training_structures", 2), ("measured_batches", 99), ("measured_structures", 396),
                ("completed_worst_indices", [0]), ("worst_case_policy", "single_worst"), ("elapsed_seconds", float("nan")),
                ("phase", "sample"), ("status", "cuda_oom")]:
            with capacity_fixture() as f:
                f["worker"][key] = value
                write(f["root"] / "attempt-01-b4/result.json", f["worker"])
                write(f["root"] / "report.json", f["report"])
                with self.assertRaises(ValueError):
                    contracts.frozen_capacity(f["root"], f["config"], f["probe"], f["counts"])

    def test_preflight_cannot_silently_shrink_reference_batch_or_change_request(self):
        for mutation in ("batch", "request", "worker", "attempts"):
            with capacity_fixture() as f:
                if mutation == "batch":f["report"]["final_batch_size"] = 2
                elif mutation == "request":
                    write(f["root"] / "attempt-01-b4/request.json", dict(config={}, probe=f["probe"], phase="train"))
                elif mutation == "worker":
                    changed = dict(f["worker"], stage="interrupted");write(f["root"] / "attempt-01-b4/result.json", changed)
                else:f["report"]["attempts"].append(copy.deepcopy(f["report"]["attempts"][0]))
                write(f["root"] / "report.json", f["report"])
                with self.assertRaises(ValueError):
                    contracts.frozen_capacity(f["root"], f["config"], f["probe"], f["counts"])

    def test_frozen_physics_uses_zero_body_gradients_and_preserves_default_positive_policy(self):
        for task in ("forcefield", "dielectric"):
            value = physics(task, device="cpu")
            with self.assertRaises(ValueError):verify_physics(value, task, dict(ids=["first", "second"]))
            verify_physics(value, task, dict(ids=["first", "second"]), frozen_backbone=True)
            value["device"] = "cuda:0"
            self.assertEqual(readiness.frozen_physics(value, dict(task=task), ["first", "second"], device="cuda:0"), value["frozen_state"])

    def test_frozen_physics_rejects_cpu_as_cuda_changed_state_modes_or_tolerances(self):
        for mutation in ("cpu", "state", "mode", "gradients", "body_gradient", "head_gradient", "tolerance", "ids"):
            value = physics()
            if mutation == "cpu":value["device"] = "cpu"
            elif mutation == "state":value["frozen_state"]["backbone_state_after_sha256"] = "b" * 64
            elif mutation == "mode":value["frozen_state"]["frozen_modules_eval"] = False
            elif mutation == "gradients":value["frozen_state"]["backbone_gradients_absent"] = False
            elif mutation == "body_gradient":value["mixed_parameter_gradient_norms"]["backbone"] = 1.
            elif mutation == "head_gradient":value["mixed_parameter_gradient_norms"]["readout"] = 0.
            elif mutation == "tolerance":value["checks"]["forces_finite_difference"]["atol"] = 1.
            else:value["structure_ids"] = ["first", "wrong"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                readiness.frozen_physics(value, dict(task="forcefield"), ["first", "second"], device="cuda:0")

    def test_login_guards_run_before_source_reads_or_model_imports(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):readiness.prepare_frozen_case("unknown", "none", "none")
            with self.assertRaises(RuntimeError):readiness.check_frozen_preparation("unknown", "none")
            with self.assertRaises(RuntimeError):worker.main()


if __name__ == "__main__":unittest.main()
