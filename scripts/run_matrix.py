"""Prepare, execute one Slurm array case, or summarize honest per-case evidence."""

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


MODELS = ["cgcnn", "megnet", "alignn", "equiformer", "nequip", "mace"]


def prepare(args):
    if args.epochs < 1 or args.width < 4 or args.learning_rate <= 0:
        raise ValueError("Need positive epochs/rate and width>=4")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    names = args.models.split(",") if args.models else MODELS
    tasks = args.tasks.split(",") if args.tasks else list(manifest["tasks"])
    args.output.mkdir(parents=True, exist_ok=True)
    cases = []
    for name in names:
        if name not in MODELS:
            raise ValueError(f"Unknown matrix backbone {name}")
        for task_name in tasks:
            source = manifest["tasks"][task_name]
            identifier = f"{name}--{task_name}"
            config = {"seed": 123, "structures": 10, "device": "cpu", "epochs": args.epochs,
                      "learning_rate": args.learning_rate,
                      "backbone": {"name": name, "width": args.width, "layers": 2, "cutoff": 4.},
                      "dataset": source["dataset"], "task": source["task"]}
            cases.append({"id": identifier, "config": config,
                          "output": str(args.output / identifier)})
    matrix = {"cases": cases, "pending_data": manifest.get("pending", {}),
              "interpretation": "10-structure training/reloaded-inference execution acceptance"}
    path = args.output / "matrix.json"
    path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    print(json.dumps({"matrix": str(path), "cases": len(cases), "pending_data": matrix["pending_data"]}))


def run(args):
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if not 0 <= args.index < len(matrix["cases"]):
        raise ValueError("Matrix index out of range")
    case = matrix["cases"][args.index]
    name = case["config"]["backbone"]["name"]
    if name == "mace":
        wanted = Path(os.environ.get("UGNN_MACE_PYTHON", "/home/xmz/.venvs/universal-mace/bin/python"))
        if Path(sys.executable).absolute() != wanted.absolute():
            if not wanted.is_file():
                raise FileNotFoundError(f"MACE requires its separate environment: {wanted}")
            os.execv(str(wanted), [str(wanted), *sys.argv])
    from universal_gnn.engine.training import run_training

    output = Path(case["output"])
    output.mkdir(parents=True, exist_ok=True)
    try:
        report = run_training(case["config"], output)
    except Exception as error:
        failure = {"case": case["id"], "passed": False, "error": repr(error),
                   "traceback": traceback.format_exc(), "slurm_job_id": os.environ.get("SLURM_JOB_ID")}
        (output / "failure.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        raise
    (output / "failure.json").unlink(missing_ok=True)
    print(json.dumps({"case": case["id"], "passed": report["passed"],
                      "initial_loss": report["initial_loss"], "final_loss": report["final_loss"]}))


def summarize(args):
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    records = []
    for case in matrix["cases"]:
        output = Path(case["output"])
        row = {"case": case["id"], "status": "pending"}
        if (output / "failure.json").is_file():
            row.update(status="failed", failure=json.loads((output / "failure.json").read_text()))
        elif (output / "report.json").is_file():
            report = json.loads((output / "report.json").read_text())
            row.update(status="passed" if report["passed"] else "failed",
                       initial_loss=report["initial_loss"], final_loss=report["final_loss"],
                       execution=report.get("execution"))
        records.append(row)
    report = {"cases": records, "pending_data": matrix["pending_data"],
              "passed": bool(records and all(row["status"] == "passed" for row in records)
                             and not matrix["pending_data"])}
    target = args.matrix.with_name("summary.json")
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(records), "counts": {status: sum(row["status"] == status for row in records)
                     for status in ["passed", "failed", "pending"]}, "pending_data": matrix["pending_data"]}))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--manifest", type=Path, default=Path("data/acceptance/manifest.json"))
    prep.add_argument("--output", type=Path, default=Path("runs/acceptance"))
    prep.add_argument("--models")
    prep.add_argument("--tasks")
    prep.add_argument("--epochs", type=int, default=30)
    prep.add_argument("--width", type=int, default=16)
    prep.add_argument("--learning-rate", type=float, default=.001)
    single = sub.add_parser("run")
    single.add_argument("--matrix", type=Path, required=True)
    single.add_argument("--index", type=int, required=True)
    summary = sub.add_parser("summarize")
    summary.add_argument("--matrix", type=Path, required=True)
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "summarize": summarize}[args.command](args)


if __name__ == "__main__":
    main()
