"""Pure metadata controls; numerical geometry replay belongs to CPU Slurm."""

import copy
from contextlib import contextmanager, ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.generation.assessment import (
    assess_generation_case, assess_saved_quality, compare_metrics,
)
from universal_gnn.benchmarks.generation.execution import verify_quality
from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.generative.protocol import condition_indices

generation_fixture = runpy.run_path(str(Path(__file__).with_name("test_generation_execution.py")))["generation_fixture"]


@contextmanager
def diagnostic_fixture():
    with generation_fixture() as (root, trained, gate, events, result, rows):
        ids = ["fixture-" + str(i) for i in range(96)]
        records = [dict(id=identifier, group=identifier) for identifier in ids]
        source = Path(gate["config"]["dataset"]["path"])
        source.write_text("".join(json.dumps(dict(id=identifier, numbers=[20,22,8,8,8],
            positions=[[0.,0.,0.]]*5, cell=[[4.,0.,0.],[0.,4.,0.],[0.,0.,4.]], pbc=[True]*3))+"\n" for identifier in ids),encoding="utf-8")
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        official = {identifier:"train" if i<64 else "validation" if i<80 else "test" for i,identifier in enumerate(ids)}
        manifest = create_manifest(records,source_sha256=source_sha,official=official)
        manifest_path = Path(gate["config"]["dataset"]["split_manifest"])
        manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
        config = trained["config"]
        config["generation_prior"]["statistics"]["structures"] = 64
        config["dataset"].update(sha256=source_sha,split_manifest_sha256=canonical_digest(manifest))
        trained.update(selected_structures=64,available_structures=96)
        trained["heldout"]["selection"]["tracker"]["manifest_sha256"] = canonical_digest(manifest)
        result.update(requested_samples=8,attempted=8,draws_per_condition=1,selected_test_conditions=8,
            training_structures=64,declared_training_structures=64,available_test_conditions=16,
            meets_v1_sample_count=False,source_sha256=source_sha,manifest_sha256=canonical_digest(manifest))
        test_ids=ids[80:];selected=condition_indices(test_ids,count=8,seed=456)
        rows=[];digest=hashlib.sha256()
        for index in selected:
            payload=json.dumps(["ugnn-generation-sample-v1",456,test_ids[index],0],separators=(",",":")).encode()
            digest.update(payload+b"\n")
            rows.append(dict(condition_id=test_ids[index],draw=0,
                sampling_seed=int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")%(2**63),structure=None,
                quality=dict(geometrically_valid=False,reason="synthetic invalid observation",unique=None,
                             novel_to_train=None,matches_assigned_reference=False,normalized_rms=None)))
        result["condition_sha256"]=digest.hexdigest()
        Path(result["samples"]).write_text("".join(json.dumps(row)+"\n" for row in rows),encoding="utf-8")
        gate.update(counts=dict(train=64,validation=16,test=16),source_structures=96,
                    quality_protocol=dict(samples=8,draws_per_condition=1,seed=456))
        train_path,quality_path=root/"training-report.json",root/"quality-metrics.json"
        train_path.write_text(json.dumps(trained),encoding="utf-8")
        quality_path.write_text(json.dumps(result),encoding="utf-8")
        yield root, trained, gate, result, train_path, quality_path


