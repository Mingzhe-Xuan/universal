"""Campaign CLI exports only seed123; input inspection is mocked, no bulk work."""

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from test_arxiv_experiment_definitions import registry_fixture
from universal_gnn.benchmarks.experiments import registry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_arxiv_matrix.py"


class SingleSeedMatrixCLITests(unittest.TestCase):
    def invoke(self, output, *, slurm=True):
        main = runpy.run_path(str(SCRIPT))["main"]
        source = registry_fixture()
        before = copy.deepcopy(source)
        environment = {k: v for k, v in os.environ.items() if k != "SLURM_JOB_ID"}
        if slurm:
            environment["SLURM_JOB_ID"] = "metadata-cli-test"
        with patch.dict(os.environ, environment, clear=True), \
                patch("sys.argv", [str(SCRIPT), "--output", str(output)]), \
                patch.object(registry, "inspect_registry", return_value=source) as inspect, \
                patch("subprocess.check_output", return_value="a" * 40 + "\n") as git, \
                contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()):
            if slurm and not output.exists():
                main()
                inspect.assert_called_once_with(ROOT)
                git.assert_called_once_with(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
                self.assertEqual(source, before)
                return json.loads(stdout.getvalue())
            with self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code, 2)
            inspect.assert_not_called()
            git.assert_not_called()

    def test_real_campaign_cli_exports_exact_active48_with_no_extra_training_seed(self):
        scope = json.loads((ROOT / "configs/arxiv_v1_scope.json").read_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "single-seed"
            summary = self.invoke(output)
            matrix = json.loads((output / "matrix.json").read_bytes())
            self.assertEqual(summary["cases"], 48)
            self.assertEqual(summary["completed_training_runs"], 0)
            self.assertEqual(matrix["seeds"], [123])
            self.assertEqual(matrix["expected_training_runs"], 48)
            self.assertEqual({c["id"] for c in matrix["cases"]}, set(scope["active_case_ids"]))
            self.assertEqual(len(matrix["pairs"]), 24)
            self.assertEqual(len(list((output / "configs").glob("*.json"))), 48)
            for case in matrix["cases"]:
                config = json.loads((output / case["config_path"]).read_bytes())
                self.assertEqual(config, case["config"])
                self.assertEqual(config["seed"], 123)
                self.assertEqual(case["seed"], 123)
                self.assertEqual(config["structures"], "all")
                self.assertIsNone(config["max_atoms"])
                self.assertEqual(config["epochs"], 300)
                self.assertEqual(config["evaluation"]["patience"], 30)
                self.assertEqual(config["dtype"], "float32")
                if case["task"] == "generation":
                    self.assertEqual(case["generation_quality"]["seed"], 456)
                    self.assertEqual(case["generation_quality"]["samples"], 1000)
                    self.assertEqual(case["generation_quality"]["draws_per_condition"], 5)
            execution = matrix["preparation_execution"]
            self.assertEqual(execution["slurm_job_id"], "metadata-cli-test")
            self.assertEqual(execution["git_commit"], "a" * 40)
            self.assertEqual(execution["source_sha256"][str(SCRIPT.relative_to(ROOT))],
                             hashlib.sha256(SCRIPT.read_bytes()).hexdigest())

    def test_existing_definition_directory_refused_before_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            sentinel = output / "matrix.json"
            sentinel.write_bytes(b"original immutable matrix")
            self.invoke(output)
            self.assertEqual(sentinel.read_bytes(), b"original immutable matrix")

    def test_bulk_preparation_without_slurm_refused_before_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "no-slurm"
            self.invoke(output, slurm=False)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
