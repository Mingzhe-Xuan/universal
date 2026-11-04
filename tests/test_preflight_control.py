"""Pure control-plane tests: subprocess fixtures never import or execute a model."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.preflight import run_preflight


WORKER = '''
import json,os,sys,time
request=json.load(open(sys.argv[1],encoding="utf-8"))
config=request["config"]
mode=config.get("test_mode","capacity")
batch=config["batch_size"]
result={"version":1,"batch_size":batch,"phase":request["phase"],"pid":os.getpid()}
if "fixture_resolved_generation" in config: result["resolved_generation"]=config["fixture_resolved_generation"]
if "fixture_native_worker_fields" in config: result.update(config["fixture_native_worker_fields"])
if mode=="kill": os._exit(137)
if mode=="timeout": time.sleep(5)
if mode=="invalid":
 open(sys.argv[2],"w").write("malformed")
 sys.exit(42)
if mode=="identity": result["batch_size"]=batch+1
if mode=="error":
 result.update(status="failed",error_type="RuntimeError",error="CUDA out of memory text alone is insufficient")
 code=1
elif mode=="mismatch":
 result.update(status="cuda_oom",error_type="ValueError")
 code=42
elif batch>config.get("fits",8):
 result.update(status="cuda_oom",error_type="cuda_out_of_memory")
 code=42
else:
 result.update(status="passed")
 code=0
json.dump(result,open(sys.argv[2],"w"))
sys.exit(code)
'''


class PreflightControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "capacity_fixture.py").write_text(WORKER, encoding="utf-8")
        self.environment = patch.dict(os.environ, {"PYTHONPATH": str(self.root)})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_probe(self, **changes):
        config = {"batch_size": 32, "device": "cuda", **changes}
        before = copy.deepcopy(config)
        report = run_preflight(config, self.root / "probe", probe={"indices": [0, 3]},
                               worker_module="capacity_fixture", timeout=.1 if changes.get("test_mode") == "timeout" else 5)
        self.assertEqual(config, before)
        self.assertEqual(json.loads((self.root / "probe/report.json").read_text()), report)
        return report

    def test_halving_new_processes_and_final_config(self):
        report = self.run_probe()
        self.assertTrue(report["passed"])
        self.assertEqual([a["batch_size"] for a in report["attempts"]], [32, 16, 8])
        self.assertEqual(len({a["worker"]["pid"] for a in report["attempts"]}), 3)
        resolved = json.loads((self.root / "probe/config.resolved.json").read_text())
        self.assertEqual(resolved["batch_size"], 8)
        self.assertEqual(report["effective_batch_size"], 8)

    def test_odd_and_single_batch_failure(self):
        report = self.run_probe(batch_size=5, fits=0)
        self.assertFalse(report["passed"])
        self.assertEqual([a["batch_size"] for a in report["attempts"]], [5, 2, 1])
        self.assertIsNone(report["final_batch_size"])
        self.assertFalse((self.root / "probe/config.resolved.json").exists())

    def test_unknown_failures_never_halve(self):
        for mode in ("kill", "invalid", "identity", "error", "mismatch", "timeout"):
            with self.subTest(mode=mode):
                output = self.root / mode
                report = run_preflight({"device": "cuda", "batch_size": 32, "test_mode": mode}, output,
                                       probe={"indices": [0]}, worker_module="capacity_fixture",
                                       timeout=.1 if mode == "timeout" else 5)
                self.assertFalse(report["passed"])
                self.assertEqual(len(report["attempts"]), 1)
                self.assertFalse((output / "config.resolved.json").exists())

    def test_validation_and_existing_output(self):
        for config, probe in [({"device": "cpu"}, {"indices": [0]}),
                              ({"device": "cuda", "batch_size": True}, {"indices": [0]}),
                              ({"device": "cuda"}, {"indices": []}),
                              ({"device": "cuda"}, {"indices": [0, 0]}),
                              ({"device": "cuda", "max_atoms": 2}, {"indices": [0]})]:
            with self.assertRaises(ValueError):
                run_preflight(config, self.root / "invalid-input", probe=probe)
        self.run_probe(batch_size=1)
        with self.assertRaisesRegex(ValueError, "empty"):
            run_preflight({"device": "cuda"}, self.root / "probe", probe={"indices": [0]})


if __name__ == "__main__":
    unittest.main()
