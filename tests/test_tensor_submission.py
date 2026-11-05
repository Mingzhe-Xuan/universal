"""Synthetic Slurm protocol controls; no job here represents numerical training."""

import copy
from contextlib import ExitStack, contextmanager, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.supplemental_tensors import submission as tensor
from universal_gnn.benchmarks.supplemental_tensors import telemetry
from universal_gnn.benchmarks.submission import dispatch as transport
from universal_gnn.benchmarks.execution.gates import file_sha, read_json

helpers = runpy.run_path(str(Path(__file__).with_name("test_tensor_execution.py")))
def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, allow_nan=False).encode())


def fields(receipt, state="RUNNING", exit_code="0:0"):
    resources = receipt["resources"]
    row = dict(JobId=receipt["job"], UserId="xmz(1001)", JobName="ugnn-" + transport.stage_kind(receipt["phase"]) + "-" + receipt["case_id"],
        Comment=receipt["submission_token"], JobState=state, ExitCode=exit_code, WorkDir=receipt["source_checkout"],
        Partition="compute", Requeue="0", NumCPUs=str(resources["cpus_per_task"]), MinMemoryNode=str(resources["memory_gib"]) + "G",
        TimeLimit=resources["time"], Nice=str(resources.get("nice", 0)), ReqNodeList="node42")
    if resources["gpus"]: row["TresPerNode"] = "gres:gpu:" + str(resources["gpus"])
    return row


@contextmanager
def fixture():
    with helpers["pair_fixture"]() as (root, identifier, prep, gates, parent, rebuild), ExitStack() as stack:
        previous = Path.cwd(); os.chdir(root); stack.callback(os.chdir, previous)
        stack.enter_context(patch.object(tensor, "selected_case", side_effect=helpers["tensor"].selected_case))
        parent["budget_seconds"] = 3600
        for mode, gate in gates.items():
            gate["budget_seconds"] = 3600
            write(root / ("gate-" + mode + ".json"), gate)
            parent["gates"][mode]["sha256"] = file_sha(root / ("gate-" + mode + ".json"))
        write(root / "report.json", parent)
        rebuild.side_effect = lambda definitions, case, preparation, **kwargs: dict(gates[case.rsplit("--", 1)[1]], git_commit="b" * 40)
        stack.enter_context(patch.object(tensor, "checked_gate_terminal", return_value=dict(job="1254", terminal_sha256="c" * 64)))
        stack.enter_context(patch.object(tensor, "partition_maximum", return_value=None))
        stack.enter_context(patch.object(tensor, "measured_train_estimate", return_value=1000.))
        stack.enter_context(patch.object(tensor.shutil, "disk_usage", return_value=SimpleNamespace(free=100 * 1024**3)))
        stack.enter_context(patch.object(telemetry.getpass, "getuser", return_value="xmz"))
        stack.enter_context(patch.object(transport, "validate_submitted_job", side_effect=fields))
        stack.enter_context(patch.object(tensor, "validate_submitted_job", side_effect=fields))
        jobs = iter(range(2001, 2100))
        scheduler = stack.enter_context(patch.object(transport.subprocess, "run", side_effect=lambda *a, **kw:
            SimpleNamespace(returncode=0, stdout=str(next(jobs)).encode(), stderr=b"")))
        yield root, identifier.rsplit("--", 1)[0], prep, root, scheduler


