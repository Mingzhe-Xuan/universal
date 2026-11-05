"""Pure receipt/dispatch controls; fixtures never represent neural computation."""

import copy
from contextlib import contextmanager, ExitStack
import getpass
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.recipes import build_matrix, TASK_DATASETS
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.prediction_assessment import submission as post
from universal_gnn.benchmarks.submission import dispatch as core
from universal_gnn.benchmarks.submission.planning import request_script

registry_fixture = runpy.run_path(str(Path(__file__).with_name("test_arxiv_experiment_definitions.py")))["registry_fixture"]


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(json.dumps(value,allow_nan=False).encode())


@contextmanager
def original_dispatch(task="bandgap", provider="alignn", seed=123):
    with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
        root=Path(directory);before=Path.cwd();os.chdir(root);stack.callback(os.chdir,before)
        matrix=build_matrix(registry_fixture());matrix_path=root/"matrix.json";write(matrix_path,matrix)
        pair=f"seed-{seed}--{task}--{provider}"
        cases=[c for c in matrix["cases"] if c["pair_id"]==pair]
        old="a"*40;current="b"*40;source=root/"runs/source-checkouts"/old;source.mkdir(parents=True)
        env=cases[0]["python_environment"];python=str(Path(f"/fake/.venvs/{env}/bin/python").absolute())
        stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"1001"}))
        stack.enter_context(patch.object(post.sys,"prefix",f"/fake/.venvs/{env}"))
        stack.enter_context(patch.object(post.sys,"executable",python))
        scope=dict(base_matrix_sha256=canonical_digest(matrix),training_seeds=[123],
                   active_case_ids=[c["id"] for c in matrix["cases"] if c["seed"]==123])
        stack.enter_context(patch.object(post,"campaign_scope",return_value=scope))
        stack.enter_context(patch.object(post,"compatible_sources",return_value=current))
        stack.enter_context(patch.object(post,"source_identity"))
        stack.enter_context(patch.object(post,"partition_maximum",return_value=None))
        gates={};stages=[]
        for case in cases:
            mode=case["initialization"]
            gates[mode]=dict(status="passed",git_commit=old,config=copy.deepcopy(case["config"]),
                             budget_seconds=3600,preparation="fixture-preparation",
                             counts=copy.deepcopy(matrix["registry"]["datasets"][TASK_DATASETS[task]]["split_counts"]))
            args=[python,"scripts/run_formal_case.py",str(matrix_path),"--matrix-sha256",canonical_digest(matrix),
                  "--case",case["id"],"--preparation","fixture-preparation","--budget-seconds","3600"]
            script=request_script(args,repository=source)
            stages.append(dict(key=case["id"]+":train",case_id=case["id"],phase="train",depends_on=None,
                script=script,request_sha256=hashlib.sha256(script.encode()).hexdigest(),resources=dict(partition="compute",node="node42",
                    gpus=1,cpus_per_task=2,memory_gib=64,time="0-01:00:00",budget_seconds=3600)))
        provenance=dict(matrix_sha256=canonical_digest(matrix),git_commit=old,python=python,
                        configs={mode:canonical_digest(gate["config"]) for mode,gate in gates.items()},
                        stages=[{k:v for k,v in s.items() if k!="script"} for s in stages])
        original=dict(status="checked",kind="formal_pair_submission_plan",pair_id=pair,cases=cases,
                      gates=gates,stages=stages,provenance=provenance,fingerprint=canonical_digest(provenance))
        jobs={}
        for index,item in enumerate(stages):
            directory=Path("runs/arxiv-v1/launches")/item["case_id"];directory.mkdir(parents=True)
            token="ugnn-"+str(index+1)*32
            intent=dict(managed_by=core.MANAGED,fingerprint=original["fingerprint"],key=item["key"],case_id=item["case_id"],
                phase="train",dependency=None,request_sha256=item["request_sha256"],resources=item["resources"],git_commit=old,
                source_checkout=str(source),state="submitted",submission_token=token,parent_slurm_job="901")
            receipt=dict(intent,job=str(2001+index),request_path=str(directory/"request.sh"),formal_training_runs_completed=0)
            write(directory/"submission-intent.json",intent);write(directory/"launch.json",receipt)
            (directory/"request.sh").write_bytes(item["script"].encode())
            jobs[item["key"]]=dict(receipt,reused=False)
        dispatch=Path("runs/arxiv-v1/dispatch")/pair;attempt=dispatch/"attempts/901"
        report=dict(status="submitted",parent_slurm_job="901",pair_id=pair,fingerprint=original["fingerprint"],jobs=jobs)
        write(attempt/"plan.json",original);write(attempt/"report.json",report)
        write(dispatch/"latest.json",dict(attempt=str(attempt),**report))
        write(dispatch/"provenance.json",dict(fingerprint=original["fingerprint"],provenance=provenance))
        def refreshed(_,identifier,*args,**kwargs):
            mode=next(c["initialization"] for c in cases if c["id"]==identifier)
            return dict(copy.deepcopy(gates[mode]),git_commit=current)
        gate=stack.enter_context(patch.object(post,"check_preparation",side_effect=refreshed))
        def retained(receipt):
            return dict(JobState="RUNNING",JobId=receipt["job"],WorkDir=str(source),Partition="compute",
                        NumCPUs="2",MinMemoryNode="64G",TimeLimit="01:00:00",TresPerNode="gres:gpu:1",ExitCode="0:0",RunTime="00:01:00")
        live=stack.enter_context(patch.object(post,"validate_submitted_job",side_effect=retained))
        stack.enter_context(patch.object(core,"validate_submitted_job"))
        yield SimpleNamespace(root=root,matrix=matrix,path=matrix_path,pair=pair,cases=cases,gates=gates,
                              original=original,dispatch=dispatch,gate=gate,live=live,scope=scope,source=source)


