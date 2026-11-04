"""Offline installer gates use stdlib fake subprocesses; never install or import Torch locally."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts/install_official_extras.py"
spec = importlib.util.spec_from_file_location("official_extras_installer", MODULE)
installer = importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class OfficialEnvironmentRestoreTests(unittest.TestCase):
    def fixture(self, root):
        relative = "official-extra-wheelhouse/fixture.whl"
        path = root / "models/official-install" / relative
        path.parent.mkdir(parents=True);path.write_bytes(b"existing-resource")
        resources = [(relative, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())]
        venvs = root / "venvs"
        base = venvs / "universal-base/lib/python3.10/site-packages"
        for name in ("universal", "universal-mace", "universal-official"):
            site = venvs / name / "lib/python3.10/site-packages";site.mkdir(parents=True)
            (site / "ugnn-common-base.pth").write_text(str(base) + "\n")
        return resources, path, venvs, base

    def runner(self, base, calls, *, bad_torch=False, wrong_e3nn_parent=False):
        def execute(command, **options):
            calls.append(command)
            name = Path(command[0]).parent.parent.name
            if "-c" in command:
                payload = dict(torch="0.0" if bad_torch else "2.7.1+cu128", torch_root=str(base),
                               e3nn="0.4.4" if name == "universal-mace" else "0.5.8",
                               e3nn_root=str(base if wrong_e3nn_parent else Path(command[0]).parent.parent / "lib/python3.10/site-packages"))
            else:
                payload = []
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")
        return execute

    def test_missing_corrupt_or_conflicting_inputs_never_invoke_install(self):
        for mode in ("missing", "corrupt", "link", "torch", "e3nn-parent"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder);resources, path, venvs, base = self.fixture(root);calls = []
                if mode == "missing": path.unlink()
                elif mode == "corrupt": path.write_bytes(b"corrupt-resource!")
                elif mode == "link": (venvs / "universal-official/lib/python3.10/site-packages/ugnn-common-base.pth").write_text("unknown-parent\n")
                with self.assertRaises(ValueError):
                    installer.install(root, venvs, resources=resources, runner=self.runner(base, calls, bad_torch=mode == "torch", wrong_e3nn_parent=mode == "e3nn-parent"))
                self.assertFalse(any("install" in command for command in calls))
                self.assertFalse(any("torch" == argument for command in calls for argument in command))

    def test_offline_install_targets_only_official_and_preserves_shared_torch_and_mace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);resources, path, venvs, base = self.fixture(root);calls = []
            report = installer.install(root, venvs, resources=resources, runner=self.runner(base, calls))
            installs = [command for command in calls if "install" in command]
            self.assertEqual(len(installs), 1)
            self.assertEqual(Path(installs[0][0]), venvs / "universal-official/bin/python")
            for flag in ("--no-index", "--no-deps", "--no-cache-dir", "--only-binary=:all:"):
                self.assertIn(flag, installs[0])
            self.assertIn(str(path.resolve()), installs[0])
            self.assertEqual(report["environments"]["universal-mace"]["metadata"]["e3nn"], "0.4.4")
            self.assertEqual(report["status"], "complete")
            self.assertFalse(report["numerical_acceptance"])
            self.assertIn("numerical acceptance still required", report["interpretation"])

    def test_cli_requires_slurm_before_any_scientific_dependency_or_install(self):
        environment = dict(os.environ);environment.pop("SLURM_JOB_ID", None)
        result = subprocess.run([sys.executable, "-S", str(MODULE), "--report", "never-written.json"],
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must run through Slurm", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "existing.json";report.write_text("keep-existing-report")
            refused = subprocess.run([sys.executable, "-S", str(MODULE), "--report", str(report)],
                                     env={**environment, "SLURM_JOB_ID": "guard-fixture"}, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("Report already exists", refused.stderr)
            self.assertEqual(report.read_text(), "keep-existing-report")


if __name__ == "__main__":
    unittest.main()
