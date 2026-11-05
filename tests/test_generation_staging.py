"""Staging preserves complete evidence and every attempted sample, without Torch."""

import copy
from contextlib import contextmanager, ExitStack
import json
import math
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.execution import gates
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.generation import staging
from universal_gnn.benchmarks.generation import sampling_failures
from universal_gnn.benchmarks.generation.sampling_failures import (
    image_budget_failure, invalid_geometry_attempts, checked_untrained_sampling_failure, sampling_policy)

HERE = Path(__file__).parent
registry_fixture = runpy.run_path(str(HERE / "test_arxiv_experiment_definitions.py"))["registry_fixture"]
shared_evidence = runpy.run_path(str(HERE / "test_tensor_preparation_gate.py"))["shared_evidence"]
generation_fixture = runpy.run_path(str(HERE / "test_generation_execution.py"))["generation_fixture"]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf8")


def failed_sample(root, mode="scratch", error_type="ValueError", message="Cell requires 51129 periodic images; check cell/cutoff"):
    path = root / "sample-capacity" / "individual" / mode / "report.json"
    worker = dict(status="failed", phase="sample", stage="sample", error_type=error_type, error=message)
    trial = dict(status="failed", passed=False, phase="sample", attempts=[dict(status="failed", worker=worker)])
    write(path, trial)
    report = dict(status="failed", passed=False, phase="sample", failed_stage="individual", failed_initialization=mode,
                  trials=[dict(stage="individual", initialization=mode, passed=False, directory=str(path.parent), report_sha256=canonical_digest(trial))])
    write(root / "sample-capacity/report.json", report)
    return path, report


@contextmanager
def failed_source_receipts():
    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
        before = Path.cwd();os.chdir(folder);stack.callback(os.chdir, before)
        commit = "a" * 40;provider = "mace";job = "1022"
        claim = Path("runs/full-generation-preparations-aaaaaaa-claim")
        source = Path("runs/source-checkouts") / commit;source.mkdir(parents=True)
        path = Path("runs/arxiv-v1/full-generation-preparation-1022-mace");path.mkdir(parents=True)
        claim.mkdir();request = claim / "mace.sh";request.write_bytes(b"original request")
        control_request = claim / "control.sh";control_request.write_bytes(b"original control")
        control_path = Path("runs/generation-preparation-control-1019/report.json")
        control = dict(status="passed", git_commit=commit, slurm_job_id="1019", main_test_cases=8)
        write(control_path, control)
        entry = dict(job=job, git_commit=commit, status="submitted_preparation_only", formal_training_runs=0,
                     source_checkout=str(source.resolve()), request_path=str(request), request_sha256=gates.file_sha(request))
        receipts = dict(preparations={provider: entry}, control=dict(job="1019", git_commit=commit,
            source_checkout=str(source.resolve()), request_sha256=gates.file_sha(control_request)))
        write(claim / "jobs.json", receipts)
        stack.enter_context(patch.object(sampling_failures.subprocess, "check_output",
            side_effect=lambda args, **kwargs: commit + "\n" if args[-1] == "HEAD" else ""))
        yield dict(path=path, prepared=dict(slurm_job_id=job), commit=commit, provider=provider,
                   claim=claim, receipts=receipts, request=request, control_path=control_path, control=control)