@contextmanager
def original_gate():
    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
        root = Path(folder); previous = Path.cwd(); os.chdir(root); stack.callback(os.chdir, previous)
        pair = "rank34--seed-123--piezoelectric--cgcnn"
        stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "recorder-fixture"}))
        stack.enter_context(patch.object(telemetry, "selected_case", return_value={}))
        stack.enter_context(patch.object(telemetry, "source_pinned"))
        stack.enter_context(patch.object(telemetry.getpass, "getuser", return_value="xmz"))
        claim = telemetry.GATE_CLAIMS / pair; claim.mkdir(parents=True)
        request = claim / "request.sh"; request.write_bytes(b"#!/bin/bash\n# explicit protocol fixture, never executed\n")
        source = "/home/xmz/universal/runs/source-checkouts/" + telemetry.GATE_COMMIT
        output = "runs/arxiv-v1/supplemental-preparation-gates/" + pair + "-3483500-attempt-001"
        argv = ["sbatch", "--no-requeue", "--partition=compute", "--nodelist=node42", "--cpus-per-task=1", "--mem=4G",
                "--time=00:20:00", "--chdir=" + source, "--job-name=ugnn-rank34-independent-gate-" + pair, "--dependency=afterok:1233:1234"]
        entry = dict(pair=pair, seed=123, git_commit=telemetry.GATE_COMMIT, source_checkout=source,
            preparation_job="1233", terminal_observer_job="1234", dependency="afterok:1233:1234", output=output,
            request_path=str(request), request_sha256=file_sha(request), sbatch_argv=argv, formal_training_runs=0,
            acceptance_control_job="1252", job="1254", state="submitted")
        write(claim / "job.json", entry)
        write(Path(output) / "report.json", dict(status="passed", slurm_job_id="1254", git_commit=telemetry.GATE_COMMIT))
        row = dict(JobId="1254", UserId="xmz(1001)", JobName="ugnn-rank34-independent-gate-" + pair,
            WorkDir=source, Partition="compute", Requeue="0", NumCPUs="1", MinMemoryNode="4G", TimeLimit="00:20:00",
            Nice="0", ReqNodeList="node42", JobState="COMPLETED", ExitCode="0:0")
        yield root, pair, entry, row


