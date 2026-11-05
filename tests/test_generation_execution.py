"""Pure orchestration fixtures; no model training or geometric quality claims."""

import copy
from contextlib import contextmanager, ExitStack
import hashlib
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

from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.execution.gates import case_spec
from universal_gnn.benchmarks.generation.evidence import validate_prior, checked_generation_config, check_sampling_capacity
from universal_gnn.benchmarks.generation.execution import (
    generation_case, verify_generation_training, verify_quality, run_generation_case, run_generation_case_quality,
)
from universal_gnn.engine.generative.protocol import condition_indices, fit_volume_prior

registry_fixture = runpy.run_path(str(Path(__file__).with_name("test_arxiv_experiment_definitions.py")))["registry_fixture"]


@contextmanager
def generation_fixture(valid=0):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        numbers = [20, 22, 8, 8, 8]
        records = [dict(id="fixture-" + str(i), numbers=numbers) for i in range(205)]
        source, split = root / "source.jsonl", root / "split.json"
        source.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        manifest = dict(source_count=205, records=[dict(id=r["id"]) for r in records],
                        partitions=dict(train=list(range(4)), validation=[4], test=list(range(5, 205))))
        split.write_text(json.dumps(manifest), encoding="utf-8")
        prior = dict(sampling_volume_source="train_fit", statistics=fit_volume_prior(
            [dict(numbers=numbers, cell=[[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]])] * 4,
            training_fingerprint="a" * 64))
        config = dict(seed=123, structures="all", max_atoms=None, device="cuda", dtype="float32",
            epochs=3, batch_size=2, evaluation=dict(patience=2, min_delta=0.),
            backbone=dict(name="alignn", implementation="official", initialization="pretrained"),
            dataset=dict(path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                         split_manifest=str(split), split_manifest_sha256=canonical_digest(manifest), partition="train"),
            generation_prior=prior, task=dict(kind="generation", sampling=dict(steps=100, inner_steps=2,
                            volume_per_atom=prior["statistics"]["volume_per_atom"])))
        best, last = root / "best.bin", root / "last.bin"
        best.write_bytes(b"synthetic best identity; never deserialize")
        last.write_bytes(b"synthetic last identity; never deserialize")
        pred = root / "predictions.jsonl"
        values = dict(fractional_score=[[0., 0., 0.]] * 5, cell_score=[[0.] * 6])
        pred.write_text("".join(json.dumps(dict(id=r["id"], noise_phase="test", predictions=values,
                                              targets=values)) + "\n" for r in records[5:]), encoding="utf-8")
        history = [dict(epoch=i, loss=1. / i) for i in range(1, 4)]
        tracker = dict(history=history, best_epoch=3, best_loss=1. / 3, bad_epochs=0,
                       manifest_sha256=canonical_digest(manifest))
        events = [e for row in history for e in [dict(event="validation", structures=1, **row),
                                               dict(event="epoch", structures=4, minibatches=2, **row)]]
        trained = dict(passed=True, checkpoint_reload=True, config=config,
            data_fingerprint="a" * 64, completed_epochs=3, requested_epochs=3, selected_structures=4,
            available_structures=205, resume=dict(path=None, kind="none", completed_epochs_before=0),
            history=[r["loss"] for r in history], backbone_gradient_norms=[1.] * 3,
            reload_verification=dict(state_exact=True, deterministic_algorithms=True),
            execution=dict(git_commit="b" * 40, official=dict(initialization="pretrained", parameter_coverage=1.)),
            best_checkpoint=str(best), checkpoint=str(last), heldout=dict(structures=200, validation_structures=1,
                declared_train_structures=4, source_structures=205, partition="test", checkpoint_role="validation_best",
                source_sha256=config["dataset"]["sha256"], predictions=str(pred),
                selection=dict(tracker=tracker, best_sha256=hashlib.sha256(best.read_bytes()).hexdigest())))
        gate = dict(config=config, counts=dict(train=4, validation=1, test=200), source_structures=205,
                    common_batch_size=2, training_prior=prior, case=dict(initialization="pretrained"),
                    quality_protocol=dict(samples=1000, draws_per_condition=5, seed=456),
                    matrix_sha256="c" * 64, git_commit="b" * 40, versions={}, probed_sample_batch_seconds=1.)
        ids = [r["id"] for r in records[5:]]
        selected = condition_indices(ids, count=200, seed=456)
        rows, digest = [], hashlib.sha256()
        for i in selected:
            for draw in range(5):
                payload = json.dumps(["ugnn-generation-sample-v1", 456, ids[i], draw], separators=(",", ":")).encode()
                digest.update(payload + b"\n")
                positive = len(rows) < valid
                rows.append(dict(condition_id=ids[i], draw=draw,
                    sampling_seed=int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63),
                    structure=dict(numbers=numbers, positions=[[0., 0., 0.]] * 5,
                                   cell=[[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]], pbc=[True] * 3) if positive else None,
                    quality=dict(geometrically_valid=positive, reason=None if positive else "synthetic invalid observation",
                                 unique=positive if positive else None, novel_to_train=positive if positive else None,
                                 matches_assigned_reference=positive, normalized_rms=.1 if positive else None)))
        samples = root / "samples.jsonl"
        samples.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        result = dict(execution_complete=True, meets_v1_sample_count=True, requested_samples=1000, attempted=1000,
            draws_per_condition=5, seed=456, sampling_batch_size=1, training_structures=4, declared_training_structures=4,
            full_training_partition=True, available_test_conditions=200, partition="test", checkpoint_role="validation_best",
            checkpoint_sha256=trained["heldout"]["selection"]["best_sha256"],
            source_sha256=config["dataset"]["sha256"], manifest_sha256=config["dataset"]["split_manifest_sha256"],
            training_prior=prior, sampling=config["task"]["sampling"], samples=str(samples),
            condition_sha256=digest.hexdigest(), selected_test_conditions=200,
            geometry_definition=dict(three_dimensional_pbc=True, positive_volume=True,
                                    fractional_coordinates_in_unit_cell=True, minimum_periodic_distance_angstrom=.5),
            matching=dict(implementation="pymatgen.StructureMatcher", ltol=.3, stol=.5, angle_tol=10.,
                          primitive_cell=False, scale=True, attempt_supercell=False, symmetric=True,
                          comparator="ElementComparator", rms_unit="normalized by (V/N)^(1/3)"),
            conditioning="given composition and atom count", geometrically_valid=valid, geometric_validity=valid / 1000,
            unique_valid_structures=valid, uniqueness_among_valid=1. if valid else None,
            novel_valid_structures=valid, novelty_among_valid=1. if valid else None,
            valid_samples_with_training_seen_composition=valid,
            novelty_among_valid_with_training_seen_composition=1. if valid else None,
            valid_composition_groups=int(valid > 0), valid_samples_with_repeated_generated_composition=valid if valid > 1 else 0,
            matched_assigned_references=valid, paired_match_rate=valid / 1000,
            paired_match_rate_among_valid=1. if valid else None, mean_normalized_rms_among_matches=.1 if valid else None,
            distribution_wasserstein_1=dict(volume_per_atom_angstrom3=0. if valid else None, density_g_cm3=0. if valid else None))
        yield root, trained, gate, events, result, rows


