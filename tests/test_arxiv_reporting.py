"""Small protocol-only archive fixtures; never scientific training/quality evidence."""

import copy
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_prediction_assessment import physics_fixture
from universal_gnn.benchmarks.experiments.registry import DATASETS
from universal_gnn.benchmarks.preflight import write_json as atomic_write_json
from universal_gnn.benchmarks.reporting import evidence, runtime
from universal_gnn.engine.evaluation.metrics import BinaryClassificationMetrics


def scope_ids():
    return [f"seed-123--{task}--{model}--{mode}" for task in ["classification", "bandgap", "dielectric", "spectrum", "forcefield", "generation"]
        for model in ["cgcnn", "alignn", "mace", "nequip"] for mode in ["pretrained", "scratch"]]


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, value)


@contextmanager
def fixture(*, legacy=False):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);base=root/"accepted";base.mkdir()
        scope=root/"scope.json";write_json(scope,dict(training_seeds=[123],expected_training_runs=48,active_case_ids=scope_ids()))
        cases=[]
        for number,mode in enumerate(["pretrained","scratch"],1):
            model,task=("mace","forcefield") if legacy else ("cgcnn","spectrum")
            case=f"seed-123--{task}--{model}--{mode}"
            folder=base/case;folder.mkdir()
            source_sha,counts=DATASETS["mlearn-forcefield" if legacy else "jarvis-phonon-dos"]
            train,val,test=counts
            config=dict(seed=123,epochs=300,structures="all",max_atoms=None,dtype="float32",batch_size=4,
                backbone=dict(name=model,initialization=mode),task=dict(kind="forcefield",supervised_outputs=["total_energy","forces"]) if legacy else dict(kind="supervised",property="spectrum"),
                dataset=dict(sha256=source_sha,split_manifest_sha256="b"*64,bindings=dict(total_energy=dict(unit="eV"))))
            metrics={"spectrum":dict(mae=0. if number==1 else .2,rmse=.3,structures=test)}
            if legacy:
                metrics={"total_energy":dict(mae=.1),"forces":dict(mae=.2),"energy_per_atom":dict(mae=.3,unit="eV/atom")}
            job="968" if legacy and mode=="pretrained" else str(number+10)
            costs=dict(wall_seconds=100.+number,peak_gpu_allocated_bytes=1000,peak_gpu_reserved_bytes=2000,peak_process_rss_bytes=3000,final_artifact_bytes=4000)
            held=dict(declared_train_structures=train,validation_structures=val,test_structures=test,structures=test,
                source_structures=sum(counts),checkpoint_role="validation_best",partition="test",selection=dict(best_sha256="a"*64),metrics=metrics)
            trained=dict(passed=True,config=config,execution=dict(git_commit="c"*40,slurm=dict(SLURM_JOB_ID=job)),
                completed_epochs=40,selected_structures=train,available_structures=sum(counts),heldout=held,
                components=dict(backbone=dict(trainable_parameters=10,effective_trainable_upper_bound=8)))
            write_json(folder/"report.json",trained)
            status=dict(status="passed",case_id=case,slurm_job_id=job,completed_epochs=40,**costs)
            write_json(folder/"formal-status.json",status)
            proof=dict(status="passed",scientific_postevaluation_verified=True,case_id=case,job=job,completed_epochs=40,best_epoch=10,
                best_checkpoint_sha256="a"*64,metrics=metrics,resource_costs=costs,
                archived_sha256={"report.json":evidence.sha(folder/"report.json"),"formal-status.json":evidence.sha(folder/"formal-status.json")})
            if legacy and mode=="pretrained":
                proof.pop("status");proof.pop("case_id");proof.pop("job");proof.update(formal_case_id=case,formal_job=job)
                old=copy.deepcopy(trained);old["selected_structures"]=64;old["heldout"]["declared_train_structures"]=64
                write_json(folder/"pilot/report.json",old)
                proof["archived_sha256"]["pilot/report.json"]=evidence.sha(folder/"pilot/report.json")
                post=dict(status="passed",stage="complete",case_id=case,slurm_job_id="993",test_ids_verified=164,
                    best_checkpoint_sha256="a"*64,training_commit="c"*40,inference_structures=1566,
                    inference_prediction_sha256="d"*64,inference_prediction_bytes=5000,wall_seconds=2.,peak_process_rss_bytes=1000,
                    rescored=copy.deepcopy(metrics))
                post["rescored"]["energy_per_atom"].pop("unit")
                physical=physics_fixture("forcefield",["train-1","train-2"])
                independent=dict(status="passed",slurm_job_id="1002",structures=1566,all_ordered_ids_match_source=True,
                    completion_marker_verified=True,prediction_sha256="d"*64,prediction_bytes=5000,source_sha256=source_sha,wall_seconds=.5)
                write_json(base/"supplements/arxiv-v1/mace-full-postevaluation-993/report.json",post)
                write_json(base/"supplements/arxiv-v1/mace-full-postevaluation-993/trained-best-physics.json",physical)
                write_json(base/"supplements/arxiv-v1/mace-inference-verification-1002/report.json",independent)
                write_json(base/"gates-verified.json",dict(mace993=dict(trained_best_cpu_physics=True),inference1002=independent))
            write_json(folder/"verified.json",proof)
            cases.append(dict(case_id=case,job=job,proof=case+"/verified.json"))
        index=base/"index.json";write_json(index,dict(status="passed",formal_cases_submitted=48,formal_training_runs_independently_verified=2,cases=cases))
        with patch.object(runtime,"SCOPE_SHA",evidence.sha(scope)):
            yield root,index,scope,cases


