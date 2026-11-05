"""Pure launch protocol fixtures; never evidence of official CUDA or training."""

import copy
from contextlib import ExitStack, contextmanager, redirect_stderr
import hashlib
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

from universal_gnn.benchmarks.execution.gates import file_sha, read_json
from universal_gnn.benchmarks.frozen_backbones import submission as frozen
from universal_gnn.benchmarks.frozen_backbones import telemetry
from universal_gnn.benchmarks.submission import dispatch as transport

HERE = Path(__file__).parent
fields = runpy.run_path(str(HERE / "test_tensor_submission.py"))["fields"]


def write(path, value):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, allow_nan=False).encode())


@contextmanager
def fixture(task="forcefield", provider="cgcnn"):
    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
        root = Path(folder);previous = Path.cwd();os.chdir(root);stack.callback(os.chdir, previous)
        claim = Path("original-claims")
        stack.enter_context(patch.object(telemetry, "PREPARATION_CLAIMS", claim))
        stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "protocol-fixture"}))
        stack.enter_context(patch.object(telemetry, "source_pinned"))
        stack.enter_context(patch("universal_gnn.benchmarks.supplemental_tensors.telemetry.getpass.getuser", return_value="xmz"))
        stack.enter_context(patch.object(frozen.sys, "prefix", "/fixture/universal-official"))
        stack.enter_context(patch.object(frozen, "partition_maximum", return_value=None))
        stack.enter_context(patch.object(frozen.shutil, "disk_usage", return_value=SimpleNamespace(free=100 * 1024**3)))
        specs, jobs = {}, {}
        for task_name in ("forcefield", "dielectric"):
            for model, base in telemetry.FIRST_JOBS.items():
                identifier = "frozen--seed-123--" + task_name + "--" + model
                first = base + (4 if task_name == "dielectric" else 0)
                config = dict(seed=123, epochs=300, structures="all", max_atoms=None, dtype="float32", batch_size=4,
                    optimization=dict(train_backbone=False, train_readout=True), evaluation=dict(patience=30, min_delta=0.))
                case = dict(id=identifier, task=task_name, model=model, seed=123, initialization="pretrained",
                    config=config, run_directory="runs/arxiv-v1/frozen-cases/" + identifier, python_environment="universal-official")
                specs[identifier] = dict(case=case, counts=dict(train=3, validation=1, test=1))
                preparation = "runs/arxiv-v1/frozen-preparation-" + str(first) + "-" + task_name + "-" + model
                independent = "runs/arxiv-v1/frozen-independent-gates-b167881/" + identifier + ".json"
                outputs = [preparation, str(claim / (identifier + "-preparation-terminal.json")), independent,
                           str(claim / (identifier + "-gate-terminal.json"))]
                dependencies = [None, "afterany:" + str(first), "afterok:" + str(first) + ":" + str(first + 1), "afterany:" + str(first + 2)]
                jobs[identifier] = {}
                for index, phase in enumerate(telemetry.PHASES):
                    cpus, memory, limit, gpus, nice = telemetry.resources(phase)
                    request = claim / (identifier + "-" + phase + ".sh")
                    request.parent.mkdir(parents=True, exist_ok=True);request.write_text("#!/bin/bash\n# protocol fixture " + identifier + " " + phase + "\n")
                    token = "ugnn-frozen-" + hashlib.sha256(str(request).encode()).hexdigest()[:32]
                    source = "/home/xmz/universal/runs/source-checkouts/" + telemetry.PREPARATION_COMMIT
                    argv = ["sbatch", "--parsable", "--no-requeue", "--partition=compute", "--nodelist=node42",
                        "--cpus-per-task=" + str(cpus), "--mem=" + str(memory) + "G", "--time=" + limit,
                        "--nice=" + str(nice), "--chdir=" + source, "--comment=" + token,
                        "--job-name=ugnn-frozen-" + phase + "-" + identifier]
                    if gpus:argv.append("--gres=gpu:1")
                    if dependencies[index]:argv.append("--dependency=" + dependencies[index])
                    jobs[identifier][phase] = dict(case_id=identifier, phase=phase, job=str(first + index),
                        git_commit=telemetry.PREPARATION_COMMIT, source_checkout=source, submission_token=token,
                        request_path=str(request), request_sha256=file_sha(request), sbatch_argv=argv,
                        formal_training_runs=0, output=outputs[index])
                write(Path(preparation) / "report.json", dict(git_commit=telemetry.PREPARATION_COMMIT, slurm_job_id=str(first),
                    case_id=identifier, status="passed", stage="complete", cuda_acceptance=True))
                write(independent, dict(status="passed", kind="formal_frozen_backbone_execution_gate", case=case,
                    definition_sha256=telemetry.DEFINITION_SHA, git_commit=telemetry.PREPARATION_COMMIT,
                    budget_seconds=3600, probed_train_only_seconds=1000., config=config))
                for phase, artifact in (("prepare", Path(preparation) / "report.json"), ("gate", Path(independent))):
                    entry = jobs[identifier][phase];cpus, memory, limit, gpus, nice = telemetry.resources(phase)
                    row = dict(JobId=entry["job"], UserId="xmz(1001)", JobName="ugnn-frozen-" + phase + "-" + identifier,
                        WorkDir=source, Comment=entry["submission_token"], Partition="compute", Requeue="0", NumCPUs=str(cpus),
                        MinMemoryNode=str(memory) + "G", TimeLimit=limit, Nice=str(nice), ReqNodeList="node42",
                        JobState="COMPLETED", ExitCode="0:0")
                    if gpus:row["TresPerNode"] = "gres:gpu:1"
                    write(jobs[identifier][phase + "-terminal"]["output"], dict(status="retained", successful=True, entry=entry,
                        fields=row, raw=shlex.join([k + "=" + v for k, v in row.items()]), request_sha256=entry["request_sha256"],
                        artifact=str(artifact), artifact_sha256=file_sha(artifact), formal_training_runs=0))
        write(claim / "jobs.json", jobs)
        select = lambda settings, identifier: copy.deepcopy(specs[identifier])
        stack.enter_context(patch.object(frozen, "execution_spec", side_effect=select))
        stack.enter_context(patch.object(telemetry, "execution_spec", side_effect=select))
        def replay(settings, identifier, preparation, independent_gate, **options):
            return dict(read_json(independent_gate), git_commit="b" * 40)
        stack.enter_context(patch.object(frozen, "checked_execution_gate", side_effect=replay))
        stack.enter_context(patch.object(transport, "validate_submitted_job", side_effect=fields))
        stack.enter_context(patch.object(frozen, "validate_submitted_job", side_effect=fields))
        numbers = iter(range(2001, 2200))
        scheduler = stack.enter_context(patch.object(transport.subprocess, "run",
            side_effect=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=str(next(numbers)).encode(), stderr=b"")))
        identifier = "frozen--seed-123--" + task + "--" + provider
        entries = jobs[identifier]
        yield root, identifier, Path(entries["prepare"]["output"]), Path(entries["gate"]["output"]), jobs, scheduler


