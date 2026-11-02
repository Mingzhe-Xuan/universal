"""Audit actual saved reports and images, with no model execution or invented job status."""

import argparse
import hashlib
import json
import math
from pathlib import Path


MODELS = ("cgcnn", "megnet", "alignn", "equiformer", "nequip", "mace")
TASKS = ("formation_energy", "bandgap", "generation", "classification", "atom_charge", "atom_moment",
         "electron_dos", "phonon_dos", "dielectric", "piezoelectric", "elastic", "forcefield",
         "born_charge", "dielectric_dfpt", "raman", "optical")


def read(path):
    return json.loads(Path(path).read_text())


def audit_training(report):
    identifiers = [item["id"] for item in report["structures"]]
    return bool(report.get("passed") and len(identifiers) == 10 and len(set(identifiers)) == 10
                and report.get("checkpoint_reload")
                and math.isfinite(report["final_loss"]) and report["final_loss"] < report["initial_loss"]
                and math.isfinite(report["parameter_delta_norm"]) and report["parameter_delta_norm"] > 0
                and max(report["backbone_gradient_norms"], default=0) > 0
                and report["execution"].get("git_commit")
                and report["execution"].get("slurm", {}).get("SLURM_JOB_ID"))


def audit_workflow(path):
    import numpy as np

    report = read(path)
    identifiers = [item["id"] for item in report["structures"]]
    if not report.get("passed") or len(identifiers) != 10 or len(set(identifiers)) != 10:
        return False
    for item in report["structures"]:
        if set(item.get("spectra", {})) != {"ir", "raman", "neutron"}:
            return False
        if not all(np.isfinite(spectrum).all() for spectrum in item["spectra"].values()):
            return False
        image_path = (path.parent / item["microscopy"]["image"]).resolve()
        if not image_path.is_relative_to(path.parent.resolve()):
            return False
        image = np.load(image_path, allow_pickle=False)
        if (image.shape != (item["microscopy"]["scan_gpts"],) * 2 or not np.isfinite(image).all()
                or image.max() <= 0 or image.min() < -1e-10 or np.ptp(image) == 0):
            return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrices", type=Path, nargs="+", required=True)
    parser.add_argument("--workflows", type=Path, default=Path("runs/workflows"))
    parser.add_argument("--output", type=Path, default=Path("results/acceptance-index.json"))
    args = parser.parse_args()
    cases, failures = {}, []
    for matrix_path in args.matrices:
        for case in read(matrix_path)["cases"]:
            path = Path(case["output"]) / "report.json"
            try:
                report = read(path)
                passed = audit_training(report)
                cases[case["id"]] = {"passed": passed, "path": str(path),
                                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                      "execution": report["execution"],
                                      "initial_loss": report["initial_loss"], "final_loss": report["final_loss"]}
            except Exception as error:
                failures.append({"case": case["id"], "error": repr(error)})
    expected = {f"{model}--{task}" for model in MODELS for task in TASKS}
    missing = sorted(expected - cases.keys())
    workflows = {}
    for model in MODELS:
        path = args.workflows / model / "report.json"
        try:
            workflows[model] = {"passed": audit_workflow(path), "path": str(path),
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                "execution": read(path)["execution"]}
        except Exception as error:
            workflows[model] = {"passed": False, "error": repr(error)}
    result = {"training": cases, "workflows": workflows, "missing": missing, "failures": failures,
              "passed": bool(not missing and not failures and all(case["passed"] for case in cases.values())
                             and all(case["passed"] for case in workflows.values())),
              "scope": "ten-structure execution and checkpoint replay; no accuracy or physical convergence claim"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"passed": result["passed"], "training": len(cases), "missing": missing,
                      "workflow_passed": sum(row["passed"] for row in workflows.values()),
                      "failures": failures}))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