class ArxivReportingTests(unittest.TestCase):
    def test_complete48_slots24_pairs_with_only_accepted_scientific_rows(self):
        with fixture() as (_,index,scope,__):
            result=runtime.build_summary(index,scope)
            self.assertEqual((len(result["rows"]),len(result["pairs"]),result["accepted_cases"],result["missing_cases"],result["complete_pairs"]),(48,24,2,46,1))
            self.assertEqual(sum(row["metrics"] is None for row in result["rows"]),46)
            pair=next(p for p in result["pairs"] if p["status"]=="complete")
            self.assertEqual(pair["differences"]["spectrum.mae"],dict(pretrained=0.,scratch=.2,pretrained_minus_scratch=-.2))
            self.assertEqual(result["training_seeds"],[123])

    def test_tampered_archive_or_escaped_path_is_rejected(self):
        for change in ["bytes","traversal","absolute"]:
            with self.subTest(change=change),fixture() as (root,index,scope,cases):
                folder=index.parent/cases[0]["case_id"]
                if change=="bytes":write_json(folder/"report.json",dict(tampered=True))
                else:
                    proof=json.loads((folder/"verified.json").read_text(encoding="utf8"))
                    proof["archived_sha256"]={("../outside.json" if change=="traversal" else str(root/"outside.json")):"a"*64}
                    write_json(folder/"verified.json",proof)
                with self.assertRaises(ValueError):runtime.build_summary(index,scope)

    def test_duplicate_wrong_seed_and_nonaccepted_proofs_stop_export(self):
        for change in ["duplicate","seed","not_scientific","case"]:
            with self.subTest(change=change),fixture() as (_,index,scope,cases):
                data=json.loads(index.read_text(encoding="utf8"))
                if change=="duplicate":data["cases"][1]=copy.deepcopy(data["cases"][0])
                elif change=="seed":data["cases"][0]["case_id"]=cases[0]["case_id"].replace("123","456")
                else:
                    path=index.parent/cases[0]["proof"];proof=json.loads(path.read_text(encoding="utf8"))
                    proof["scientific_postevaluation_verified"]=change!="not_scientific"
                    if change=="case":proof["case_id"]=cases[1]["case_id"]
                    write_json(path,proof)
                write_json(index,data)
                with self.assertRaises(ValueError):runtime.build_summary(index,scope)

    def test_partial_pilot_and_conflicting_full_training_reports_are_not_promoted(self):
        for change in ["pilot","conflict"]:
            with self.subTest(change=change),fixture() as (_,index,scope,cases):
                folder=index.parent/cases[0]["case_id"];report=json.loads((folder/"report.json").read_text(encoding="utf8"))
                proof=json.loads((folder/"verified.json").read_text(encoding="utf8"))
                if change=="pilot":
                    report["selected_structures"]=64;write_json(folder/"report.json",report)
                    proof["archived_sha256"]["report.json"]=evidence.sha(folder/"report.json")
                else:
                    report["config"]["batch_size"]=2;write_json(folder/"another/report.json",report)
                    proof["archived_sha256"]["another/report.json"]=evidence.sha(folder/"another/report.json")
                write_json(folder/"verified.json",proof)
                with self.assertRaises(ValueError):runtime.build_summary(index,scope)

    def test_protocol_mismatch_and_cost_record_mismatch_are_rejected(self):
        for change in ["batch","dataset","cost"]:
            with self.subTest(change=change),fixture() as (_,index,scope,cases):
                folder=index.parent/cases[1]["case_id"];proof=json.loads((folder/"verified.json").read_text(encoding="utf8"))
                report=json.loads((folder/"report.json").read_text(encoding="utf8"))
                if change=="batch":report["config"]["batch_size"]=2
                elif change=="dataset":report["config"]["dataset"]["split_manifest_sha256"]="e"*64
                else:proof["resource_costs"]["wall_seconds"]=1.
                write_json(folder/"report.json",report);proof["archived_sha256"]["report.json"]=evidence.sha(folder/"report.json")
                write_json(folder/"verified.json",proof)
                with self.assertRaises(ValueError):runtime.build_summary(index,scope)

    def test_missing_costs_are_null_final_disk_never_becomes_peak_or_throughput(self):
        with fixture() as (_,index,scope,__):
            result=runtime.build_summary(index,scope);row=next(r for r in result["rows"] if r["costs"])
            cost=row["costs"]
            for key in ["peak_disk_bytes","isolated_inference_seconds","cpu_postprocess_physics_allsource_wall_seconds","cpu_independent_verification_seconds"]:
                self.assertIsNone(cost[key])
            self.assertEqual(cost["final_artifact_bytes"],4000)
            self.assertEqual(cost["components"]["backbone"]["effective_trainable_upper_bound"],8)
            text=runtime.markdown(result);self.assertIn("unavailable",text);self.assertIn("not peak disk",text)

    def test_legacy_formal_pilot_and_separate_scientific_evidence_are_bound(self):
        with fixture(legacy=True) as (_,index,scope,__):
            result=runtime.build_summary(index,scope)
            row=next(r for r in result["rows"] if r["case_id"]=="seed-123--forcefield--mace--pretrained")
            self.assertEqual(row["counts"]["train"],1309)
            self.assertEqual(row["evidence"]["source_format"],"legacy_968_plus_993_1002")
            self.assertEqual(row["costs"]["cpu_postprocess_physics_allsource_wall_seconds"],2.)
            self.assertEqual(row["costs"]["cpu_independent_verification_seconds"],.5)
            self.assertTrue(any("mace-inference-verification-1002" in name for name in result["input_sha256"]))

    def test_legacy_wrong_physics_or_inference_binding_is_rejected(self):
        for change in ["physics","inference","unit"]:
            with self.subTest(change=change),fixture(legacy=True) as (_,index,scope,cases):
                if change=="physics":
                    path=index.parent/"supplements/arxiv-v1/mace-full-postevaluation-993/trained-best-physics.json"
                    report=json.loads(path.read_text(encoding="utf8"));report["checks"].pop("stress_finite_difference")
                elif change=="inference":
                    path=index.parent/"supplements/arxiv-v1/mace-inference-verification-1002/report.json"
                    report=json.loads(path.read_text(encoding="utf8"));report["prediction_sha256"]="f"*64
                else:
                    path=index.parent/cases[0]["case_id"]/"verified.json"
                    report=json.loads(path.read_text(encoding="utf8"));report["metrics"]["energy_per_atom"]["unit"]="unknown"
                write_json(path,report)
                with self.assertRaises(ValueError):runtime.build_summary(index,scope)

    def test_scope_sha_and_existing_output_are_not_silently_accepted(self):
        with fixture() as (root,index,scope,__):
            output=root/"export";result=runtime.write_summary(index,scope,output)
            self.assertEqual(json.loads((output/"summary.json").read_text(encoding="utf8"))["input_sha256"],result["input_sha256"])
            with self.assertRaises(FileExistsError):runtime.write_summary(index,scope,output)
            scope.write_text("{}",encoding="utf8")
            with self.assertRaises(ValueError):runtime.build_summary(index,scope)

    def test_one_accepted_initialization_keeps_pair_and_other_slots_incomplete(self):
        with fixture() as (_,index,scope,__):
            data=json.loads(index.read_text(encoding="utf8"));data["cases"].pop();data["formal_training_runs_independently_verified"]=1
            write_json(index,data);result=runtime.build_summary(index,scope)
            self.assertEqual(result["accepted_cases"],1);self.assertEqual(result["complete_pairs"],0)
            pair=next(p for p in result["pairs"] if p["model"]=="cgcnn" and p["task"]=="spectrum")
            self.assertEqual(pair["status"],"incomplete");self.assertEqual(len(pair["missing"]),1);self.assertEqual(pair["differences"],{})

    def test_unknown_accepted_generation_schema_is_rejected_instead_of_dropped(self):
        with fixture() as (_,index,scope,cases):
            data=json.loads(index.read_text(encoding="utf8"));entry=data["cases"][0]
            identifier="seed-123--generation--cgcnn--pretrained";entry["case_id"]=identifier
            path=index.parent/entry["proof"];proof=json.loads(path.read_text(encoding="utf8"));proof["case_id"]=identifier
            write_json(path,proof);write_json(index,data)
            with self.assertRaisesRegex(ValueError,"generation proof"):
                runtime.build_summary(index,scope)

    def test_actual_costs_and_metric_values_cannot_be_nan_or_negative(self):
        for value in [float("nan"),-1,True,0]:
            with self.subTest(value=value),fixture() as (_,index,scope,cases):
                path=index.parent/cases[0]["case_id"]/"verified.json";proof=json.loads(path.read_text(encoding="utf8"))
                proof["resource_costs"]["wall_seconds"]=value
                path.write_text(json.dumps(proof),encoding="utf8")
                with self.assertRaises(ValueError):runtime.build_summary(index,scope)
        with self.assertRaises(ValueError):list(runtime.scalar_metrics(dict(x=dict(mae=float("nan")))))
        self.assertEqual(list(runtime.scalar_metrics(dict(x=dict(mae=None)))),[])

    def test_new_process_import_and_cli_help_do_not_load_numerical_modules(self):
        code="import sys;sys.path.insert(0,'src');from universal_gnn.benchmarks.reporting import runtime;assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable,"-S","-c",code],capture_output=True,check=True)
        import os
        env=dict(os.environ,PYTHONPATH=str(Path("src").resolve()))
        result=subprocess.run([sys.executable,"-S","scripts/summarize_arxiv_results.py","--help"],env=env,capture_output=True,text=True,check=True)
        self.assertIn("--index",result.stdout)


