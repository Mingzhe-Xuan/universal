import importlib.util
from pathlib import Path


def test_evidence_rejects_failed_and_duplicate_records():
    path = Path(__file__).resolve().parents[1] / "scripts" / "collect_evidence.py"
    spec = importlib.util.spec_from_file_location("collect_evidence", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = {"passed": True, "structures": [{"id": str(i)} for i in range(10)],
              "checkpoint_reload": True, "initial_loss": 2., "final_loss": 1.,
              "parameter_delta_norm": .1, "backbone_gradient_norms": [.1],
              "execution": {"git_commit": "abc", "slurm": {"SLURM_JOB_ID": "123"}}}
    assert module.audit_training(report)
    report["passed"] = False
    assert not module.audit_training(report)
    report["passed"] = True
    report["structures"][0]["id"] = "1"
    assert not module.audit_training(report)
