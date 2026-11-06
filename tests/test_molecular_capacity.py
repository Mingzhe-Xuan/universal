"""Pure schedule/receipt controls; mocked CUDA metadata is never runtime evidence."""

import copy
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from universal_gnn.benchmarks.molecular import capacity, mixed, schedule, worker


def probe():
    return dict(indices=[0,1,2,3,4],worst_indices=[1,3],warmup_batches=2,measure_batches=100,
                coverage=dict(verified_full_cuda_training_scan=True,verified_full_training_scan=True))


def mixed_report(batch=4,device="cuda:0"):
    return dict(version=1,status="passed",policy="full_batch_mixed_extremes_v1",batch_size=batch,
        measured_batches=100,warmup_batches=2,measured_structures=100*batch,covered_worst_indices=[1,3],
        complete_training_structures=900,within_batch_mixing=batch>1,formal_training_runs=0,
        model_state_changed=dict(backbone=True,readout=True),actual_device=device,cuda_capacity=device.startswith("cuda"),
        elapsed_seconds=2.,peak_allocated_bytes=100,peak_reserved_bytes=200,
        minimum_parameter_gradient_norms=dict(backbone=1.,readout=2.))


def measured_worker(batch=4):
    return dict(version=1,status="passed",stage="complete",phase="train",batch_size=batch,
        worker_kind="molecular_homogeneous_and_mixed_v1",selected_training_structures=900,
        coverage=probe()["coverage"],completed_worst_indices=[1,3],all_declared_worst_cases_completed=True,
        base_capacity=dict(measured_batches=100,measured_structures=100*batch),
        mixed_capacity=mixed_report(batch),measured_batches=200,measured_structures=200*batch)


