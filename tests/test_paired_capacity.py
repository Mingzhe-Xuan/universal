"""Real subprocess control fixtures; no model, Torch import or GPU execution."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.pairing.capacity import run_paired_capacity, select_pair, validate_pair
from universal_gnn.benchmarks.experiments.registry import canonical_digest

WORKER = '''
import json,os,sys
from pathlib import Path
request=json.load(open(sys.argv[1],encoding="utf-8"))
config=request["config"]; mode=config["backbone"]["initialization"]; batch=config["batch_size"]
scenario=os.environ.get("PAIR_FIXTURE_SCENARIO", "stable")
result={"version":1,"batch_size":batch,"phase":request["phase"],"pid":os.getpid()}
if config.get("task",{}).get("kind")=="generation":
 result["resolved_generation"]={"generation_corruption":config["generation_corruption"],
  "generation_prior":config.get("generation_prior"),"sampling":config["task"].get("sampling",{})}
fits=8 if mode=="pretrained" else 4
if scenario=="odd":fits=3 if mode=="pretrained" else 2
if scenario=="one_fails" and mode=="scratch":fits=0
if scenario=="shrink" and "common-01" in sys.argv[2] and mode=="pretrained":fits=2
if scenario=="unknown" and mode=="scratch":
 result.update(status="failed",error_type="RuntimeError",error="CUDA out of memory text alone")
 code=1
elif batch>fits:
 result.update(status="cuda_oom",error_type="cuda_out_of_memory");code=42
else:result.update(status="passed");code=0
with open(os.environ["PAIR_FIXTURE_HISTORY"],"a") as out:
 out.write(json.dumps({"mode":mode,"batch":batch,"pid":os.getpid(),"stage":str(Path(sys.argv[2]).parents[2].name)})+"\\n")
json.dump(result,open(sys.argv[2],"w"));sys.exit(code)
'''


def configurations(batch=32):
    base=dict(seed=123, structures="all", batch_size=batch, device="cuda", dtype="float32", max_atoms=None,
              backbone=dict(name="cgcnn", implementation="official"),
              dataset=dict(path="fixed.jsonl",split_manifest="fixed-split.json",partition="train"),
              task=dict(kind="supervised", property="bandgap"), prediction=dict(head_mode="reset"),
              optimization=dict(train_backbone=True, train_readout=True))
    result={}
    for mode in ("pretrained", "scratch"):
        result[mode]=copy.deepcopy(base);result[mode]["backbone"]["initialization"]=mode
    return result


def matrix_fixture():
    configs=configurations()
    registry={"fixture":"metadata only"}
    return dict(version=1, kind="arxiv_v1_primary_matrix", registry=registry, registry_sha256=canonical_digest(registry),
                pairs=[dict(id="pair",cases=["p","s"])], cases=[dict(id=identifier,pair_id="pair",initialization=mode,
                    config=configs[mode],config_sha256=canonical_digest(configs[mode]))
                    for identifier,mode in [("p","pretrained"),("s","scratch")]])


class PairedCapacityTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        (self.root/"paired_capacity_fixture.py").write_text(WORKER,encoding="utf-8")
        self.history=self.root/"history.jsonl"
        self.environment=patch.dict(os.environ,dict(PYTHONPATH=str(self.root),PAIR_FIXTURE_HISTORY=str(self.history)))
        self.environment.start()

    def tearDown(self):
        self.environment.stop();self.temporary.cleanup()

    def run_pair(self,configs=None,*,scenario="stable",phase="train"):
        configs=configurations() if configs is None else configs
        before=copy.deepcopy(configs)
        with patch.dict(os.environ,dict(PAIR_FIXTURE_SCENARIO=scenario)):
            result=run_paired_capacity(configs,self.root/"pair",probe=dict(indices=[0,3],worst_indices=[3],
                coverage=dict(verified_full_training_scan=True)),phase=phase,worker_module="paired_capacity_fixture")
        self.assertEqual(configs,before)
        self.assertEqual(result,json.loads((self.root/"pair/report.json").read_text()))
        self.assertFalse(result["full_training_graph_coverage_certified"])
        return result

    def test_common_smaller_batch_is_rechecked_in_fresh_processes_for_both(self):
        result=self.run_pair()
        self.assertTrue(result["passed"]);self.assertEqual(result["common_batch_size"],4)
        self.assertEqual([row["final_batch_size"] for row in result["trials"]],[8,4,4,4])
        rows=[json.loads(line) for line in self.history.read_text().splitlines()]
        self.assertEqual(len(rows),9);self.assertEqual(len({row["pid"] for row in rows}),9)
        for mode in ("pretrained","scratch"):
            config=json.loads((self.root/"pair"/result["final_configs"][mode]).read_text())
            self.assertEqual(config["batch_size"],4)
            self.assertEqual(config["backbone"]["initialization"],mode)
            self.assertEqual(result["resolved_config_sha256"][mode],canonical_digest(config))
            self.assertEqual(result["input_config_sha256"][mode],canonical_digest(configurations()[mode]))
        for trial in result["trials"]:
            nested=json.loads((Path(trial["directory"])/'report.json').read_text())
            self.assertEqual(trial["report_sha256"],canonical_digest(nested))

    def test_oom_during_common_recheck_reduces_and_revalidates_both_again(self):
        result=self.run_pair(scenario="shrink")
        self.assertTrue(result["passed"]);self.assertEqual(result["common_batch_size"],2)
        self.assertEqual([row["final_batch_size"] for row in result["trials"]],[8,4,2,4,2,2])
        self.assertEqual([row["stage"] for row in result["trials"]][-2:],["common-02-b2"]*2)

    def test_unequal_odd_initial_batches_and_final_pair_keep_task_settings(self):
        configs=configurations(5);configs["scratch"]["batch_size"]=3
        result=self.run_pair(configs,scenario="odd")
        self.assertEqual(result["common_batch_size"],1)
        self.assertEqual([row["final_batch_size"] for row in result["trials"]],[2,1,1,1])

    def test_batch_one_failure_has_no_top_level_success_configs(self):
        result=self.run_pair(configurations(5),scenario="one_fails")
        self.assertFalse(result["passed"]);self.assertEqual(result["failed_initialization"],"scratch")
        nested=json.loads((self.root/"pair/individual/scratch/report.json").read_text())
        self.assertEqual([row["batch_size"] for row in nested["attempts"]],[5,2,1])
        self.assertFalse(list((self.root/"pair").glob('config.*.resolved.json')))

    def test_unknown_worker_failure_does_not_start_common_checks_or_halve(self):
        result=self.run_pair(scenario="unknown")
        self.assertFalse(result["passed"]);self.assertEqual(len(result["trials"]),2)
        nested=json.loads((self.root/"pair/individual/scratch/report.json").read_text())
        self.assertEqual(len(nested["attempts"]),1)
        self.assertFalse(list((self.root/"pair").glob('config.*.resolved.json')))

    def test_task_mismatch_and_invalid_inputs_fail_before_any_worker(self):
        for field,value in [("seed",456),("dtype","float64"),("structures",10),("device","cpu"),
                            ("max_atoms",64),("batch_size",True),("dataset",dict(path="other.jsonl"))]:
            configs=configurations();configs["scratch"][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                run_paired_capacity(configs,self.root/field,probe=dict(indices=[0]))
        with self.assertRaises(ValueError):validate_pair(dict(pretrained=configurations()["pretrained"]))
        configs=configurations()
        for config in configs.values():config["dataset"]["partition"]="test"
        with self.assertRaises(ValueError):validate_pair(configs)
        with self.assertRaises(ValueError):run_paired_capacity(configurations(),self.root/"sample",probe=dict(indices=[0]),phase="sample")
        self.assertFalse(self.history.exists())
        self.run_pair(configurations(1))
        with self.assertRaises(FileExistsError):
            run_paired_capacity(configurations(),self.root/"pair",probe=dict(indices=[0]))

    def test_only_scratch_native_normalization_can_differ(self):
        configs=configurations()
        for config in configs.values():config["backbone"]["name"]="mace"
        configs["scratch"]["backbone"]["neighbor_statistics"]={"fixture":"not numerical acceptance"}
        validate_pair(configs)
        configs["pretrained"]["backbone"]["neighbor_statistics"]={}
        with self.assertRaises(ValueError):validate_pair(configs)

    def test_selected_matrix_pair_rejects_ambiguous_or_tampered_definitions(self):
        matrix=matrix_fixture();self.assertEqual(select_pair(matrix,"pair"),configurations())
        for mutation in ("registry","config","duplicate","mode","unknown"):
            changed=copy.deepcopy(matrix)
            if mutation=="registry":changed["registry"]["extra"]=True
            elif mutation=="config":changed["cases"][0]["config"]["structures"]=10
            elif mutation=="duplicate":changed["cases"].append(changed["cases"][0])
            elif mutation=="mode":changed["cases"][0]["initialization"]="scratch"
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                select_pair(changed,"unknown" if mutation=="unknown" else "pair")

    def test_sampling_keeps_steps_and_phase_while_matching_its_separate_batch(self):
        configs=configurations(5)
        for config in configs.values():
            config.update(task=dict(kind="generation",sampling=dict(steps=100,inner_steps=2)),generation_corruption="per_structure_v1")
        result=self.run_pair(configs,phase="sample")
        self.assertTrue(result["passed"]);self.assertEqual(result["phase"],"sample")
        for mode in ("pretrained","scratch"):
            final=json.loads((self.root/"pair"/result["final_configs"][mode]).read_text())
            self.assertEqual(final["task"]["sampling"],dict(steps=100,inner_steps=2))

    def test_cli_slurm_guard_and_metadata_import_need_no_numerical_dependencies(self):
        env={**os.environ,"PYTHONPATH":str(Path('src').resolve())};env.pop('SLURM_JOB_ID',None)
        result=subprocess.run([sys.executable,'-S','-m','universal_gnn.benchmarks.pairing.capacity','absent.json',
            '--pair','pair','--probe','absent-probe.json','--output','absent-output'],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn('Slurm',result.stderr);self.assertNotIn('ModuleNotFoundError',result.stderr)
        imported=subprocess.run([sys.executable,'-S','-c','import sys; import universal_gnn.benchmarks.pairing.capacity; assert "torch" not in sys.modules'],
            env=env,capture_output=True,text=True)
        self.assertEqual(imported.returncode,0,imported.stderr)


if __name__=='__main__':unittest.main()