@contextmanager
def classification_fixture(auc=(.8, .6)):
    """Declared full counts test only the exporter, never actual model quality."""
    with fixture() as (root, index, scope, cases):
        source_sha, counts = DATASETS["jarvis-gap"]
        train, validation, test = counts
        for position, entry in enumerate(cases):
            folder = index.parent / entry["case_id"]
            identifier = entry["case_id"].replace("--spectrum--", "--classification--")
            entry["case_id"] = identifier
            trained = json.loads((folder / "report.json").read_text(encoding="utf8"))
            trained["config"]["task"] = dict(kind="supervised", property="classification")
            trained["config"]["batch_size"] = 32
            trained["config"]["dataset"].update(sha256=source_sha,
                bindings=dict(classification=dict(key="classification", unit="class")))
            metrics = dict(classification=dict(roc_auc=auc[position], accuracy=.7-position*.1, structures=test))
            trained.update(selected_structures=train, available_structures=sum(counts))
            trained["heldout"].update(declared_train_structures=train, validation_structures=validation,
                test_structures=test, structures=test, source_structures=sum(counts), metrics=metrics)
            write_json(folder / "report.json", trained)
            status = json.loads((folder / "formal-status.json").read_text(encoding="utf8"))
            status["case_id"] = identifier
            write_json(folder / "formal-status.json", status)
            proof = json.loads((folder / "verified.json").read_text(encoding="utf8"))
            proof.update(case_id=identifier, metrics=metrics)
            for name in ["report.json", "formal-status.json"]:
                proof["archived_sha256"][name] = evidence.sha(folder / name)
            write_json(folder / "verified.json", proof)
        data = json.loads(index.read_text(encoding="utf8"))
        data["cases"] = cases
        write_json(index, data)
        yield root, index, scope, cases