class PredictionSubmissionTests(unittest.TestCase):
    def test_all_sixteen_pairs_keep_original_training_and_only_plan_cpu_outputs(self):
        for task in ["bandgap","classification","dielectric","spectrum"]:
            for provider in ["cgcnn","alignn","mace","nequip"]:
                with self.subTest(task=task,provider=provider),original_dispatch(task,provider) as f:
                    before=copy.deepcopy(f.matrix)
                    plan=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                    self.assertEqual(f.matrix,before);self.assertEqual(f.gate.call_count,2)
                    self.assertEqual(plan["formal_training_runs_submitted"],0)
                    self.assertEqual(len(plan["stages"]),4)
                    for index,item in enumerate(plan["stages"]):
                        self.assertEqual(item["resources"]["gpus"],0)
                        self.assertIn('CUDA_VISIBLE_DEVICES=""',item["script"])
                        self.assertIn("scripts/assess_prediction.py",item["script"])
                        self.assertEqual(item["depends_on"],item["case_id"]+(":train" if index%2==0 else ":post"))
                        self.assertEqual(item["resources"]["budget_seconds"],259200 if index%2==0 else 14400)

    def test_original_receipt_script_scope_and_preparation_corruption_rejected(self):
        for change in ["receipt","intent","token","script","gate","plan","dispatch","matrix","source","scope"]:
            with self.subTest(change=change),original_dispatch() as f:
                first=f.cases[0]["id"];claim=Path("runs/arxiv-v1/launches")/first
                if change in ["receipt","token"]:
                    r=json.loads((claim/"launch.json").read_text());r["submission_token" if change=="token" else "job"]="foreign"
                    write(claim/"launch.json",r)
                elif change=="intent":
                    r=json.loads((claim/"submission-intent.json").read_text());r["parent_slurm_job"]="902";write(claim/"submission-intent.json",r)
                elif change=="script":(claim/"request.sh").write_bytes(b"foreign script")
                elif change=="gate":f.gate.side_effect=lambda *a,**k:dict(f.gates["pretrained"],git_commit="b"*40,counts={})
                elif change=="plan":
                    r=copy.deepcopy(f.original);r["stages"][0]["resources"]["gpus"]=0;write(f.dispatch/"attempts/901/plan.json",r)
                elif change=="dispatch":
                    r=json.loads((f.dispatch/"latest.json").read_text());r["status"]="submission_failed";write(f.dispatch/"latest.json",r)
                elif change=="matrix":write(f.path,{})
                elif change=="source":f.original["provenance"]["python"]="foreign";write(f.dispatch/"attempts/901/plan.json",f.original)
                else:f.scope["training_seeds"]=[123,456]
                with self.assertRaises((ValueError,RuntimeError)):post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")

    def test_no_training_submission_idempotent_cpu_receipts_and_dependencies(self):
        with original_dispatch() as f:
            originals={str(p):p.read_bytes() for c in f.cases for p in (Path("runs/arxiv-v1/launches")/c["id"]).iterdir()}
            ids=iter([3001,3002,3003,3004])
            calls=[]
            def scheduler(argv,**kwargs):
                calls.append(argv);return SimpleNamespace(returncode=0,stdout=str(next(ids)).encode(),stderr=b"")
            with patch.object(core.subprocess,"run",side_effect=scheduler):
                result=post.dispatch_post_pair(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                self.assertEqual(result["newly_submitted_cpu_jobs"],4)
                with patch.dict(os.environ,{"SLURM_JOB_ID":"1002"}):
                    again=post.dispatch_post_pair(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                self.assertEqual(again["newly_submitted_cpu_jobs"],0);self.assertEqual(len(calls),4)
            self.assertEqual(result["formal_training_runs_submitted"],0)
            self.assertTrue(all("--gres=gpu:1" not in argv for argv in calls))
            self.assertIn("--dependency=afterok:2001",calls[0]);self.assertIn("--dependency=afterok:3001",calls[1])
            self.assertIn("--dependency=afterok:2002",calls[2]);self.assertIn("--dependency=afterok:3003",calls[3])
            self.assertTrue(all(Path(p).read_bytes()==raw for p,raw in originals.items()))

    def test_ambiguous_partial_submission_never_repeats_unknown_request(self):
        with original_dispatch() as f:
            calls=[]
            def scheduler(argv,**kwargs):
                calls.append(argv)
                return SimpleNamespace(returncode=0,stdout=b"3001" if len(calls)==1 else b"unknown receipt",stderr=b"")
            with patch.object(core.subprocess,"run",side_effect=scheduler):
                with self.assertRaises(RuntimeError):post.dispatch_post_pair(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                with patch.dict(os.environ,{"SLURM_JOB_ID":"1002"}),self.assertRaises(RuntimeError):
                    post.dispatch_post_pair(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            self.assertEqual(len(calls),2)
            claim=Path("runs/arxiv-v1/launches")/f.cases[0]["id"]
            self.assertTrue((claim/"post/launch.json").exists());self.assertFalse((claim/"verify/launch.json").exists())

    def test_runtime_observations_do_not_change_plan_fingerprint(self):
        with original_dispatch() as f:
            first=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            before=f.live.side_effect
            f.live.side_effect=lambda receipt:dict(before(receipt),RunTime="01:00:01",JobState="COMPLETED")
            second=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            self.assertEqual(first["fingerprint"],second["fingerprint"])
            self.assertNotEqual(first["training_observations"],second["training_observations"])

    def test_purged_receipt_requires_complete_bound_artifacts_and_preserves_known_dependency(self):
        with original_dispatch() as f:
            first=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            def context(_,identifier):
                job="2001" if identifier==f.cases[0]["id"] else "2002"
                return dict(formal=dict(slurm_job_id=job,git_commit="a"*40),
                    trained=dict(execution=dict(slurm=dict(SLURM_JOB_ID=job))),verified_training=dict(completed_epochs=300),input_sha256={})
            f.live.side_effect=core.ReceiptNotRetained("purged")
            with patch("universal_gnn.benchmarks.prediction_assessment.runtime.formal_context",side_effect=context):
                plan=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                self.assertIsNone(plan["stages"][0]["depends_on"])
                for index,case in enumerate(f.cases):
                    write(Path("runs/arxiv-v1/launches")/case["id"]/"post/launch.json",dict(dependency="afterok:"+str(2001+index)))
                resumed=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                self.assertEqual(resumed["fingerprint"],first["fingerprint"])
            with patch("universal_gnn.benchmarks.prediction_assessment.runtime.formal_context",side_effect=ValueError("incomplete")):
                with self.assertRaises(ValueError):post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")

    def test_foreign_owner_resource_failure_never_uses_purged_fallback(self):
        with original_dispatch() as f:
            with patch("universal_gnn.benchmarks.prediction_assessment.runtime.formal_context") as fallback:
                f.live.side_effect=RuntimeError("foreign token/owner")
                with self.assertRaises(RuntimeError):post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                fallback.assert_not_called()
                f.live.side_effect=lambda receipt:dict(WorkDir=str(f.source),Partition="compute",NumCPUs="1",MinMemoryNode="64G",TimeLimit="01:00:00",TresPerNode="gres:gpu:1")
                with self.assertRaises(ValueError):post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
                fallback.assert_not_called()

    def test_scope_environment_budgets_and_existing_output_are_strict(self):
        for task,seed in [("forcefield",123),("generation",123),("bandgap",456)]:
            with self.subTest(task=task,seed=seed),original_dispatch(task,seed=seed) as f:
                with self.assertRaises(ValueError):post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
        with original_dispatch() as f:
            for budget in [0,-1,True,1.5,float("inf")]:
                with self.subTest(budget=budget),self.assertRaises(ValueError):
                    post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901",post_seconds=budget)
            with patch.object(post,"partition_maximum",return_value=3600),self.assertRaises(ValueError):
                post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            with patch.object(post.sys,"prefix","wrong"),self.assertRaises(ValueError):
                post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            plan=post.build_post_plan(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            Path(plan["stages"][0]["output"]).mkdir(parents=True)
            with patch.object(core.subprocess,"run") as submit,self.assertRaises(FileExistsError):
                post.dispatch_post_pair(f.matrix,f.pair,matrix_path=f.path,dispatch_job="901")
            submit.assert_not_called()

    def test_stage_names_legacy_script_and_cli_slurm_guard(self):
        self.assertEqual([core.stage_kind(p) for p in ["train","quality","assessment","post","verify"]],
                         ["formal","generation-quality","generation-assessment","prediction-post","prediction-verify"])
        with self.assertRaises(ValueError):core.stage_kind("foreign")
        self.assertEqual(request_script(["python","script.py"]),request_script(["python","script.py"],repository=Path.cwd()))
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):post.checked_training_receipts({},"fixture",matrix_path="matrix",dispatch_job="1")
            with patch.object(sys,"argv",["submit_prediction_assessment.py","matrix","--matrix-sha256","0"*64,"--pair","fixture","--dispatch-job","1"]):
                with self.assertRaises(SystemExit) as error:
                    runpy.run_path(str(Path(__file__).resolve().parents[1]/"scripts/submit_prediction_assessment.py"),run_name="__main__")
                self.assertEqual(error.exception.code,2)

    def test_real_receipt_validator_uses_prediction_names_owner_and_token(self):
        for phase in ["post","verify"]:
            receipt=dict(job="5001",phase=phase,case_id="fixture",submission_token="ugnn-"+"a"*32)
            raw="JobId=5001 JobName=ugnn-prediction-"+phase+"-fixture UserId=xmz(1001) JobState=PENDING Comment="+receipt["submission_token"]
            with self.subTest(phase=phase),patch.object(core.getpass,"getuser",return_value="xmz"):
                with patch.object(core.subprocess,"check_output",return_value=raw):
                    self.assertEqual(core.validate_submitted_job(receipt)["JobId"],"5001")
                for bad in [raw.replace("xmz(","other("),raw.replace("prediction-","generation-"),raw.replace("Comment=ugnn-","Comment=foreign-")]:
                    with patch.object(core.subprocess,"check_output",return_value=bad),self.assertRaises(RuntimeError):
                        core.validate_submitted_job(receipt)


if __name__=="__main__":unittest.main()