class GenerationExecutionTests(unittest.TestCase):
    def test_all_twenty_four_full_generation_recipes_are_explicit(self):
        matrix = build_matrix(registry_fixture())
        cases = [c for c in matrix["cases"] if c["task"] == "generation"]
        self.assertEqual(len(cases), 24)
        for case in cases:
            with self.subTest(case=case["id"]):
                spec = generation_case(matrix, case["id"])
                self.assertEqual(spec["counts"], dict(train=11356, validation=3787, test=3785))
                self.assertEqual(spec["quality_protocol"]["samples"], 1000)
                with self.assertRaises(ValueError):
                    case_spec(matrix, case["id"])
        with self.assertRaises(ValueError):
            generation_case(matrix, next(c["id"] for c in matrix["cases"] if c["task"] == "bandgap"))

    def test_prior_and_config_bind_complete_train_and_sampling_volume(self):
        with generation_fixture() as (_, _, gate, _, _, _):
            prior, config = gate["training_prior"], gate["config"]
            expected = copy.deepcopy(config)
            expected.pop("generation_prior")
            expected["task"]["sampling"].pop("volume_per_atom")
            checked_generation_config(config, expected, 2, gate["counts"], prior)
            for key, value in [("structures", 3), ("fitted_partition", "test"), ("training_fingerprint", "bad"),
                               ("volume_per_atom", -1.), ("log_volume_per_atom_std", math.nan)]:
                with self.subTest(field=key):
                    changed = copy.deepcopy(prior); changed["statistics"][key] = value
                    with self.assertRaises(ValueError): validate_prior(changed, 4)
            changed = copy.deepcopy(config); changed["task"]["sampling"]["volume_per_atom"] *= 2
            with self.assertRaises(ValueError): checked_generation_config(changed, expected, 2, gate["counts"], prior)

    def test_sampling_capacity_binds_phase_inputs_and_final_stats(self):
        with generation_fixture() as (root, _, gate, _, _, _):
            capacity = root / "sample-capacity"; capacity.mkdir()
            train = {m: copy.deepcopy(gate["config"]) for m in ("pretrained", "scratch")}
            for mode, config in train.items(): config["backbone"]["initialization"] = mode
            originals = copy.deepcopy(train)
            for config in originals.values():
                config.pop("generation_prior"); config["task"]["sampling"].pop("volume_per_atom")
            inputs = copy.deepcopy(train)
            for config in inputs.values(): config["batch_size"] = 4
            report = dict(configs=inputs, phase="sample", input_config_sha256={m: canonical_digest(c) for m,c in inputs.items()},
                          resolved_config_sha256={m: canonical_digest(c) for m,c in train.items()})
            (capacity / "report.json").write_text(json.dumps(report), encoding="utf-8")
            for mode,config in train.items(): (capacity / ("config."+mode+".resolved.json")).write_text(json.dumps(config), encoding="utf-8")
            with patch("universal_gnn.benchmarks.generation.evidence.verify_capacity_evidence", return_value=dict(common_batch_size=2)) as verifier:
                check_sampling_capacity(root, originals, train, {}, gate["counts"], gate["training_prior"],
                                        dict(initial_batch_size=4, measure_batches=5, warmup_batches=1))
                self.assertEqual(verifier.call_args.kwargs["minimum_batches"], 5)
                report["phase"] = "train"
                (capacity / "report.json").write_text(json.dumps(report), encoding="utf-8")
                with self.assertRaises(ValueError):
                    check_sampling_capacity(root, originals, train, {}, gate["counts"], gate["training_prior"],
                                            dict(initial_batch_size=4, measure_batches=5, warmup_batches=1))

    def test_complete_denoising_training_and_scratch_provenance(self):
        with generation_fixture() as (_, trained, gate, events, _, _):
            self.assertEqual(verify_generation_training(trained, gate, events)["test_structures"], 200)
            trained["execution"]["official"] = dict(initialization="scratch", parameter_coverage=0., buffer_coverage=0., state_layout_verified=True)
            gate["case"]["initialization"] = "scratch"
            gate["config"]["backbone"]["initialization"] = "scratch"
            verify_generation_training(trained, gate, events)
            trained["execution"]["official"]["parameter_coverage"] = 1.
            with self.assertRaises(ValueError): verify_generation_training(trained, gate, events)

    def test_training_rejects_missing_epochs_nonfinite_losses_and_wrong_noise(self):
        for corruption in ("epoch", "validation_order", "loss", "prior", "noise", "test_count"):
            with self.subTest(corruption=corruption), generation_fixture() as (_, trained, gate, events, _, _):
                if corruption == "epoch": events.pop()
                if corruption == "validation_order": events[0]["epoch"] = 2
                if corruption == "loss": trained["history"][0] = math.nan
                if corruption == "prior": trained["data_fingerprint"] = "d" * 64
                if corruption == "test_count": trained["heldout"]["structures"] = 16
                if corruption == "noise":
                    p = Path(trained["heldout"]["predictions"])
                    p.write_text(p.read_text(encoding="utf-8").replace('"test"', '"train"', 1), encoding="utf-8")
                with self.assertRaises(ValueError): verify_generation_training(trained, gate, events)

    def test_all_thousand_attempts_count_even_when_none_are_valid(self):
        for valid in (0, 5):
            with self.subTest(valid=valid), generation_fixture(valid) as (_, trained, gate, _, result, _):
                accepted = verify_quality(result, trained, gate)
                self.assertEqual(accepted["attempted"], 1000)
                self.assertEqual(accepted["selected_test_conditions"], 200)

    def test_quality_rejects_protocol_summary_source_and_draw_tampering(self):
        changes = [lambda r:r.update(attempted=8), lambda r:r.update(draws_per_condition=1),
                   lambda r:r.update(checkpoint_sha256="f"*64), lambda r:r.update(source_sha256="f"*64),
                   lambda r:r.update(sampling={"steps":20}), lambda r:r["matching"].update(scale=False),
                   lambda r:r.update(geometric_validity=1.), lambda r:r.update(uniqueness_among_valid=0.)]
        with generation_fixture() as (_, trained, gate, _, result, rows):
            for index, change in enumerate(changes):
                with self.subTest(change=index):
                    bad=copy.deepcopy(result); change(bad)
                    with self.assertRaises(ValueError): verify_quality(bad, trained, gate)
            for field,value in [("draw",5), ("sampling_seed",0), ("condition_id","foreign")]:
                with self.subTest(field=field):
                    bad=copy.deepcopy(rows); bad[0][field]=value
                    Path(result["samples"]).write_text("".join(json.dumps(r)+"\n" for r in bad),encoding="utf-8")
                    with self.assertRaises(ValueError): verify_quality(result, trained, gate)
            Path(result["samples"]).write_text("".join(json.dumps(r)+"\n" for r in rows[:-1]),encoding="utf-8")
            with self.assertRaises(ValueError): verify_quality(result, trained, gate)

    def test_quality_rejects_wrong_condition_geometry_format_and_distribution(self):
        with generation_fixture(5) as (_, trained, gate, _, result, rows):
            for field,value in [("numbers",[8]*5),("positions",[[math.nan]*3]*5),("cell",[[1.]])]:
                with self.subTest(field=field):
                    bad=copy.deepcopy(rows); bad[0]["structure"][field]=value
                    Path(result["samples"]).write_text("".join(json.dumps(r)+"\n" for r in bad),encoding="utf-8")
                    with self.assertRaises(ValueError): verify_quality(result, trained, gate)
            Path(result["samples"]).write_text("".join(json.dumps(r)+"\n" for r in rows),encoding="utf-8")
            result["distribution_wasserstein_1"]["density_g_cm3"]=math.nan
            with self.assertRaises(ValueError): verify_quality(result, trained, gate)

    def test_no_slurm_and_bad_quality_budget_reject_before_model_imports(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError): run_generation_case({}, "unused", "unused", budget_seconds=1)
            with self.assertRaises(RuntimeError): run_generation_case_quality({}, "unused", budget_seconds=1)
        with patch.dict(os.environ, {"SLURM_JOB_ID":"fixture"}):
            for budget in (0, -1, math.nan, True):
                with self.subTest(budget=budget), self.assertRaises(ValueError):
                    run_generation_case_quality({}, "unused", budget_seconds=budget)

    def test_quality_failure_retry_and_live_claim_preserve_training_and_attempts(self):
        with generation_fixture() as (root, trained, gate, events, result, _), ExitStack() as stack:
            case = dict(initialization="pretrained", run_directory=str(root))
            gate["case"] = case
            expected = copy.deepcopy(gate["config"])
            expected.pop("generation_prior"); expected["task"]["sampling"].pop("volume_per_atom")
            spec = dict(case=case, counts=gate["counts"], source_structures=gate["source_structures"],
                        configs={"pretrained": expected}, quality_protocol=gate["quality_protocol"],
                        matrix_sha256=gate["matrix_sha256"])
            status = dict(status="training_passed_quality_pending", formal_training_runs_completed=1,
                          generation_quality_complete=False, independent_postevaluation_verified=False,
                          last_checkpoint_sha256=hashlib.sha256(Path(trained["checkpoint"]).read_bytes()).hexdigest())
            for name,value in [("generation-gate.json",gate),("report.json",trained),("formal-status.json",status)]:
                (root/name).write_text(json.dumps(value),encoding="utf-8")
            (root/"events.jsonl").write_text("".join(json.dumps(e)+"\n" for e in events),encoding="utf-8")
            prefix = "universal_gnn.benchmarks.generation.execution."
            for name,value in [("generation_case",spec),("installed_versions",{}),
                               ("compatible_sources","b"*40),("allocation_budget",86400.)]:
                stack.enter_context(patch(prefix+name,return_value=value))
            stack.enter_context(patch(prefix+"shutil.disk_usage",return_value=SimpleNamespace(free=30*1024**3)))
            cuda = SimpleNamespace(is_available=lambda:True, reset_peak_memory_stats=lambda:None,
                                   max_memory_allocated=lambda:0,max_memory_reserved=lambda:0)
            resource = SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda _:SimpleNamespace(ru_maxrss=0))
            calls=[]
            def sample(checkpoint, output, **kwargs):
                self.assertEqual(checkpoint,trained["checkpoint"])
                self.assertEqual(kwargs,dict(count=1000,draws_per_condition=5,seed=456,device="cuda"))
                output.mkdir(); (output/"partial.txt").write_text("preserved attempt",encoding="utf-8")
                calls.append(output)
                if len(calls)==1: raise RuntimeError("synthetic interrupted sampler")
                return result
            fake_quality=SimpleNamespace(run_generation_quality=sample)
            stack.enter_context(patch.dict(sys.modules,{"torch":SimpleNamespace(cuda=cuda),"resource":resource,
                "universal_gnn.engine.generative.quality":fake_quality}))
            stack.enter_context(patch.dict(os.environ,{"SLURM_JOB_ID":"fixture-job-1"}))
            active=root/"quality-active"; active.mkdir()
            (active/"owner.json").write_text('{"slurm_job_id":"live-owner"}',encoding="utf-8")
            with self.assertRaises(FileExistsError): run_generation_case_quality({},"fixture",budget_seconds=86400.)
            self.assertEqual(calls,[])
            self.assertEqual(json.loads((active/"owner.json").read_text())["slurm_job_id"],"live-owner")
            (active/"owner.json").unlink(); active.rmdir()
            with self.assertRaisesRegex(RuntimeError,"interrupted sampler"):
                run_generation_case_quality({},"fixture",budget_seconds=86400.)
            failed=json.loads((root/"formal-status.json").read_text())
            self.assertEqual(failed["status"],"quality_failed")
            self.assertEqual(failed["formal_training_runs_completed"],1)
            self.assertTrue((calls[0]/"partial.txt").exists())
            self.assertFalse(active.exists())
            os.environ["SLURM_JOB_ID"]="fixture-job-2"
            completed=run_generation_case_quality({},"fixture",budget_seconds=86400.)
            self.assertEqual(completed["status"],"passed")
            self.assertEqual([r["status"] for r in completed["quality_attempts"]],["failed","passed"])
            self.assertFalse(completed["independent_postevaluation_verified"])
            self.assertTrue(Path(trained["checkpoint"]).exists())
            self.assertTrue(Path(trained["best_checkpoint"]).exists())
            self.assertFalse(active.exists())
            with self.assertRaises(ValueError): run_generation_case_quality({},"fixture",budget_seconds=86400.)
            self.assertEqual(len(calls),2)


if __name__ == "__main__":
    unittest.main()