@contextmanager
def training_evidence():
    """Use full raw-source/graph evidence fixtures and real config/prior validators."""
    with shared_evidence() as f:
        spec, root = f["spec"], f["prepared"]
        spec.pop("definition_kind")
        spec["case"]["task"] = "generation"
        prior = dict(sampling_volume_source="train_fit", statistics=dict(version=1, kind="train_log_volume_per_atom_v1",
            fitted_partition="train", structures=3, unit="angstrom^3/atom", training_fingerprint="a" * 64,
            volume_per_atom=8., log_volume_per_atom_mean=math.log(8.), log_volume_per_atom_std=.1))
        for config in spec["configs"].values():
            config["task"] = dict(kind="generation", sampling=dict(steps=100, inner_steps=2))
        capacity = root / "train-capacity"
        f["cap"]["input_config_sha256"] = {k: canonical_digest(v) for k, v in spec["configs"].items()}
        for mode, expected in spec["configs"].items():
            resolved = copy.deepcopy(expected)
            resolved["generation_prior"] = prior
            resolved["task"]["sampling"]["volume_per_atom"] = 8.
            write(capacity / ("config." + mode + ".resolved.json"), resolved)
            f["cap"]["resolved_config_sha256"][mode] = canonical_digest(resolved)
        write(capacity / "report.json", f["cap"])
        for worker in f["workers"]:
            worker["resolved_generation"] = dict(generation_prior=prior)
        f["report"].update(kind="full_generation_pair_preparation", status="failed", stage="paired_sampling_capacity",
                           matrix_sha256=spec["matrix_sha256"], training_batch_size=4, training_prior=prior)
        write(root / "report.json", f["report"])
        failed_sample(root)
        definition = dict(quality=dict(samples=1000, draws_per_condition=5, seed=456), sampling_preflight={})
        with patch("universal_gnn.benchmarks.generation.preparation.generation_spec", return_value=definition):
            yield f