class MolecularCapacityTests(unittest.TestCase):
    def fake_orchestration(self, model, *, cpu_probe=False, bad_physics=False):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root=Path(temporary);official=model!="custom_knn_gcn"
            modes=["pretrained","scratch"] if official else ["scratch"]
            configs={mode:dict(backbone=dict(name=model,implementation="official" if official else "legacy",initialization=mode),
                batch_size=4,seed=123,structures="all",max_atoms=None,dtype="float32",device="cuda") for mode in modes}
            spec=dict(model=model,official=official,configs=configs,reference_config=configs[modes[0]],
                counts=dict(train=900,validation=100,test=99000),definition_sha256="a"*64)
            value=probe();value["coverage"]["verified_full_cuda_training_scan"]=not cpu_probe
            evidence=dict(common_batch_size=4,successful_workers=[measured_worker() for _ in range(4 if official else 1)])
            for index,entry in enumerate(evidence["successful_workers"]):
                mode=modes[index%len(modes)]
                entry["execution"]=dict(official=dict(initialization=mode,parameter_coverage=0. if mode=="scratch" else 1.,
                    buffer_coverage=0. if mode=="scratch" else 1.,state_layout_verified=True))
            def graph_scan(name,output,**kwargs):
                self.assertEqual(name,model);self.assertEqual(kwargs,dict(device="cuda"));output.mkdir()
                (output/"probe.json").write_text(json.dumps(value))
                for mode,config in configs.items():(output/("config."+mode+".json")).write_text(json.dumps(config))
                graph=dict(graph_definition=dict(native_graph=dict(artifact_sha256={})))
                (output/"report.json").write_text(json.dumps(graph));return graph
            def run_capacity(config,output,**kwargs):
                self.assertEqual(kwargs["worker_module"],capacity.WORKER);output.mkdir()
                for mode,value in configs.items():(output/("config."+mode+".resolved.json")).write_text(json.dumps(value))
                if not official:(output/"config.resolved.json").write_text(json.dumps(configs["scratch"]))
                return dict(passed=True)
            primary=root/"primary.json";primary.write_text(json.dumps(dict(registry=dict(artifacts={model:dict(files={})}))))
            values=dict(selected_group=lambda name:copy.deepcopy(spec),device_context=lambda name:dict(git_commit="b"*40),
                scan_molecular_graphs=graph_scan,checked_graph_metadata=lambda *args,**kwargs:None,
                run_paired_capacity=run_capacity,run_preflight=run_capacity,
                verify_capacity_evidence=lambda *args,**kwargs:evidence,single_worker_evidence=lambda *args,**kwargs:evidence,
                checked_config=lambda *args,**kwargs:None,check_artifact_identity=lambda *args,**kwargs:None,
                physical_checks=lambda *args:dict(passed=not bad_physics,dtype="torch.float32",device="cuda:0",
                    checks={key:dict(passed=not bad_physics,required=True) for key in ["forces_finite_difference","stress_finite_difference"]}))
            for name,mocked_callable in values.items():stack.enter_context(patch.object(capacity,name,mocked_callable))
            stack.enter_context(patch.object(capacity,"PRIMARY_PATH",primary))
            stack.enter_context(patch.object(capacity.shutil,"disk_usage",return_value=SimpleNamespace(free=30*1024**3)))
            stack.enter_context(patch.dict(os.environ,SLURM_JOB_ID="metadata-only-mocked-not-runtime"))
            output=root/"output"
            if cpu_probe or bad_physics:
                with self.assertRaises(ValueError):capacity.prepare_molecular_capacity(model,output)
                self.assertEqual(json.loads((output/"report.json").read_text())["status"],"failed")
            else:
                report=capacity.prepare_molecular_capacity(model,output)
                self.assertEqual(report["status"],"passed")
                self.assertFalse(report["formal_training_ready"])
                self.assertFalse(report["original_package_parity_verified"])
                self.assertEqual(report["formal_training_runs"],0)

    def test_mocked_orchestration_covers_four_pairs_and_single_plugin_without_readiness_claim(self):
        for name in ["cgcnn","alignn","mace","nequip","custom_knn_gcn"]:
            with self.subTest(model=name):self.fake_orchestration(name)

    def test_mocked_cpu_probe_and_failed_physics_cannot_be_accepted(self):
        self.fake_orchestration("cgcnn",cpu_probe=True)
        self.fake_orchestration("custom_knn_gcn",bad_physics=True)

    def test_all_batch_sizes_retain_warmup_full_measurements_and_each_extreme(self):
        for batch in [1,2,4,8]:
            rows=list(schedule.mixed_probe_batches(probe(),batch))
            self.assertEqual(len(rows),102)
            self.assertEqual([row["phase"] for row in rows[:2]],["warmup"]*2)
            self.assertTrue(all(len(row["indices"])==batch for row in rows))
            self.assertEqual({row["indices"][0] for row in rows[2:]},{1,3})
            if batch>1:self.assertTrue(all(len(set(row["indices"]))>=2 for row in rows[2:]))
            if batch>2:self.assertTrue(all(any(i in [0,2,4] for i in row["indices"]) for row in rows[2:]))
            schedule.checked_mixed_capacity(mixed_report(batch),probe(),batch)

    def test_more_than100_extremes_increases_real_measurements(self):
        value=dict(indices=list(range(120)),worst_indices=list(range(110)),warmup_batches=2,measure_batches=100)
        rows=list(schedule.mixed_probe_batches(value,4))
        self.assertEqual(len(rows),113)
        self.assertEqual({row["indices"][0] for row in rows[2:]},set(range(110)))

    def test_single_extreme_mixes_with_distinct_ordinary_and_one_record_refused(self):
        value=dict(probe(),worst_indices=[1])
        self.assertTrue(all(len(set(row["indices"]))>=2 for row in list(schedule.mixed_probe_batches(value,2))[2:]))
        with self.assertRaises(ValueError):list(schedule.mixed_probe_batches(dict(probe(),indices=[1],worst_indices=[1]),2))

    def test_batch_one_is_never_labelled_within_batch_mixing(self):
        value=mixed_report(1);schedule.checked_mixed_capacity(value,probe(),1)
        value["within_batch_mixing"]=True
        with self.assertRaises(ValueError):schedule.checked_mixed_capacity(value,probe(),1)

    def test_cpu_diagnostic_explicitly_cannot_be_cuda_capacity(self):
        value=mixed_report(device="cpu")
        schedule.checked_mixed_capacity(value,probe(),4,require_cuda=False)
        with self.assertRaises(ValueError):schedule.checked_mixed_capacity(value,probe(),4)
        value["cuda_capacity"]=True
        with self.assertRaises(ValueError):schedule.checked_mixed_capacity(value,probe(),4,require_cuda=False)

    def test_short_mismatched_nonfinite_and_component_failure_receipts_refused(self):
        changes=[("version",True),("batch_size",True),("measured_batches",99),("warmup_batches",1),
            ("measured_structures",399),("covered_worst_indices",[1]),("complete_training_structures",899),
            ("formal_training_runs",1),("actual_device","cuda:bogus"),("elapsed_seconds",float("nan")),
            ("peak_allocated_bytes",0),("model_state_changed",dict(backbone=False,readout=True)),
            ("minimum_parameter_gradient_norms",dict(backbone=0.,readout=2.))]
        for key,wrong in changes:
            with self.subTest(key=key),self.assertRaises(ValueError):
                value=mixed_report();value[key]=wrong;schedule.checked_mixed_capacity(value,probe(),4)

    def test_aggregate_workers_require_both_phases_and_full_bound_coverage(self):
        evidence=dict(common_batch_size=4,successful_workers=[measured_worker()])
        self.assertEqual(capacity.validate_workers(evidence,probe()),4)
        for key,wrong in [("worker_kind","legacy"),("selected_training_structures",899),
                          ("measured_batches",100),("completed_worst_indices",[1]),("status","failed")]:
            bad=copy.deepcopy(evidence);bad["successful_workers"][0][key]=wrong
            with self.subTest(key=key),self.assertRaises(ValueError):capacity.validate_workers(bad,probe())
        bad=copy.deepcopy(evidence);bad["successful_workers"][0]["mixed_capacity"]=mixed_report(device="cpu")
        with self.assertRaises(ValueError):capacity.validate_workers(bad,probe())

    def test_numerical_entrypoints_require_slurm_before_imports(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):mixed.run_mixed_capacity({}, {}, "unused")
            with self.assertRaises(RuntimeError):capacity.prepare_molecular_capacity("cgcnn","unused")
            with self.assertRaises(RuntimeError):worker.execute(dict(config=dict(device="cuda")),{},"unused")
        self.assertNotIn("torch",sys.modules)

    def test_single_preflight_typed_oom_chain_and_file_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);config=dict(batch_size=4,backbone=dict(name="plugin:example"))
            reports=[]
            for index,batch in enumerate([4,2]):
                directory=root/str(index);directory.mkdir()
                value=dict(version=1,batch_size=batch,phase="train",status="cuda_oom" if index==0 else "passed")
                if index==0:value["error_type"]="cuda_out_of_memory"
                (directory/"request.json").write_text(json.dumps(dict(config=dict(config,batch_size=batch),probe=probe(),phase="train")))
                (directory/"result.json").write_text(json.dumps(value))
                reports.append(dict(directory=str(directory),batch_size=batch,worker=value,
                    status=value["status"],returncode=42 if index==0 else 0))
            value=dict(status="passed",passed=True,probe=probe(),initial_batch_size=4,final_batch_size=2,config=config,attempts=reports)
            (root/"report.json").write_text(json.dumps(value))
            self.assertEqual(capacity.single_worker_evidence(root,probe())["common_batch_size"],2)
            value["attempts"][0]["returncode"]=1;(root/"report.json").write_text(json.dumps(value))
            with self.assertRaises(ValueError):capacity.single_worker_evidence(root,probe())

    def test_clean_process_imports_no_numerical_packages(self):
        code="import sys;sys.path.insert(0,'src');from universal_gnn.benchmarks.molecular import schedule,mixed,worker,capacity;assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable,"-S","-c",code],cwd=Path(__file__).resolve().parents[1],check=True)