class GenerationAssessmentTests(unittest.TestCase):
    def test_metric_comparison_preserves_null_booleans_counts_and_finite_values(self):
        expected=dict(count=8,valid=False,conditional=None,value=.125,nested=[1.,2.])
        compare_metrics(copy.deepcopy(expected),expected)
        for key,value in [("count",8.),("valid",0),("conditional",0.),("value",math.nan),("value",.2),
                          ("nested",[1.])]:
            with self.subTest(field=key,value=value):
                changed=copy.deepcopy(expected);changed[key]=value
                with self.assertRaises(ValueError):compare_metrics(changed,expected)

    def test_diagnostic_must_be_explicit_and_never_claims_formal_sample_count(self):
        with diagnostic_fixture() as (_,trained,gate,result,_,_):
            accepted=verify_quality(result,trained,gate,diagnostic=True)
            self.assertEqual(accepted["attempted"],8)
            with self.assertRaises(ValueError):verify_quality(result,trained,gate)
            result["meets_v1_sample_count"]=True
            with self.assertRaises(ValueError):verify_quality(result,trained,gate,diagnostic=True)

    def test_formal_integrity_rejects_a_smaller_protocol_even_with_a_true_flag(self):
        with generation_fixture() as (_,trained,gate,_,result,_):
            gate["quality_protocol"]["samples"]=8
            with self.assertRaisesRegex(ValueError,"frozen formal1000/5"):
                verify_quality(result,trained,gate)

    def test_guards_reject_login_missing_formal_binding_and_existing_outputs(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):assess_saved_quality("none","none","none")
            with self.assertRaises(RuntimeError):assess_generation_case({},"none","none")
        with patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}),diagnostic_fixture() as (root,_,_,_,train,quality):
            with self.assertRaises(ValueError):assess_saved_quality(train,quality,root/"new")
            with self.assertRaises(FileExistsError):assess_saved_quality(train,quality,root,diagnostic=True)

    def test_partial_source_wrong_prior_and_reduced_steps_are_rejected(self):
        for corruption in ("source","prior","steps","count"):
            with self.subTest(corruption=corruption),patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}),diagnostic_fixture() as (root,trained,_,_,train,quality):
                if corruption=="source":Path(trained["config"]["dataset"]["path"]).write_text("partial\n",encoding="utf-8")
                if corruption=="prior":trained["config"]["generation_prior"]["statistics"]["structures"]=63
                if corruption=="steps":trained["config"]["task"]["sampling"]["steps"]=20
                if corruption=="count":trained["selected_structures"]=63
                train.write_text(json.dumps(trained),encoding="utf-8")
                with self.assertRaises((ValueError,json.JSONDecodeError)):
                    assess_saved_quality(train,quality,root/"new",diagnostic=True)
                self.assertFalse((root/"new").exists())

    def test_metadata_runner_preserves_original_files_and_diagnostic_scope(self):
        with diagnostic_fixture() as (root,_,_,_,train,quality),ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}))
            prefix="universal_gnn.benchmarks.generation.assessment."
            stack.enter_context(patch(prefix+"check_scoring_runtime",return_value=dict(git_commit="a"*40)))
            fake=dict(samples_rescored=8,training_structures=64,metrics={},interpretation="synthetic backend; metadata control only")
            stack.enter_context(patch(prefix+"recompute_saved",return_value=fake))
            stack.enter_context(patch.dict(sys.modules,{"resource":SimpleNamespace(RUSAGE_SELF=0,
                getrusage=lambda _:SimpleNamespace(ru_maxrss=0))}))
            before=(train.read_bytes(),quality.read_bytes())
            report=assess_saved_quality(train,quality,root/"assessment",diagnostic=True)
            self.assertEqual(report["status"],"passed")
            self.assertEqual(report["scope"],"diagnostic")
            self.assertFalse(report["formal_generation_quality_verified"])
            self.assertFalse(report["model_deserialized"])
            self.assertEqual(report["new_samples_generated"],0)
            self.assertEqual(before,(train.read_bytes(),quality.read_bytes()))

    def test_mid_assessment_mutation_fails_and_keeps_failure_evidence(self):
        with diagnostic_fixture() as (root,_,_,_,train,quality),ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}))
            prefix="universal_gnn.benchmarks.generation.assessment."
            stack.enter_context(patch(prefix+"check_scoring_runtime",return_value={}))
            stack.enter_context(patch.dict(sys.modules,{"resource":SimpleNamespace()}))
            def mutate(*_):
                quality.write_text("changed during fake backend",encoding="utf-8")
                return dict(samples_rescored=8)
            stack.enter_context(patch(prefix+"recompute_saved",side_effect=mutate))
            with self.assertRaisesRegex(ValueError,"inputs changed"):
                assess_saved_quality(train,quality,root/"failed",diagnostic=True)
            report=json.loads((root/"failed/report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"],"failed")
            self.assertFalse(report["formal_generation_quality_verified"])

    def test_formal_case_requires_completed_quality_before_reading_training(self):
        with diagnostic_fixture() as (root,_,_,_,_,_),patch.dict(os.environ,{"SLURM_JOB_ID":"fixture"}):
            case=dict(run_directory=str(root))
            spec=dict(case=case,counts={},source_structures=18928,matrix_sha256="a"*64,quality_protocol={})
            gate=dict(spec,case=case)
            (root/"generation-gate.json").write_text(json.dumps(gate),encoding="utf-8")
            (root/"formal-status.json").write_text(json.dumps(dict(status="quality_running")),encoding="utf-8")
            with patch("universal_gnn.benchmarks.generation.assessment.generation_case",return_value=spec):
                with self.assertRaisesRegex(ValueError,"completed frozen"):
                    assess_generation_case({},"fixture",root/"new")
            self.assertFalse((root/"new").exists())


if __name__ == "__main__":
    unittest.main()