class GenerationStagingTests(unittest.TestCase):
    def test_missing_success_only_source_stamp_requires_exact_original_receipts(self):
        with failed_source_receipts() as f:
            proof = sampling_failures.checked_failed_preparation_source(f["path"], f["prepared"], f["commit"], f["provider"], graph_job="1022")
            self.assertEqual(proof["git_commit"], f["commit"])
            self.assertEqual(proof["original_job"], "1022")
            self.assertEqual(proof["request_sha256"], gates.file_sha(f["request"]))
            self.assertEqual(proof["control_report_sha256"], gates.file_sha(f["control_path"]))

    def test_failed_source_receipt_job_graph_request_control_and_git_tampering_refuse(self):
        for mutation in ("job", "graph_job", "request", "control", "git", "missing"):
            with self.subTest(mutation=mutation), failed_source_receipts() as f:
                graph_job = "1022"
                if mutation == "job":
                    f["prepared"]["slurm_job_id"] = "1020"
                elif mutation == "graph_job":
                    graph_job = "1020"
                elif mutation == "request":
                    f["request"].write_bytes(b"changed request")
                elif mutation == "control":
                    f["control"]["status"] = "failed";write(f["control_path"], f["control"])
                elif mutation == "git":
                    sampling_failures.subprocess.check_output.side_effect = lambda *a, **kw: "b" * 40
                else:
                    (f["claim"] / "jobs.json").unlink()
                with self.assertRaises((ValueError, FileNotFoundError)):
                    sampling_failures.checked_failed_preparation_source(f["path"], f["prepared"], f["commit"], f["provider"], graph_job=graph_job)

    def test_training_gate_retains_verified_original_source_when_parent_stamp_missing(self):
        with training_evidence() as f:
            f["report"].pop("git_commit");write(f["prepared"] / "report.json", f["report"])
            proof = dict(git_commit="a" * 40, original_job="fixture", request_sha256="b" * 64)
            with patch.object(sampling_failures, "checked_failed_preparation_source", return_value=proof) as check:
                result = gates._check_prepared_spec(f["matrix"], f["spec"], f["prepared"], budget_seconds=10000, generation_training_only=True)
            self.assertEqual(result["preparation_source_proof"], proof)
            self.assertTrue(result["training_readiness_only"])
            self.assertEqual(check.call_count, 1)

    def test_only_exact_known_periodic_guard_is_adapted(self):
        self.assertTrue(image_budget_failure("ValueError", "Cell requires 51129 periodic images; check cell/cutoff"))
        for kind, message in [("RuntimeError", "Cell requires 51129 periodic images; check cell/cutoff"),
                ("ValueError", "CUDA out of memory"), ("ValueError", "Cell requires 0 periodic images; check cell/cutoff"),
                ("ValueError", "Cell requires 51129 periodic images; check cell/cutoff extra")]:
            self.assertFalse(image_budget_failure(kind, message))

    def test_success_arguments_result_identity_state_and_method_restoration(self):
        token = object()
        class Denoiser:
            def sample(self, *args, **kwargs):
                self.call = (args, kwargs)
                return token
        original = Denoiser.sample
        model = Denoiser()
        with invalid_geometry_attempts(Denoiser):
            self.assertIs(model.sample("batch", seed=456, steps=100, inner_steps=2), token)
            self.assertEqual(model.call, (("batch",), dict(seed=456, steps=100, inner_steps=2)))
        self.assertIs(Denoiser.sample, original)
        policy = sampling_policy()
        for key in ("changed_sampling_arithmetic", "changed_rng", "changed_steps"):
            self.assertIs(policy[key], False)

    def test_known_invalid_attempt_but_unknown_and_oom_propagate_and_restore(self):
        class OutOfMemoryError(RuntimeError):
            pass
        errors = [ValueError("Cell requires 51129 periodic images; check cell/cutoff"), ValueError("bad shape"),
                  RuntimeError("unexpected failure"), OutOfMemoryError("CUDA out of memory"), FloatingPointError("Nonfinite node output")]
        for error in errors:
            class Denoiser:
                def sample(self):
                    raise error
            original = Denoiser.sample
            with self.assertRaises(FloatingPointError if error is errors[0] else type(error)) as caught:
                with invalid_geometry_attempts(Denoiser):
                    Denoiser().sample()
            self.assertIs(Denoiser.sample, original)
            if error is errors[0]:
                self.assertIs(caught.exception.__cause__, error)
            else:
                self.assertIs(caught.exception, error)

    def test_failed_sampler_bound_to_exact_trial_bytes_and_known_non_oom(self):
        for mode, kind, message in [("scratch", "ValueError", "Cell requires 51129 periodic images; check cell/cutoff"),
                                   ("pretrained", "FloatingPointError", "Nonfinite node output")]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                path, _ = failed_sample(root, mode, kind, message)
                proof = checked_untrained_sampling_failure(root)
                self.assertFalse(proof["sampling_capacity_passed"])
                self.assertEqual(proof["initialization"], mode)
                changed = json.loads(path.read_text())
                changed["attempts"][-1]["worker"]["error"] += " changed"
                write(path, changed)
                with self.assertRaises(ValueError):
                    checked_untrained_sampling_failure(root)
        for kind, message in [("OutOfMemoryError", "CUDA out of memory"), ("RuntimeError", "unknown"),
                              ("FloatingPointError", "not a known geometry error")]:
            with tempfile.TemporaryDirectory() as folder:
                failed_sample(Path(folder), error_type=kind, message=message)
                with self.assertRaises(ValueError):
                    checked_untrained_sampling_failure(folder)

    def test_complete_training_evidence_is_separate_from_strict_full_preparation(self):
        with training_evidence() as f:
            kwargs = dict(budget_seconds=10000)
            with self.assertRaises(ValueError):
                gates._check_prepared_spec(f["matrix"], f["spec"], f["prepared"], **kwargs)
            result = gates._check_prepared_spec(f["matrix"], f["spec"], f["prepared"], generation_training_only=True, **kwargs)
            self.assertEqual(result["kind"], "formal_generation_training_execution_gate")
            self.assertTrue(result["training_readiness_only"])
            self.assertFalse(result["sampling_readiness"]["sampling_capacity_passed"])
            self.assertFalse(result["generation_quality_complete"])
            self.assertNotIn("probed_sample_batch_seconds", result)
            self.assertEqual(json.loads((f["prepared"] / "report.json").read_text())["status"], "failed")

    def test_training_only_does_not_bypass_raw_graph_config_prior_or_artifact_checks(self):
        def graph(f):
            (f["prepared"] / "graph-scan/graph-sizes.jsonl").write_text("{}\n")
        def config(f):
            path = f["prepared"] / "train-capacity/config.scratch.resolved.json"
            value = json.loads(path.read_text());value["epochs"] = 1;write(path, value)
        def prior(f):
            f["report"]["training_prior"]["statistics"]["structures"] = 2;write(f["prepared"] / "report.json", f["report"])
        def raw(f):
            Path(f["spec"]["configs"]["pretrained"]["dataset"]["path"]).write_text("{}\n")
        def artifact(f):
            Path("models/official/fixture.bin").write_bytes(b"different")
        def stage(f):
            f["report"]["stage"] = "paired_training_capacity";write(f["prepared"] / "report.json", f["report"])
        for mutate in (graph, config, prior, raw, artifact, stage):
            with self.subTest(mutation=mutate.__name__), training_evidence() as f:
                mutate(f)
                with self.assertRaises((ValueError, KeyError)):
                    gates._check_prepared_spec(f["matrix"], f["spec"], f["prepared"], budget_seconds=10000, generation_training_only=True)

    def test_only_eight_active_generation_cases_and_original_recipes(self):
        matrix = build_matrix(registry_fixture())
        matrix.update(definition_revision=2, registry_sha256=canonical_digest(matrix["registry"]))
        active = [c for c in matrix["cases"] if c["task"] == "generation" and c["seed"] == 123]
        scope = dict(training_seeds=[123], supplemental_training_seeds=[123], base_matrix_sha256=canonical_digest(matrix),
                     active_case_ids=[c["id"] for c in active])
        with patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}), patch.object(staging, "read_json", return_value=scope):
            self.assertEqual(len(active), 8)
            for case in active:
                self.assertEqual(staging.active_generation_case(matrix, case["id"])["case"], case)
            for case in matrix["cases"]:
                if case["task"] == "generation" and case["seed"] != 123:
                    with self.assertRaises(ValueError):
                        staging.active_generation_case(matrix, case["id"])

    def test_login_and_invalid_budget_reject_before_model_import(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                staging.check_generation_training_preparation({}, "unused", "unused", budget_seconds=10)
            with self.assertRaises(RuntimeError):
                staging.run_staged_generation_quality({}, "unused", budget_seconds=10)
        with patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"}):
            for budget in (0, -1, True, math.nan, math.inf):
                with self.assertRaises(ValueError):
                    staging.declared_quality_budget(budget)

    def test_declared_quality_allocation_has_no_fabricated_measured_estimate(self):
        detail = "JobId=123 UserId=fixture(1) JobState=RUNNING NodeList=node42 AllocTRES=cpu=2,gres/gpu=1 TimeLimit=03:00:00 RunTime=00:01:00"
        with patch.dict(os.environ, {"SLURM_JOB_ID": "123"}), patch.object(staging.getpass, "getuser", return_value="fixture"), \
                patch.object(staging.subprocess, "check_output", return_value=detail):
            self.assertEqual(staging.declared_quality_budget(10800), 10740)
        with patch.dict(os.environ, {"SLURM_JOB_ID": "123"}), patch.object(staging.getpass, "getuser", return_value="fixture"), \
                patch.object(staging.subprocess, "check_output", return_value=detail.replace(",gres/gpu=1", "")):
            with self.assertRaises(RuntimeError):
                staging.declared_quality_budget(10800)

    def test_saved_gate_is_replayed_and_any_non_source_field_change_rejected(self):
        gate = dict(git_commit="a" * 40, training_readiness_only=True, preparation="prep", budget_seconds=100, config=dict(epochs=300))
        with patch.object(staging, "active_generation_case"), patch.object(staging, "check_generation_training_preparation", return_value=copy.deepcopy(gate)):
            staging.revalidate_gate({}, "case", gate)
            gate["config"]["epochs"] = 3
            with self.assertRaises(ValueError):
                staging.revalidate_gate({}, "case", gate)

    def test_full_thousand_invalid_or_mixed_attempts_remain_required(self):
        from universal_gnn.benchmarks.generation.execution import verify_quality
        for valid in (0, 3):
            with generation_fixture(valid=valid) as f:
                # Existing fixture is an ordered protocol observation, not a model-quality claim.
                _, trained, gate, _, result, _ = f
                result["sampling_failure_policy"] = sampling_policy()
                self.assertEqual(verify_quality(result, trained, gate)["attempted"], 1000)
                result["attempted"] = 999
                with self.assertRaises(ValueError):
                    verify_quality(result, trained, gate)

    def test_staged_quality_saves_explicit_policy_and_preserves_best_and_last(self):
        from universal_gnn.benchmarks.generation.execution import _run_generation_case_quality
        with generation_fixture() as f, ExitStack() as stack:
            root, trained, gate, events, result, _ = f
            case = dict(id="fixture", run_directory=str(root), initialization="pretrained")
            gate["case"] = case
            gate["preparation"] = "unchanged-failed-preparation"
            gate["training_readiness_only"] = True
            gate.pop("probed_sample_batch_seconds")
            expected = copy.deepcopy(gate["config"])
            expected.pop("generation_prior");expected["task"]["sampling"].pop("volume_per_atom")
            spec = dict(case=case, counts=gate["counts"], source_structures=gate["source_structures"],
                        configs={"pretrained": expected}, quality_protocol=gate["quality_protocol"], matrix_sha256=gate["matrix_sha256"])
            status = dict(status="training_passed_quality_pending", formal_training_runs_completed=1,
                generation_quality_complete=False, independent_postevaluation_verified=False,
                last_checkpoint_sha256=gates.file_sha(trained["checkpoint"]))
            for name, value in [("generation-gate.json", gate), ("report.json", trained), ("formal-status.json", status)]:
                write(root / name, value)
            (root / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            prefix = "universal_gnn.benchmarks.generation.execution."
            for name, value in [("generation_case", spec), ("installed_versions", {}), ("compatible_sources", "b" * 40)]:
                stack.enter_context(patch(prefix + name, return_value=value))
            stack.enter_context(patch(prefix + "shutil.disk_usage", return_value=SimpleNamespace(free=30 * 1024**3)))
            stack.enter_context(patch.object(staging, "revalidate_gate", return_value=gate))
            stack.enter_context(patch.object(staging, "declared_quality_budget", return_value=86400))
            class Denoiser:
                def sample(self):
                    raise ValueError("Cell requires 51129 periodic images; check cell/cutoff")
            original = Denoiser.sample
            def quality(checkpoint, output, **kwargs):
                self.assertEqual(kwargs, dict(count=1000, draws_per_condition=5, seed=456, device="cuda"))
                self.assertEqual(checkpoint, trained["checkpoint"])
                with self.assertRaises(FloatingPointError):
                    Denoiser().sample()
                output.mkdir()
                return result
            cuda = SimpleNamespace(is_available=lambda: True, reset_peak_memory_stats=lambda: None,
                                   max_memory_allocated=lambda: 0, max_memory_reserved=lambda: 0)
            stack.enter_context(patch.dict(sys.modules, {"torch": SimpleNamespace(cuda=cuda),
                "resource": SimpleNamespace(RUSAGE_SELF=0, getrusage=lambda _: SimpleNamespace(ru_maxrss=0)),
                "universal_gnn.tasks.generation": SimpleNamespace(PeriodicDenoiser=Denoiser),
                "universal_gnn.engine.generative.quality": SimpleNamespace(run_generation_quality=quality)}))
            stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "controlled-quality"}))
            completed = _run_generation_case_quality({}, "fixture", budget_seconds=86400, staged=True)
            self.assertEqual(completed["status"], "passed")
            self.assertIsNone(completed["quality_budget_estimate_seconds"])
            self.assertFalse(completed["independent_postevaluation_verified"])
            metrics = json.loads(Path(completed["quality"]).read_text())
            self.assertEqual(metrics["sampling_failure_policy"], completed["sampling_failure_policy"])
            self.assertEqual(metrics["sampling_failure_policy"], sampling_policy())
            self.assertTrue(Path(trained["checkpoint"]).exists() and Path(trained["best_checkpoint"]).exists())
            self.assertIs(Denoiser.sample, original)


if __name__ == "__main__":
    unittest.main()