class TensorSubmissionTests(unittest.TestCase):
    def test_plan_has_two_full_trains_four_cpu_science_six_afterany_recorders(self):
        with fixture() as (root, pair, prep, independent, scheduler):
            plan = tensor.build_tensor_submission_plan({}, pair, prep, independent)
            self.assertEqual(len(plan["stages"]), 12)
            self.assertEqual(plan["training_budget_seconds"], 3600)
            for item in plan["stages"]:
                terminal = item["phase"].startswith("terminal_")
                resources = item["resources"]
                self.assertEqual(item["dependency_kind"], "afterany" if terminal else "afterok")
                self.assertEqual(resources["nice"], 0 if terminal else 1000)
                self.assertEqual(resources["gpus"], int(item["phase"] == "train"))
                self.assertEqual(file_sha(root / ("gate-" + item["case_id"].rsplit("--", 1)[1] + ".json")),
                                 read_json(root / "report.json")["gates"][item["case_id"].rsplit("--", 1)[1]]["sha256"])
                if item["phase"] != "train": self.assertIn('CUDA_VISIBLE_DEVICES=""', item["script"])
                if terminal: self.assertIn("record_tensor_terminal.py stage", item["script"])
                else: self.assertIn("run_tensor_case.py " + item["phase"], item["script"])
            scheduler.assert_not_called()

    def test_dispatch_exact_twelve_requests_and_reuse_submits_zero(self):
        with fixture() as (root, pair, prep, independent, scheduler):
            first = tensor.dispatch_tensor_pair({}, pair, prep, independent)
            self.assertEqual((first["newly_submitted_jobs"], first["newly_submitted_training_jobs"]), (12, 2))
            self.assertEqual(scheduler.call_count, 12)
            for receipt in first["jobs"].values():
                claim = Path(receipt["claim_directory"])
                self.assertTrue(claim.is_relative_to(tensor.LAUNCHES))
                self.assertEqual(receipt["request_sha256"], file_sha(claim / "request.sh"))
                terminal = receipt["phase"].startswith("terminal_")
                if receipt["phase"] != "train":
                    self.assertTrue(receipt["dependency"].startswith("afterany:" if terminal else "afterok:"))
                self.assertIn("--nice=" + str(receipt["resources"]["nice"]), receipt["sbatch_argv"])
            with patch.dict(os.environ, {"SLURM_JOB_ID": "reuse-fixture"}):
                second = tensor.dispatch_tensor_pair({}, pair, prep, independent)
            self.assertEqual(second["newly_submitted_jobs"], 0)
            self.assertTrue(all(row["reused"] for row in second["jobs"].values()))
            self.assertEqual(scheduler.call_count, 12)
            self.assertFalse((root / "runs/arxiv-v1/launches").exists())

    def test_unknown_partial_rpc_never_retries_and_keeps_prior_receipts(self):
        with fixture() as (root, pair, prep, independent, scheduler):
            scheduler.side_effect = [SimpleNamespace(returncode=0, stdout=b"2001", stderr=b""), subprocess.TimeoutExpired("sbatch", 30)]
            with self.assertRaises(subprocess.TimeoutExpired): tensor.dispatch_tensor_pair({}, pair, prep, independent)
            report = read_json(tensor.DISPATCHES / pair / "attempts/protocol-fixture/report.json")
            self.assertEqual(report["status"], "submission_failed")
            self.assertEqual(len(report["jobs"]), 1)
            plan = read_json(tensor.DISPATCHES / pair / "attempts/protocol-fixture/plan.json")
            claim = tensor.claim_path(plan["stages"][1])
            self.assertEqual(read_json(claim / "submission-intent.json")["state"], "submission_unknown")
            with patch.dict(os.environ, {"SLURM_JOB_ID": "retry-fixture"}), self.assertRaises(RuntimeError):
                tensor.dispatch_tensor_pair({}, pair, prep, independent)
            self.assertEqual(scheduler.call_count, 2)

    def test_existing_output_foreign_claim_lock_and_changed_receipt_stop_before_submitting(self):
        for change in ("output", "foreign", "lock", "receipt"):
            with self.subTest(change=change), fixture() as (root, pair, prep, independent, scheduler):
                plan = tensor.build_tensor_submission_plan({}, pair, prep, independent)
                if change == "output": Path(plan["stages"][2]["output"]).mkdir(parents=True)
                elif change == "foreign": tensor.claim_path(plan["stages"][0]).mkdir(parents=True)
                elif change == "lock": (tensor.DISPATCHES / pair / "active").mkdir(parents=True)
                else:
                    tensor.dispatch_tensor_pair({}, pair, prep, independent)
                    claim = tensor.claim_path(plan["stages"][-1]); receipt = read_json(claim / "launch.json")
                    receipt["submission_token"] = "foreign"; write(claim / "launch.json", receipt)
                    os.environ["SLURM_JOB_ID"] = "another-fixture"
                prior = scheduler.call_count
                with self.assertRaises((RuntimeError, FileExistsError)):
                    tensor.dispatch_tensor_pair({}, pair, prep, independent)
                self.assertEqual(scheduler.call_count, prior)

    def test_partition_budget_disk_and_independent_gate_fail_before_requests(self):
        for change in ("budget", "partition", "disk", "gate"):
            with self.subTest(change=change), fixture() as (root, pair, prep, independent, scheduler), ExitStack() as stack:
                args = {}
                if change == "budget": args["post_seconds"] = 0
                elif change == "partition": stack.enter_context(patch.object(tensor, "partition_maximum", return_value=1000))
                elif change == "disk": stack.enter_context(patch.object(tensor.shutil, "disk_usage", return_value=SimpleNamespace(free=1)))
                else: stack.enter_context(patch.object(tensor, "checked_gate_terminal", side_effect=ValueError("unfinished")))
                with self.assertRaises((ValueError, RuntimeError)): tensor.dispatch_tensor_pair({}, pair, prep, independent, **args)
                scheduler.assert_not_called()

    def test_transport_preserves_default_claims_and_limits_afterany_and_nice(self):
        with fixture() as (root, pair, prep, independent, scheduler):
            plan = tensor.build_tensor_submission_plan({}, pair, prep, independent)
            item = copy.deepcopy(plan["stages"][0])
            for change in ("afterany", "nice"):
                with self.subTest(change=change):
                    bad = copy.deepcopy(item)
                    if change == "nice": bad["resources"]["nice"] = True
                    with self.assertRaises(ValueError):
                        transport.submit_stage(plan, bad, {}, dependency_kind="afterany" if change == "afterany" else "afterok")
            scheduler.assert_not_called()
            self.assertFalse((root / "runs").exists())

    def test_actual_resource_schema_rejects_wrong_owner_gpu_memory_nice_or_exit_identity(self):
        with fixture() as (root, pair, prep, independent, scheduler):
            report = tensor.dispatch_tensor_pair({}, pair, prep, independent)
            receipt = next(row for row in report["jobs"].values() if row["phase"] == "train")
            for key, value in (("UserId", "foreign(2)"), ("TresPerNode", "gres:gpu:2"), ("MinMemoryNode", "32G"), ("Nice", "0"), ("Comment", "other")):
                bad = fields(receipt); bad[key] = value
                with self.subTest(key=key), patch.object(tensor, "validate_submitted_job", return_value=bad), self.assertRaises(ValueError):
                    tensor.checked_request_resources(receipt)

    def test_original_gate_terminal_success_and_failure_retained_without_overwrite(self):
        for state, code in (("COMPLETED", "0:0"), ("FAILED", "1:0"), ("OUT_OF_MEMORY", "0:125")):
            with self.subTest(state=state), original_gate() as (root, pair, entry, row):
                row.update(JobState=state, ExitCode=code)
                result = SimpleNamespace(returncode=0, stdout=shlex.join([key + "=" + value for key, value in row.items()]), stderr="")
                with patch.object(telemetry.subprocess, "run", return_value=result):
                    value = telemetry.record_gate_terminal({}, pair)
                    self.assertEqual(value["status"], "retained")
                    self.assertEqual(value["successful"], state == "COMPLETED")
                    with self.assertRaises(FileExistsError): telemetry.record_gate_terminal({}, pair)
                if state == "COMPLETED": self.assertEqual(telemetry.checked_gate_terminal({}, pair, entry["output"])["job"], "1254")
                else:
                    with self.assertRaises(ValueError): telemetry.checked_gate_terminal({}, pair, entry["output"])

    def test_gate_terminal_changed_report_request_source_or_owner_is_refused(self):
        for change in ("report", "request", "owner", "resources"):
            with self.subTest(change=change), original_gate() as (root, pair, entry, row):
                if change == "owner": row["UserId"] = "foreign(2)"
                elif change == "resources": row["MinMemoryNode"] = "8G"
                result = SimpleNamespace(returncode=0, stdout=shlex.join([key + "=" + value for key, value in row.items()]), stderr="")
                with patch.object(telemetry.subprocess, "run", return_value=result):
                    if change in {"owner", "resources"}:
                        with self.assertRaises(ValueError): telemetry.record_gate_terminal({}, pair)
                        self.assertEqual(read_json(telemetry.GATE_CLAIMS / pair / "terminal.json")["status"], "invalid_identity")
                        continue
                    telemetry.record_gate_terminal({}, pair)
                if change == "report": write(Path(entry["output"]) / "report.json", {})
                else: Path(entry["request_path"]).write_bytes(b"changed request")
                with self.assertRaises(ValueError): telemetry.checked_gate_terminal({}, pair, entry["output"])

    def test_stage_terminal_records_exact_source_token_and_scientific_report_hash(self):
        with fixture() as (root, pair, prep, independent, scheduler), patch.object(telemetry, "source_pinned"):
            report = tensor.dispatch_tensor_pair({}, pair, prep, independent)
            receipt = next(row for row in report["jobs"].values() if row["phase"] == "post")
            path = Path(receipt["claim_directory"]) / "launch.json"
            output = root / "post-output"; write(output / "report.json", dict(status="failed", diagnostic="fixture"))
            row = fields(receipt, "FAILED", "1:0")
            result = SimpleNamespace(returncode=0, stdout=shlex.join([key + "=" + value for key, value in row.items()]), stderr="")
            with patch.object(telemetry.subprocess, "run", return_value=result):
                value = telemetry.record_stage_terminal(path, output)
            self.assertFalse(value["successful"])
            self.assertEqual(value["artifact_sha256"][str(output / "report.json")], file_sha(output / "report.json"))

    def test_clis_require_slurm_and_unambiguous_modes(self):
        root = Path(__file__).resolve().parents[1]
        cases = [("submit_tensor_pair.py", ["--pair", "fixture", "--preparation", "p", "--independent-gate", "g"], False),
                 ("record_tensor_terminal.py", ["gate", "--pair", "fixture"], False),
                 ("record_tensor_terminal.py", ["gate", "--pair", "fixture", "--receipt", "p"], True),
                 ("record_tensor_terminal.py", ["stage", "--receipt", "p"], True)]
        for filename, args, slurm in cases:
            script = str(root / "scripts" / filename)
            with self.subTest(filename=filename, args=args), patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"} if slurm else {}, clear=True), \
                    patch.object(sys, "argv", [script, *args]), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as error: runpy.run_path(script, run_name="__main__")
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__": unittest.main()