class RocAucReportingTests(unittest.TestCase):
    def test_actual_metric_producer_key_and_tied_scores_are_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            for number, (scores, expected) in enumerate([([.1, .2, .3, .4], 1.), ([.5]*4, .5)]):
                with BinaryClassificationMetrics(Path(directory) / (str(number)+".sqlite")) as accumulator:
                    for score, target in zip(scores, [0, 0, 1, 1]):
                        accumulator.update(score, target)
                    measured = accumulator.result()
                self.assertEqual(measured["roc_auc"], expected)
                exported = dict(runtime.scalar_metrics(dict(classification=measured)))
                self.assertEqual(exported["classification.roc_auc"], expected)

    def test_complete_classification_pair_keeps_original_auc_and_signed_difference(self):
        with classification_fixture() as (_, index, scope, __):
            summary = runtime.build_summary(index, scope)
            pair = next(row for row in summary["pairs"] if row["status"] == "complete")
            self.assertEqual(pair["task"], "classification")
            self.assertEqual(pair["differences"]["classification.roc_auc"],
                dict(pretrained=.8, scratch=.6, pretrained_minus_scratch=.8-.6))
            self.assertIn("classification.roc_auc", runtime.markdown(summary))
            rows = [row for row in summary["rows"] if row["status"] == "independently_accepted"]
            self.assertEqual([row["metrics"]["classification"]["roc_auc"] for row in rows], [.8, .6])
            self.assertTrue(all(row["counts"] == dict(train=60823, validation=7590, test=7580) for row in rows))

    def test_single_class_null_auc_is_retained_without_an_invented_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            with BinaryClassificationMetrics(Path(directory) / "single.sqlite") as accumulator:
                for target in [1, 1]:
                    accumulator.update(.75, target)
                measured = accumulator.result()
            self.assertIsNone(measured["roc_auc"])
            self.assertNotIn("classification.roc_auc", dict(runtime.scalar_metrics(dict(classification=measured))))
        with classification_fixture(auc=(None, None)) as (_, index, scope, __):
            summary = runtime.build_summary(index, scope)
            pair = next(row for row in summary["pairs"] if row["status"] == "complete")
            self.assertNotIn("classification.roc_auc", pair["differences"])
            rows = [row for row in summary["rows"] if row["status"] == "independently_accepted"]
            self.assertTrue(all(row["metrics"]["classification"]["roc_auc"] is None for row in rows))

    def test_nonfinite_and_boolean_auc_is_rejected_instead_of_silently_omitted(self):
        for value in [float("nan"), float("inf"), True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                list(runtime.scalar_metrics(dict(classification=dict(roc_auc=value))))


if __name__=="__main__":unittest.main()
