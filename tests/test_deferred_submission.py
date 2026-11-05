"""Pure submission protocol controls; mocked jobs never represent real training."""

import copy
from contextlib import contextmanager, ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.submission import build_submission_plan, dispatch_pair
from universal_gnn.benchmarks.submission.planning import finite_budget, partition_maximum, slurm_duration, request_script
from universal_gnn.benchmarks.execution.runner import duration_seconds
from universal_gnn.benchmarks.submission.dispatch import submit_stage, validate_submitted_job

registry_fixture = runpy.run_path(str(Path(__file__).with_name("test_arxiv_experiment_definitions.py")))["registry_fixture"]


@contextmanager
def plan_fixture(task="bandgap", provider="alignn", seed=123):
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory)
        before = Path.cwd()
        os.chdir(root)
        stack.callback(os.chdir, before)
        matrix = build_matrix(registry_fixture())
        path = root / "matrix.json"
        path.write_text(json.dumps(matrix), encoding="utf-8")
        preparation = root / "preparation"
        preparation.mkdir()
        (preparation / "report.json").write_text(json.dumps(dict(status="passed", stage="complete")), encoding="utf-8")
        stack.enter_context(patch.dict(os.environ, {"SLURM_JOB_ID": "parent-1"}))
        env = {"mace":"universal-mace", "nequip":"universal"}.get(provider,"universal-official")
        stack.enter_context(patch("sys.prefix", "/fake/.venvs/" + env))
        stack.enter_context(patch("sys.executable", "/fake/.venvs/" + env + "/bin/python"))
        prefix = "universal_gnn.benchmarks.submission.planning."
        stack.enter_context(patch(prefix + "partition_maximum", return_value=None))
        stack.enter_context(patch(prefix + "measured_train_estimate", return_value=1000.))
        def gate(_, identifier, preparation, **options):
            case = next(c for c in matrix["cases"] if c["id"]==identifier)
            return dict(status="passed",git_commit="a"*40,config=copy.deepcopy(case["config"]),
                        probed_train_only_seconds=1000.,probed_sample_batch_seconds=2.)
        full_gate = stack.enter_context(patch(prefix + "check_preparation", side_effect=gate))
        stack.enter_context(patch("universal_gnn.benchmarks.submission.dispatch.validate_submitted_job"))
        pair = "seed-" + str(seed) + "--" + task + "--" + provider
        yield root, matrix, path, preparation, pair, full_gate


def fake_scheduler(start=2001):
    jobs=iter(range(start,start+100))
    return lambda *a,**k:SimpleNamespace(returncode=0,stdout=str(next(jobs)).encode(),stderr=b"")


