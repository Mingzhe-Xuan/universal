"""Pure adversarial preparation checks; fixtures are never numerical evidence."""

import copy
from contextlib import contextmanager
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.molecular.source import COUNTS
from universal_gnn.benchmarks.molecular.readiness import contracts, evidence, runtime


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def capacity():
    spec = dict(model="cgcnn", definition_sha256="a"*64, reference_config=dict(batch_size=4))
    graph = dict(slurm_job_id="100", git_commit="b"*40)
    report = dict(version=1, kind="molecular_cuda_capacity_and_physics", status="passed",
        stage="cuda_capacity_and_physics_only", model="cgcnn", counts=COUNTS,
        definition_sha256=spec["definition_sha256"], cuda_capacity=True, formal_training_runs=0,
        formal_training_ready=False, original_package_parity_verified=False,
        slurm_job_id="100", git_commit="b"*40, graph_report_sha256="e"*64, common_batch_size=4, allocation=dict(gpus=1))
    return report, graph, spec


class MolecularReadinessTests(unittest.TestCase):
    def test_complete_capacity_scope_is_explicit(self):
        report, graph, spec = capacity()
        self.assertEqual(contracts.checked_capacity(report, graph, spec), 4)
        for key, value in [("version", True), ("graph_report_sha256", ""), ("status", "running"), ("stage", "graph_only_complete"),
                ("cuda_capacity", False), ("formal_training_ready", True), ("formal_training_runs", True),
                ("model", "mace"), ("counts", dict(train=899)), ("definition_sha256", "x"*64),
                ("slurm_job_id", "101"), ("git_commit", "c"*40)]:
            broken = dict(report, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                contracts.checked_capacity(broken, graph, spec)
        for value in [True, 0, -1, 5, 4.0]:
            with self.subTest(batch=value), self.assertRaises(ValueError):
                contracts.checked_capacity(dict(report, common_batch_size=value), graph, spec)
        for allocation in [{}, dict(gpus=0), dict(gpus=True)]:
            with self.assertRaises(ValueError):
                contracts.checked_capacity(dict(report, allocation=allocation), graph, spec)

    def test_original_capacity_summary_cannot_be_replaced(self):
        workers = dict(common_batch_size=2, trial_count=4, cuda_oom_attempts=1, successful_workers=[dict(status="passed")])
        report = dict(common_batch_size=2, capacity_evidence={k: v for k,v in workers.items() if k != "successful_workers"})
        contracts.checked_capacity_summary(report, workers)
        for key, value in [("common_batch_size", 4), ("trial_count", 3), ("cuda_oom_attempts", 0)]:
            broken = copy.deepcopy(report); broken["capacity_evidence"][key] = value
            with self.assertRaises(ValueError): contracts.checked_capacity_summary(broken, workers)

    def test_probe_requires_actual_complete_cuda_identity_and100_batches(self):
        rebuilt = dict(indices=[0,1], worst_indices=[0,1], measure_batches=100, warmup_batches=2,
            coverage=dict(structures=900, binding=dict(source_sha256="a"*64)))
        graph = dict(device="cuda:0", graph_definition=dict(provider="cgcnn"), slurm_job_id="100")
        probe = copy.deepcopy(rebuilt)
        probe["coverage"].update(verified_full_training_scan=True, complete_source_graphs=100000,
            kind="complete_molecular_source_and_training_native_graphs", geometry_scope="all_source_and_source_ordered_train",
            device=graph["device"], verified_full_cuda_training_scan=True, model_forward_executed=False,
            graph_definition=graph["graph_definition"], scan_slurm_job_id=graph["slurm_job_id"])
        graph["probe_sha256"] = canonical_digest(probe)
        contracts.checked_probe(probe, rebuilt, graph)
        for key, value in [("verified_full_cuda_training_scan", False), ("structures", 899),
                ("device", "cpu"), ("scan_slurm_job_id", "101"), ("complete_source_graphs", 99999)]:
            broken = copy.deepcopy(probe); broken["coverage"][key] = value
            with self.assertRaises(ValueError): contracts.checked_probe(broken, rebuilt, graph)
        for name, value in [("measure_batches", 99), ("warmup_batches", 1)]:
            broken, source = copy.deepcopy(probe), copy.deepcopy(rebuilt)
            broken[name] = source[name] = value
            new_graph = dict(graph, probe_sha256=canonical_digest(broken))
            with self.assertRaises(ValueError): contracts.checked_probe(broken, source, new_graph)

    def test_task_path_escape_and_modified_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            root = Path(directory); (root/"runs").mkdir()
            good = root/"runs/report.json"; good.write_text("{}", encoding="utf8")
            record = evidence.Evidence(); record.read(good)
            for path in [root/"outside.json", root/"runs/../outside.json", root/"runs"]:
                with self.assertRaises(ValueError): record.path(path)
            good.write_text('{"status":"changed"}', encoding="utf8")
            with self.assertRaises(ValueError): record.unchanged()

    def retained_fixture(self, root):
        directory = root/"runs/capacity"; directory.mkdir(parents=True)
        commit = "a"*40; checkout = "/home/xmz/universal/runs/source-checkouts/"+commit
        def save(path, value): path.write_text(json.dumps(value), encoding="utf8")
        request = directory/"request.sh"; request.write_text("#!/bin/bash\ntrue\n", encoding="utf8")
        entry = dict(state="submitted", formal_training_runs=0, source_checkout=checkout, git_commit=commit,
            job="100", submission_token="ugnn-test", request_path=str(request), request_sha256=evidence.file_sha(request),
            output=str(directory), sbatch_argv=["sbatch", "--no-requeue", "--partition=compute", "--nodelist=node42",
                "--chdir="+checkout, "--comment=ugnn-test", "--cpus-per-task=2", "--mem=16G", "--time=02:00:00",
                "--job-name=ugnn-test", "--nice=0", "--gres=gpu:1"])
        receipt = directory/"receipt.json"; save(receipt, entry)
        report_path = directory/"report.json"
        save(report_path, dict(slurm_job_id="100", git_commit=commit, source_checkout=checkout))
        fields = dict(JobId="100", UserId=getpass.getuser()+"(1)", JobName="ugnn-test", WorkDir=checkout,
            Partition="compute", Requeue="0", NumCPUs="2", MinMemoryNode="16G", TimeLimit="02:00:00",
            Comment="ugnn-test", Nice="0", TresPerNode="gres:gpu:1", ReqNodeList="node42",
            JobState="COMPLETED", ExitCode="0:0")
        terminal = dict(status="retained", successful=True, exit=0, entry=entry, receipt=str(receipt),
            receipt_sha256=evidence.file_sha(receipt), request_sha256=entry["request_sha256"],
            artifact_sha256={str(report_path): evidence.file_sha(report_path)}, fields=fields,
            raw=" ".join(k+"="+v for k,v in fields.items()), observer_slurm_job="101")
        terminal_path = directory/"terminal.json"; save(terminal_path, terminal)
        return terminal_path, report_path, terminal, save

    def test_retained_parent_checks_requests_reports_resources_and_owner(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory), \
                patch.object(evidence, "source_pinned") as pin:
            terminal_path, report_path, original, save = self.retained_fixture(Path(directory))
            self.assertEqual(evidence.successful_parent(evidence.Evidence(), terminal_path, report_path)["job"], "100")
            pin.assert_called_once()
            for key, value in [("successful", False), ("status", "unavailable"), ("exit", 1),
                    ("request_sha256", "f"*64), ("request_sha256", ""), ("receipt_sha256", "f"*64),
                    ("receipt_sha256", ""), ("observer_slurm_job", "100")]:
                save(terminal_path, dict(original, **{key: value}))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    evidence.successful_parent(evidence.Evidence(), terminal_path, report_path)
            for key, value in [("JobState", "FAILED"), ("ExitCode", "1:0"), ("NumCPUs", "1"),
                    ("UserId", "another(2)"), ("TresPerNode", "gres:gpu:0"), ("Comment", "different")]:
                broken = copy.deepcopy(original); broken["fields"][key] = value
                broken["raw"] = " ".join(k+"="+v for k,v in broken["fields"].items()); save(terminal_path, broken)
                with self.subTest(field=key), self.assertRaises(ValueError):
                    evidence.successful_parent(evidence.Evidence(), terminal_path, report_path)
            save(terminal_path, original); report_path.write_text("{}", encoding="utf8")
            with self.assertRaises(ValueError): evidence.successful_parent(evidence.Evidence(), terminal_path, report_path)

    def test_missing_cuda_never_exports_a_ready_configuration(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory), \
                patch.dict(os.environ, SLURM_JOB_ID="500"), \
                patch.object(runtime, "ENVIRONMENTS", {"cgcnn": Path(sys.prefix).name}):
            output = Path(directory)/"runs/check"
            definitions = Path(directory)/"runs/definitions.json"; definitions.parent.mkdir()
            definitions.write_text("{}", encoding="utf8")
            with patch.object(runtime, "DEFINITION_PATH", definitions), patch.object(runtime, "PRIMARY_PATH", definitions), \
                    patch.object(runtime, "selected_group", return_value=dict(definition_sha256=evidence.file_sha(definitions))):
                with self.assertRaises(FileNotFoundError):
                    runtime.check_molecular_readiness("cgcnn", Path(directory)/"runs/absent", "missing",
                        Path(directory)/"runs/missing-parity", "missing", output)
            report = json.loads((output/"report.json").read_text(encoding="utf8"))
            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["preparation_gate_passed"])
            self.assertFalse(report["formal_training_ready"])
            self.assertFalse(list(output.glob("config.*")))

    def test_empty_graph_stream_cannot_certify100000_records(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            root = Path(directory)/"runs/graph"; root.mkdir(parents=True)
            source = root/"source-graph-sizes.jsonl"; source.touch()
            training = root/"training-graph-sizes.jsonl"; training.touch()
            graph = dict(source_graph_rows_sha256=evidence.file_sha(source), training_graph_rows_sha256=evidence.file_sha(training))
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                runtime.graph_rows(evidence.Evidence(), root, graph, dict(partitions=dict(train=[])), [])

    def test_slurm_requirement_precedes_output_creation(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Slurm"):
                runtime.check_molecular_readiness("cgcnn", "a", "b", "c", "d", "never-created")

    def test_fresh_import_and_cli_help_are_numerical_framework_free(self):
        code = "import sys;sys.path.insert(0,'src');from universal_gnn.benchmarks.molecular.readiness import runtime;assert 'torch' not in sys.modules and 'numpy' not in sys.modules"
        subprocess.run([sys.executable, "-S", "-c", code], check=True, capture_output=True)
        env = dict(os.environ, PYTHONPATH=str(Path("src").resolve()))
        result = subprocess.run([sys.executable, "-S", "scripts/check_molecular_readiness.py", "--help"], env=env, check=True, capture_output=True, text=True)
        self.assertIn("--capacity-terminal", result.stdout)


if __name__ == "__main__":
    unittest.main()
