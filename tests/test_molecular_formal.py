"""Pure protocol fixtures only; no numerical/GPU/formal scientific acceptance."""

import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_arxiv_experiment_definitions import registry_fixture
from test_formal_execution import report_fixture
from test_molecular_capacity import measured_worker, probe
from test_molecular_experiment_definitions import input_fixture
from test_molecular_readiness import working_directory
from test_prediction_assessment import fixture as predictions_fixture
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.execution.gates import file_sha
from universal_gnn.benchmarks.execution.runner import verify_training_report
from universal_gnn.benchmarks.molecular import contracts as molecular_contracts, definitions
from universal_gnn.benchmarks.molecular.formal import contracts, cohorts, gates, runtime, submission
from universal_gnn.benchmarks.molecular.source import COUNTS
from universal_gnn.benchmarks.preflight import write_json


class MolecularFormalTests(unittest.TestCase):
    def setUp(self):
        primary = build_matrix(registry_fixture())
        self.pin = patch.object(definitions, "PRIMARY_SHA", canonical_digest(primary)); self.pin.start(); self.addCleanup(self.pin.stop)
        complete = definitions.build_molecular_definitions(primary, input_fixture(), repository=Path(__file__).resolve().parents[1])
        self.groups = {model: molecular_contracts.molecular_group_spec(primary, complete, model)
            for model in ["cgcnn", "alignn", "mace", "nequip", "custom_knn_gcn"]}
        self.group_patch = patch.object(contracts, "selected_group", side_effect=lambda model: self.groups[model])
        self.group_patch.start(); self.addCleanup(self.group_patch.stop)

    def spec(self, model="cgcnn", mode="pretrained"):
        identifier = ("molecular-plugin--seed-123--forcefield--knn-gcn--scratch" if model == "custom_knn_gcn"
            else "molecular--seed-123--forcefield--" + model + "--" + mode)
        return contracts.selected_case(identifier)

    def timings(self):
        worker = measured_worker(); worker["base_capacity"]["elapsed_seconds"] = 20.
        worker["mixed_capacity"]["elapsed_seconds"] = 30.
        return dict(common_batch_size=4, successful_workers=[copy.deepcopy(worker) for _ in range(4)])

    def test_all_nine_closed_cases_preserve_complete_scope(self):
        count = 0
        for group in self.groups.values():
            for case in group["cases"]:
                spec = contracts.selected_case(case["id"])
                self.assertEqual(spec["case"], case); self.assertEqual(spec["counts"], COUNTS)
                self.assertEqual(case["seed"], 123); self.assertEqual(case["config"]["epochs"], 300)
                count += 1
        self.assertEqual(count, 9)
        for value in ["seed-123--forcefield--cgcnn--pretrained", "molecular--seed-456--forcefield--cgcnn--scratch",
                "molecular--seed-123--bandgap--cgcnn--scratch", "molecular-plugin--seed-123--forcefield--knn-gcn--pretrained"]:
            with self.assertRaises(ValueError): contracts.selected_case(value)

    def test_budget_includes_full_validation_test_and_extra_traversals(self):
        config = self.spec()["case"]["config"]
        budget = contracts.execution_budget(config, self.timings())
        self.assertEqual(budget["workload"], dict(training_batches=67500, validation_batches=7500,
            heldout_batches=24750, additional_training_pass_batches=1125, author_cohort_model_batches=0, author_cohort_saved_rows=1000))
        self.assertEqual(budget["training_equivalent_batches"], 100875)
        self.assertEqual(budget["estimated_execution_seconds"], 100875 * .3)
        self.assertGreaterEqual(budget["budget_seconds"], 1.5 * budget["estimated_execution_seconds"] + 900)
        self.assertFalse(budget["evaluation_throughput_measured"]); self.assertFalse(budget["timing_upper_bound_proven"])
        one = contracts.workload(config, 1)
        self.assertEqual(sum(one[k] for k in ["training_batches", "validation_batches", "heldout_batches", "additional_training_pass_batches"]), 403500)

    def test_budget_rejects_short_timings_changed_scope_and_partition_overflow(self):
        config = self.spec()["case"]["config"]
        for field, value in [("elapsed_seconds", float("nan")), ("elapsed_seconds", 0), ("measured_batches", 99)]:
            bad = self.timings(); bad["successful_workers"][0]["mixed_capacity"][field] = value
            with self.assertRaises(ValueError): contracts.execution_budget(config, bad)
        for key, value in [("epochs", 3), ("seed", 456), ("structures", 10), ("dtype", "float64"), ("max_atoms", 64)]:
            with self.assertRaises(ValueError): contracts.execution_budget(dict(config, **{key: value}), self.timings())
        with self.assertRaises(ValueError): contracts.execution_budget(config, dict(common_batch_size=4, successful_workers=[]))
        with self.assertRaises(ValueError): contracts.execution_budget(config, self.timings(), maximum=3600)
        for batch in [0, True, 1.5]:
            with self.assertRaises(ValueError): contracts.workload(config, batch)

    def test_plugin_initialization_is_closed_and_never_forges_official(self):
        spec = self.spec("custom_knn_gcn", "scratch")
        graph = dict(gnn=dict(path="/home/xmz/universal/runs/source-checkouts/"+"a"*40+"/examples/custom_knn_gcn"))
        gate = dict(kind="formal_molecular_execution_gate", definition_sha256=molecular_contracts.DEFINITION_SHA,
            case=spec["case"], config=spec["case"]["config"], counts=COUNTS, source_structures=100000,
            native_graph=graph, capacity_commit="a"*40)
        trained = dict(execution=dict(official=None, backbone_class="StandardBackbone", gnn_class="MolecularGCN", extensions=dict(gnn={}, graph={})))
        with patch.object(contracts, "plugin_identity") as identity:
            contracts.verify_plugin_initialization(trained, gate); identity.assert_called_once()
            for key, value in [("official", {}), ("backbone_class", "OfficialCGCNNBackbone"), ("gnn_class", "AnotherGNN")]:
                bad = copy.deepcopy(trained); bad["execution"][key] = value
                with self.assertRaises(ValueError): contracts.verify_plugin_initialization(bad, gate)
            for key, value in [("kind", "other"), ("counts", dict(train=10)), ("source_structures", 1000)]:
                with self.assertRaises(ValueError): contracts.verify_plugin_initialization(trained, dict(gate, **{key: value}))
            bad = copy.deepcopy(gate); bad["config"]["epochs"] = 3
            with self.assertRaises(ValueError): contracts.verify_plugin_initialization(trained, bad)

    def test_plugin_uses_every_existing_shared_epoch_reload_and_heldout_check(self):
        with report_fixture("forcefield") as (_, trained, gate, events), patch.object(contracts, "verify_plugin_initialization") as policy:
            trained["execution"]["official"] = None
            result = verify_training_report(trained, gate, events, plugin_backbone=True)
            self.assertEqual(result["test_structures"], 2); policy.assert_called_once()
            for field, value in [("checkpoint_reload", False), ("selected_structures", 2), ("backbone_gradient_norms", [0., 0., 0.])]:
                bad = copy.deepcopy(trained); bad[field] = value
                with self.assertRaises(ValueError): verify_training_report(bad, gate, events, plugin_backbone=True)
            with self.assertRaises(ValueError): verify_training_report(trained, gate, events[:-1], plugin_backbone=True)
            with self.assertRaises((ValueError, AttributeError)): verify_training_report(trained, gate, events)
            with self.assertRaises(ValueError): verify_training_report(trained, gate, events, plugin_backbone=True, frozen_backbone=True)

    @contextmanager
    def gate_fixture(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            spec = self.spec(); root = Path(directory)/"runs"; prep = root/"joint"; cap = root/"capacity"
            prep.mkdir(parents=True); (cap/"graph-scan").mkdir(parents=True)
            terminal = prep/"terminal-parent.json"; write_json(terminal, {})
            opaque = root/"bound.json"; write_json(opaque, dict(original=True))
            for mode, config in spec["configs"].items():
                write_json(prep/("config."+mode+".resolved.json"), config)
                write_json(cap/("config."+mode+".resolved.json"), config)
            write_json(cap/"graph-scan/probe.json", probe())
            write_json(cap/"graph-scan/report.json", dict(graph_definition=dict(native_graph={}, cutoff=6.)))
            saved = dict(version=1, kind="joint_molecular_preparation_evidence", status="passed", preparation_gate_passed=True,
                formal_training_ready=False, formal_training_runs=0, model="cgcnn", counts=COUNTS,
                definition_sha256=molecular_contracts.DEFINITION_SHA, initializations=["pretrained", "scratch"],
                input_sha256={str(opaque): file_sha(opaque)}, versions=dict(test_package=None), git_commit="a"*40,
                capacity_parent=dict(git_commit="a"*40, output=str(cap)), parity_parent=dict(git_commit="a"*40), common_batch_size=4)
            write_json(prep/"report.json", saved)
            with patch.dict(os.environ, SLURM_JOB_ID="123"), patch.object(gates, "selected_case", return_value=spec), \
                    patch.dict(gates.ENVIRONMENTS, cgcnn=Path(sys.prefix).name), patch.object(gates, "successful_parent"), \
                    patch.object(gates, "compatible_sources", return_value="a"*40), \
                    patch.object(gates.subprocess, "check_output", return_value=""), \
                    patch.object(gates.importlib.metadata, "version", return_value=None), \
                    patch.object(gates, "verify_capacity_evidence", return_value=self.timings()):
                yield spec, prep, terminal, saved, opaque

    def test_gate_checks_actual_preparation_scope_all_exports_budget_and_input_sha(self):
        with self.gate_fixture() as (spec, prep, terminal, saved, opaque):
            identifier = spec["case"]["id"]
            result = gates.check_execution_gate(identifier, prep, terminal)
            self.assertTrue(result["formal_training_ready"]); self.assertFalse(result["scientific_quality_accepted"])
            self.assertEqual(result["probed_execution_seconds"], 30262.5)
            with self.assertRaises(ValueError): gates.check_execution_gate(identifier, prep, terminal, budget_seconds=3600)
            for key, value in [("status", "running"), ("preparation_gate_passed", False), ("counts", dict(train=10)),
                    ("initializations", ["pretrained"]), ("formal_training_ready", True)]:
                write_json(prep/"report.json", dict(saved, **{key: value}))
                with self.assertRaises(ValueError): gates.check_execution_gate(identifier, prep, terminal)
            write_json(prep/"report.json", saved); write_json(opaque, dict(original=False))
            with self.assertRaises(ValueError): gates.check_execution_gate(identifier, prep, terminal)

    def test_gate_refuses_modified_export_before_training(self):
        with self.gate_fixture() as (spec, prep, terminal, _, __):
            config = copy.deepcopy(spec["configs"]["scratch"]); config["epochs"] = 3
            write_json(prep/"config.scratch.resolved.json", config)
            with self.assertRaises(ValueError): gates.check_execution_gate(spec["case"]["id"], prep, terminal)

    def test_author_cohort_contract_rejects_partial_duplicate_development_indices(self):
        manifest = dict(counts=COUNTS, records=[None]*100000,
            partitions=dict(train=list(range(900)), validation=list(range(900,1000)), test=list(range(1000,100000))),
            evaluation_cohorts=dict(official_test_01=list(reversed(range(1000,2000)))))
        self.assertEqual(cohorts.cohort_indices(manifest), list(reversed(range(1000,2000))))
        for values in [list(range(1000,1999)), [1000]*1000, list(range(999,1999)), [True]+list(range(1001,2000))]:
            bad = dict(manifest, evaluation_cohorts=dict(official_test_01=values))
            with self.assertRaises(ValueError): cohorts.cohort_indices(bad)
        bad = dict(manifest, partitions=dict(manifest["partitions"], test=list(range(1000,2000))))
        with self.assertRaises(ValueError): cohorts.cohort_indices(bad)

    def test_bounded_author_metric_fixture_preserves_raw_labels_order_units_and_sha(self):
        with predictions_fixture("forcefield") as (root, path, report, _):
            manifest = json.loads(Path(report["config"]["dataset"]["split_manifest"]).read_text(encoding="utf8"))
            indices = list(reversed(manifest["partitions"]["test"]))
            with patch.object(cohorts, "cohort_indices", return_value=indices):
                result = cohorts.rescore_author_cohort(path, root/"author")
                self.assertEqual(result["structures"], 2); self.assertEqual(result["complete_heldout_structures"], 2)
                self.assertEqual(result["ordered_ids"], [manifest["records"][i]["id"] for i in indices])
                self.assertEqual(result["metrics"], report["heldout"]["metrics"])
                self.assertFalse(result["model_execution_performed"])
                self.assertEqual(result["full_prediction_sha256"], file_sha(report["heldout"]["predictions"]))
                self.assertEqual(result["prediction_sha256"], file_sha(root/"author/predictions.jsonl"))

    def test_author_metric_refuses_missing_reordered_malformed_or_changed_labels(self):
        for change in ["missing", "order", "target", "nan", "atoms"]:
            with self.subTest(change=change), predictions_fixture("forcefield") as (root, path, report, rows):
                manifest = json.loads(Path(report["config"]["dataset"]["split_manifest"]).read_text(encoding="utf8"))
                indices = manifest["partitions"]["test"]
                if change=="missing": rows.pop()
                elif change=="order": rows.reverse()
                elif change=="target": rows[0]["targets"]["total_energy"][0][0] += 1
                elif change=="nan": rows[0]["predictions"]["forces"][0][0] = float("nan")
                else: rows[0]["natoms"] += 1
                Path(report["heldout"]["predictions"]).write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf8")
                with patch.object(cohorts, "cohort_indices", return_value=indices):
                    with self.assertRaises(ValueError): cohorts.rescore_author_cohort(path, root/"author")

    def test_nine_plans_have_full_budget_six_exact_stages_without_submitting(self):
        with patch.dict(os.environ, SLURM_JOB_ID="123"), patch.object(submission, "partition_maximum", return_value=None), \
                patch.object(submission, "check_execution_gate") as check:
            for group in self.groups.values():
                for case in group["cases"]:
                    check.return_value = dict(case=case, git_commit="a"*40, budget_seconds=7200)
                    plan = submission.build_submission_plan(case["id"], "runs/joint", "runs/joint/terminal.json", post_seconds=86400, verify_seconds=3600)
                    self.assertEqual(len(plan["stages"]), 6); self.assertEqual(plan["formal_training_runs_submitted"], 0)
                    self.assertEqual([row["phase"] for row in plan["stages"]], ["train", "terminal_train", "post", "terminal_post", "verify", "terminal_verify"])
                    for row in plan["stages"]:
                        self.assertEqual(row["case_id"], case["id"]); self.assertEqual(row["resources"]["gpus"], int(row["phase"]=="train"))
                        self.assertEqual(row["dependency_kind"], "afterany" if row["phase"].startswith("terminal_") else "afterok")
                        self.assertNotIn("--limit", row["script"])
            with self.assertRaises(ValueError): submission.build_submission_plan(case["id"], "runs/a", "runs/b", post_seconds=0, verify_seconds=3600)

    def test_foreign_claim_stops_before_any_sbatch(self):
        case = self.spec()["case"]
        with tempfile.TemporaryDirectory() as directory, working_directory(directory), patch.dict(os.environ, SLURM_JOB_ID="123"), \
                patch.object(submission, "build_submission_plan", return_value=dict(cases=[case], fingerprint="x")), \
                patch.object(submission, "submit_stage") as submit, \
                patch.object(submission.shutil, "disk_usage", return_value=type("Disk", (), dict(free=100*1024**3))()):
            (Path("runs/arxiv-v1/launches")/case["id"]).mkdir(parents=True)
            with self.assertRaises(FileExistsError): submission.dispatch_case(case["id"], "a", "b")
            submit.assert_not_called()

    def test_author_failure_marks_parent_failed_instead_of_leaving_passed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"post"; output.mkdir()
            with patch.object(runtime, "_postprocess_case", return_value=dict(status="passed", input_sha256={})), \
                    patch.object(runtime, "molecular_context", return_value=dict(input_sha256={}, report_path="fake")), \
                    patch.object(runtime, "rescore_author_cohort", side_effect=ValueError("bad cohort")):
                with self.assertRaises(ValueError): runtime.postprocess_molecular_case("fake", output)
            self.assertEqual(json.loads((output/"report.json").read_text(encoding="utf8"))["status"], "failed")

    def test_no_slurm_guards_and_fresh_cli_help_import_no_numerical_modules(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Slurm"): gates.check_execution_gate("bad", "a", "b")
            with self.assertRaisesRegex(RuntimeError, "Slurm"): runtime.run_molecular_case("bad", "a", "b", budget_seconds=3600)
            with self.assertRaisesRegex(RuntimeError, "Slurm"): submission.build_submission_plan("bad", "a", "b", post_seconds=3600, verify_seconds=3600)
        env = dict(os.environ, PYTHONPATH=str(Path("src").resolve()))
        result = subprocess.run([sys.executable, "-S", "scripts/run_molecular_case.py", "--help"], env=env, capture_output=True, text=True, check=True)
        self.assertIn("--preparation-terminal", result.stdout)
        code = "import sys;sys.path.insert(0,'src');from universal_gnn.benchmarks.molecular.formal import runtime,submission;assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, check=True)


if __name__ == "__main__":
    unittest.main()