class DeferredSubmissionTests(unittest.TestCase):
    def test_existing_job_requires_same_owner_token_name_and_retained_success_state(self):
        receipt=dict(job="2001",phase="train",case_id="fixture",submission_token="ugnn-"+"a"*32)
        text="JobId=2001 JobName=ugnn-formal-fixture UserId=xmz(1001) JobState=RUNNING Comment="+receipt["submission_token"]
        with patch("universal_gnn.benchmarks.submission.dispatch.getpass.getuser",return_value="xmz"):
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.check_output",return_value=text):
                validate_submitted_job(receipt)
            for changed in (text.replace("xmz(","other("),text.replace("ugnn-formal-fixture","other"),
                            text.replace("RUNNING","FAILED"),text.replace("Comment=ugnn-","Comment=foreign-")):
                with self.subTest(text=changed),patch("universal_gnn.benchmarks.submission.dispatch.subprocess.check_output",return_value=changed):
                    with self.assertRaises(RuntimeError):validate_submitted_job(receipt)

    def test_finite_budgets_reserve_rounding_limits_and_slurm_duration(self):
        self.assertEqual(finite_budget(10.),3600)
        self.assertEqual(finite_budget(10000.),15900)
        self.assertEqual(duration_seconds(slurm_duration(123456)),123456)
        for estimate in (0,-1,True,math.inf,math.nan,1.79e308):
            with self.subTest(estimate=estimate),self.assertRaises(ValueError):finite_budget(estimate)
        with self.assertRaises(ValueError):finite_budget(10000.,10000)
        for maximum in (0,-1,True):
            with self.subTest(maximum=maximum),self.assertRaises(ValueError):finite_budget(1.,maximum)
        with patch("universal_gnn.benchmarks.submission.planning.subprocess.check_output",return_value="PartitionName=compute State=UP MaxTime=UNLIMITED"):
            self.assertIsNone(partition_maximum())
        with patch("universal_gnn.benchmarks.submission.planning.subprocess.check_output",return_value="PartitionName=compute State=UP MaxTime=2-00:00:00"):
            self.assertEqual(partition_maximum(),172800)

    def test_all_four_providers_six_tasks_keep_frozen_pair_recipes(self):
        for provider in ("cgcnn","alignn","mace","nequip"):
            for task in ("bandgap","classification","dielectric","spectrum","forcefield","generation"):
                for seed in (123,456,789):
                    with self.subTest(provider=provider,task=task,seed=seed),plan_fixture(task,provider,seed) as (root,matrix,path,prep,pair,gate):
                        before=copy.deepcopy(matrix)
                        plan=build_submission_plan(matrix,pair,prep,matrix_path=path)
                        self.assertEqual(matrix,before)
                        self.assertEqual(gate.call_count,2)
                        self.assertEqual(len(plan["stages"]),6 if task=="generation" else 2)
                        self.assertEqual(plan["formal_training_runs_submitted"],0)
                        self.assertFalse((root/"runs").exists())
                        self.assertEqual({c["config"]["epochs"] for c in plan["cases"]},{300})
                        self.assertEqual({c["seed"] for c in plan["cases"]},{seed})
                        self.assertEqual({c["initialization"] for c in plan["cases"]},{"pretrained","scratch"})

    def test_source_matrix_environment_and_both_gates_precede_submission(self):
        with plan_fixture() as (root,matrix,path,prep,pair,gate):
            with patch("sys.prefix","/fake/wrong"):
                with self.assertRaises(ValueError):build_submission_plan(matrix,pair,prep,matrix_path=path)
            original_gate=gate.side_effect
            count=0
            def second_rejected(*a,**k):
                nonlocal count
                count+=1
                if count==2:raise ValueError("second full evidence rejected")
                return original_gate(*a,**k)
            gate.side_effect=second_rejected
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run") as submit:
                with self.assertRaises(ValueError):dispatch_pair(matrix,pair,prep,matrix_path=path)
                submit.assert_not_called()
                self.assertEqual(count,2)
            self.assertFalse((root/"runs").exists())
            changed=copy.deepcopy(matrix);changed["unrelated_metadata"]="different on-disk identity"
            path.write_text(json.dumps(changed),encoding="utf-8")
            with self.assertRaises(ValueError):build_submission_plan(matrix,pair,prep,matrix_path=path)

    def test_generated_shell_arguments_are_quoted_and_not_reinterpreted(self):
        arguments=["/a path/python","script.py","file with spaces", "$(never_execute)","a'b"]
        body=request_script(arguments)
        self.assertEqual(shlex.split(body.splitlines()[-1])[1:],arguments)
        self.assertTrue(body.startswith("#!/bin/bash\nset -euo pipefail\n"))

    def test_predictive_dispatch_and_exact_known_receipt_retry(self):
        with plan_fixture() as (_,matrix,path,prep,pair,_):
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run",side_effect=fake_scheduler()) as submit:
                first=dispatch_pair(matrix,pair,prep,matrix_path=path)
                self.assertEqual(submit.call_count,2)
                self.assertEqual(first["formal_training_jobs"],2)
                self.assertEqual(first["formal_training_runs_completed"],0)
                os.environ["SLURM_JOB_ID"]="parent-2"
                for identifier in first["jobs"]:
                    case=identifier.rsplit(":",1)[0]
                    (Path("runs/arxiv-v1/cases")/case).mkdir(parents=True)
                second=dispatch_pair(matrix,pair,prep,matrix_path=path)
                self.assertEqual(submit.call_count,2)
                self.assertEqual(second["newly_submitted_training_jobs"],0)
                self.assertTrue(all(j["reused"] for j in second["jobs"].values()))

    def test_generation_stages_keep_afterok_gpu_and_cpu_boundaries(self):
        with plan_fixture("generation") as (_,matrix,path,prep,pair,_):
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run",side_effect=fake_scheduler()) as submit:
                result=dispatch_pair(matrix,pair,prep,matrix_path=path)
                self.assertEqual(submit.call_count,6)
                calls=submit.call_args_list
                for index in (0,3):
                    self.assertFalse(any(v.startswith("--dependency") for v in calls[index].args[0]))
                self.assertIn("--dependency=afterok:2001",calls[1].args[0])
                self.assertIn("--dependency=afterok:2002",calls[2].args[0])
                self.assertIn("--dependency=afterok:2004",calls[4].args[0])
                self.assertIn("--dependency=afterok:2005",calls[5].args[0])
                for index,call in enumerate(calls):
                    self.assertEqual("--gres=gpu:1" in call.args[0],index not in (2,5))
                self.assertEqual(result["formal_training_jobs"],2)
                self.assertEqual(result["formal_training_runs_completed"],0)

    def test_unmanaged_existing_results_or_claims_are_never_rerun(self):
        for existing in ("cases","launches"):
            with self.subTest(existing=existing),plan_fixture() as (_,matrix,path,prep,pair,_):
                (Path("runs/arxiv-v1")/existing/(pair+"--pretrained")).mkdir(parents=True)
                with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run") as submit:
                    with self.assertRaises(FileExistsError):dispatch_pair(matrix,pair,prep,matrix_path=path)
                    submit.assert_not_called()

    def test_ambiguous_submission_keeps_intent_and_never_auto_retries(self):
        for response in (SimpleNamespace(returncode=1,stdout=b"",stderr=b"lost reply"),
                         SimpleNamespace(returncode=0,stdout=b"unexpected text",stderr=b""),
                         subprocess.TimeoutExpired("sbatch",30)):
            with self.subTest(response=type(response).__name__),plan_fixture() as (_,matrix,path,prep,pair,_):
                with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run",side_effect=response if isinstance(response,Exception) else lambda *a,**k:response) as submit:
                    with self.assertRaises((RuntimeError,subprocess.TimeoutExpired)):dispatch_pair(matrix,pair,prep,matrix_path=path)
                    self.assertEqual(submit.call_count,1)
                    os.environ["SLURM_JOB_ID"]="parent-2"
                    with self.assertRaises(RuntimeError):dispatch_pair(matrix,pair,prep,matrix_path=path)
                    self.assertEqual(submit.call_count,1)
                directory=Path("runs/arxiv-v1/launches")/(pair+"--pretrained")
                intent=json.loads((directory/"submission-intent.json").read_text())
                self.assertEqual(intent["state"],"submission_unknown")
                self.assertFalse((directory/"launch.json").exists())

    def test_partial_pair_before_next_claim_recovers_without_duplicate_job(self):
        with plan_fixture() as (_,matrix,path,prep,pair,_):
            count=0
            def interrupted(plan,item,jobs):
                nonlocal count
                count+=1
                if count==2:raise RuntimeError("controller interrupted before next claim")
                return submit_stage(plan,item,jobs)
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run",side_effect=fake_scheduler()) as submit:
                with patch("universal_gnn.benchmarks.submission.dispatch.submit_stage",side_effect=interrupted):
                    with self.assertRaises(RuntimeError):dispatch_pair(matrix,pair,prep,matrix_path=path)
                self.assertEqual(submit.call_count,1)
                os.environ["SLURM_JOB_ID"]="parent-2"
                recovered=dispatch_pair(matrix,pair,prep,matrix_path=path)
                self.assertEqual(submit.call_count,2)
                self.assertEqual(recovered["newly_submitted_training_jobs"],1)
                self.assertEqual(recovered["jobs"][pair+"--pretrained:train"]["job"],"2001")

    def test_saved_request_tampering_and_live_pair_lock_are_refused(self):
        with plan_fixture() as (_,matrix,path,prep,pair,_):
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run",side_effect=fake_scheduler()) as submit:
                dispatch_pair(matrix,pair,prep,matrix_path=path)
                script=Path("runs/arxiv-v1/launches")/(pair+"--pretrained")/"request.sh"
                script.write_bytes(script.read_bytes()+b"# changed\n")
                os.environ["SLURM_JOB_ID"]="parent-2"
                with self.assertRaises(RuntimeError):dispatch_pair(matrix,pair,prep,matrix_path=path)
                self.assertEqual(submit.call_count,2)
        with plan_fixture() as (_,matrix,path,prep,pair,_):
            active=Path("runs/arxiv-v1/dispatch")/pair/"active";active.mkdir(parents=True)
            (active/"owner.json").write_text('{"slurm_job_id":"other"}')
            with patch("universal_gnn.benchmarks.submission.dispatch.subprocess.run") as submit:
                with self.assertRaises(FileExistsError):dispatch_pair(matrix,pair,prep,matrix_path=path)
                submit.assert_not_called()
            self.assertTrue((active/"owner.json").exists())

    def test_guards_precede_runtime_and_disk_claims(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):build_submission_plan({},"unused","unused",matrix_path="unused")
            with self.assertRaises(RuntimeError):dispatch_pair({},"unused","unused",matrix_path="unused")
        with plan_fixture() as (root,matrix,path,prep,pair,_):
            with patch("universal_gnn.benchmarks.submission.dispatch.shutil.disk_usage",return_value=SimpleNamespace(free=1)):
                with self.assertRaises(RuntimeError):dispatch_pair(matrix,pair,prep,matrix_path=path)
            self.assertFalse((root/"runs").exists())


if __name__ == "__main__":
    unittest.main()