class FrozenSubmissionTests(unittest.TestCase):
    def test_all_eight_original_successful_terminals_are_source_and_artifact_bound(self):
        with fixture() as (_, _, _, _, jobs, scheduler):
            for identifier, entries in jobs.items():
                result = telemetry.checked_preparation_terminals({}, identifier, entries["prepare"]["output"], entries["gate"]["output"])
                self.assertEqual(result["preparation_job"], entries["prepare"]["job"])
                self.assertEqual(result["independent_gate_job"], entries["gate"]["job"])
                self.assertEqual(len(result["input_sha256"]), 9)
            scheduler.assert_not_called()

    def test_frozen_plan_keeps_full_recipe_and_six_precise_managed_stages(self):
        with fixture() as (_, identifier, prep, gate, _, scheduler):
            plan = frozen.build_frozen_submission_plan({}, identifier, prep, gate)
            self.assertEqual(plan["gate"]["config"]["optimization"], dict(train_backbone=False, train_readout=True))
            self.assertEqual(plan["gate"]["config"]["epochs"], 300)
            self.assertEqual(plan["training_budget_seconds"], 3600)
            self.assertEqual([item["phase"] for item in plan["stages"]], ["train", "terminal_train", "post", "terminal_post", "verify", "terminal_verify"])
            for item in plan["stages"]:
                terminal = item["phase"].startswith("terminal_")
                self.assertEqual(item["dependency_kind"], "afterany" if terminal else "afterok")
                self.assertEqual(item["resources"]["nice"], 0 if terminal else 1000)
                self.assertEqual(item["resources"]["gpus"], int(item["phase"] == "train"))
                if item["phase"] != "train":self.assertIn('CUDA_VISIBLE_DEVICES=""', item["script"])
                self.assertIn("record_tensor_terminal.py stage" if terminal else "run_frozen_case.py " + item["phase"], item["script"])
            scheduler.assert_not_called()

    def test_exact_six_requests_and_same_known_receipts_reused_without_submission(self):
        with fixture() as (_, identifier, prep, gate, _, scheduler):
            first = frozen.dispatch_frozen_case({}, identifier, prep, gate)
            self.assertEqual((first["newly_submitted_jobs"], first["newly_submitted_training_jobs"]), (6, 1))
            self.assertEqual(scheduler.call_count, 6)
            for row in first["jobs"].values():
                self.assertEqual(file_sha(Path(row["claim_directory"]) / "request.sh"), row["request_sha256"])
                self.assertTrue(Path(row["claim_directory"]).is_relative_to(frozen.LAUNCHES))
            with patch.dict(os.environ, {"SLURM_JOB_ID": "reuse-fixture"}):second = frozen.dispatch_frozen_case({}, identifier, prep, gate)
            self.assertEqual(second["newly_submitted_jobs"], 0)
            self.assertTrue(all(row["reused"] for row in second["jobs"].values()))
            self.assertEqual(scheduler.call_count, 6)
            self.assertFalse(Path("runs/arxiv-v1/launches").exists())
            self.assertFalse(Path("runs/arxiv-v1/supplemental-launches").exists())

    def test_ambiguous_submit_cannot_retry_or_replace_any_prior_receipt(self):
        with fixture() as (_, identifier, prep, gate, _, scheduler):
            scheduler.side_effect = [SimpleNamespace(returncode=0, stdout=b"2001", stderr=b""), subprocess.TimeoutExpired("sbatch", 30)]
            with self.assertRaises(subprocess.TimeoutExpired):frozen.dispatch_frozen_case({}, identifier, prep, gate)
            report = read_json(frozen.DISPATCHES / identifier / "attempts/protocol-fixture/report.json")
            self.assertEqual(report["status"], "submission_failed")
            self.assertEqual(len(report["jobs"]), 1)
            with patch.dict(os.environ, {"SLURM_JOB_ID": "retry-fixture"}), self.assertRaises(RuntimeError):
                frozen.dispatch_frozen_case({}, identifier, prep, gate)
            self.assertEqual(scheduler.call_count, 2)

    def test_foreign_missing_purged_mutated_or_unclaimed_outputs_stop_without_new_requests(self):
        for change in ("foreign", "output", "lock", "token", "purged"):
            with self.subTest(change=change), fixture() as (_, identifier, prep, gate, _, scheduler), ExitStack() as stack:
                plan = frozen.build_frozen_submission_plan({}, identifier, prep, gate)
                if change == "foreign":frozen.claim_path(plan["stages"][0]).mkdir(parents=True)
                elif change == "output":Path(plan["stages"][2]["output"]).mkdir(parents=True)
                elif change == "lock":(frozen.DISPATCHES / identifier / "active").mkdir(parents=True)
                else:
                    first = frozen.dispatch_frozen_case({}, identifier, prep, gate)
                    if change == "token":
                        path = Path(next(iter(first["jobs"].values()))["claim_directory"]) / "launch.json"
                        row = read_json(path);row["submission_token"] = "foreign";write(path, row)
                    else:stack.enter_context(patch.object(transport, "validate_submitted_job", side_effect=transport.ReceiptNotRetained("purged")))
                    os.environ["SLURM_JOB_ID"] = "another-fixture"
                before = scheduler.call_count
                with self.assertRaises((RuntimeError, FileExistsError)):frozen.dispatch_frozen_case({}, identifier, prep, gate)
                self.assertEqual(scheduler.call_count, before)

    def test_original_job_request_source_dependency_and_resource_tampering_is_rejected(self):
        for change in ("job", "source", "token", "request", "dependency", "resource", "scope"):
            with self.subTest(change=change), fixture() as (_, identifier, prep, gate, jobs, scheduler):
                entry = jobs[identifier]["gate"]
                if change == "job":entry["job"] = "9999"
                elif change == "source":entry["git_commit"] = "f" * 40
                elif change == "token":entry["submission_token"] = "foreign"
                elif change == "request":Path(entry["request_path"]).write_text("changed bytes")
                elif change == "dependency":entry["sbatch_argv"][-1] = "--dependency=afterok:9999"
                elif change == "resource":entry["sbatch_argv"].append("--mem=8G")
                else:jobs["foreign"] = {}
                write(telemetry.PREPARATION_CLAIMS / "jobs.json", jobs)
                with self.assertRaises(ValueError):frozen.build_frozen_submission_plan({}, identifier, prep, gate)
                scheduler.assert_not_called()

    def test_retained_failed_unknown_or_changed_original_artifacts_cannot_qualify(self):
        for change in ("failed", "unavailable", "owner", "exit", "fields", "artifact", "case", "cuda", "gate_source"):
            with self.subTest(change=change), fixture() as (_, identifier, prep, gate, jobs, scheduler):
                path = jobs[identifier]["gate-terminal"]["output"]
                row = read_json(path)
                if change == "failed":row["successful"] = False
                elif change == "unavailable":row["status"] = "unavailable"
                elif change == "owner":row["fields"]["UserId"] = "foreign(2)"
                elif change == "exit":row["fields"]["ExitCode"] = "7:0"
                elif change == "fields":row["raw"] = "different retained fields"
                elif change == "artifact":write(gate, dict(changed=True))
                elif change in ("case", "gate_source"):
                    value = read_json(gate)
                    if change == "case":value["case"]["id"] += "--bad"
                    else:value["git_commit"] = "f" * 40
                    write(gate, value);row["artifact_sha256"] = file_sha(gate)
                else:
                    value = read_json(prep / "report.json");value["cuda_acceptance"] = False;write(prep / "report.json", value)
                    p = jobs[identifier]["prepare-terminal"]["output"];t = read_json(p);t["artifact_sha256"] = file_sha(prep / "report.json");write(p, t)
                if change in ("owner", "exit"):row["raw"] = shlex.join([k + "=" + v for k, v in row["fields"].items()])
                write(path, row)
                with self.assertRaises(ValueError):frozen.build_frozen_submission_plan({}, identifier, prep, gate)
                scheduler.assert_not_called()

    def test_login_budget_disk_environment_and_measured_budget_guards(self):
        for change in ("login", "budget", "partition", "disk", "environment", "measured"):
            with self.subTest(change=change), fixture() as (_, identifier, prep, gate, _, scheduler), ExitStack() as stack:
                args = {}
                if change == "login":stack.enter_context(patch.dict(os.environ, {}, clear=True))
                elif change == "budget":args["post_seconds"] = 0
                elif change == "partition":stack.enter_context(patch.object(frozen, "partition_maximum", return_value=1000))
                elif change == "disk":stack.enter_context(patch.object(frozen.shutil, "disk_usage", return_value=SimpleNamespace(free=1)))
                elif change == "environment":stack.enter_context(patch.object(frozen.sys, "prefix", "/foreign"))
                else:value = read_json(gate);value["budget_seconds"] = 7200;write(gate, value)
                with self.assertRaises((ValueError, RuntimeError)):frozen.dispatch_frozen_case({}, identifier, prep, gate, **args)
                scheduler.assert_not_called()

    def test_cli_requires_slurm_and_review_only_output(self):
        script = str(HERE.resolve().parent / "scripts/submit_frozen_case.py")
        common = ["--case", "fixture", "--preparation", "p", "--independent-gate", "g"]
        for args, slurm in [(common, False), (common + ["--plan-output", "out.json"], True)]:
            with self.subTest(slurm=slurm), patch.dict(os.environ, {"SLURM_JOB_ID": "fixture"} if slurm else {}, clear=True), \
                    patch.object(sys, "argv", [script, *args]), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as error:runpy.run_path(script, run_name="__main__")
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":unittest.main()
