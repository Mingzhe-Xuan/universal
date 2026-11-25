"""Slurm numerical controls, complete native graphs, paired capacity and fitting."""

import copy
import json
import math
import os
from pathlib import Path
import time

from universal_gnn.data.preparation.qm9.conversion import write_json
from universal_gnn.data.preparation.qm9.source import digest
from .definitions import MODES, PROPERTIES, canonical, load_case


def model_cases(definitions, model):
    matrix = json.loads((Path(definitions) / "definitions.json").read_bytes())
    cases = [c for c in matrix["cases"] if c["model"] == model]
    if len(cases) != 8:
        raise ValueError("Require all four properties and both initializations")
    for case in cases:
        load_case(definitions, case["id"])
    return cases


def smoke(definitions, model, output):
    """Small numerical control only; never a formal full-data outcome."""
    import torch
    from universal_gnn.data.splits.manifest import create_manifest
    from universal_gnn.engine.training import dataset, run_training

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cases = model_cases(definitions, model)
    source = dataset(cases[0]["config"]).source
    rows = []
    with Path(source.path).open(encoding="utf-8") as stream:
        for line in stream:
            rows.append(json.loads(line))
            if len(rows) == 24:
                break
    data = output / "fixture.jsonl"
    data.write_text("".join(json.dumps(r) + "\n" for r in rows))
    manifest = create_manifest([dict(id=r["id"], group=r["metadata"]["smiles"]) for r in rows], source_sha256=digest(data), seed=0)
    write_json(output / "split.json", manifest)
    results = {}
    for case in cases:
        config = copy.deepcopy(case["config"])
        config.update(device="cpu", epochs=2, batch_size=4)
        config["dataset"] = dict(path=str(data), sha256=digest(data), split_manifest=str(output / "split.json"),
                                 split_manifest_sha256=canonical(manifest), partition="train")
        report = run_training(config, output / case["id"])
        if not report["passed"] or not report["checkpoint_reload"] or not all(x > 0 and math.isfinite(x) for x in report["backbone_gradient_norms"]):
            raise RuntimeError("QM9 official backbone failed tiny forward/backward/reload control")
        results[case["id"]] = dict(passed=True, epochs=2, best_test_structures=report["heldout"]["structures"],
                                   report_sha256=digest(output / case["id"] / "report.json"))
    result = dict(status="passed", device="cpu", cases=results, formal_training_runs=0, slurm_job_id=os.environ["SLURM_JOB_ID"])
    write_json(output / "report.json", result)
    return result


def preflight(definitions, model, output, smoke_directory):
    import torch
    from universal_gnn.benchmarks.probes.native_scan import scan_training_graphs
    from universal_gnn.benchmarks.pairing.capacity import run_paired_capacity
    from universal_gnn.engine.initialization.neighbors import prepare_native_neighbors

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    smoke_path = Path(smoke_directory) / "report.json"
    smoke_report = json.loads(smoke_path.read_bytes())
    cases = model_cases(definitions, model)
    if smoke_report["status"] != "passed" or set(smoke_report["cases"]) != {c["id"] for c in cases}:
        raise ValueError("Require all eight actual CPU molecular controls")
    start = time.perf_counter()
    configs = {c["id"]: copy.deepcopy(c["config"]) for c in cases}
    prototype = next(c["config"] for c in cases if c["property"] == "homo" and c["initialization"] == "pretrained")
    probe = scan_training_graphs(prototype, output / "graphs")
    if model in {"mace", "nequip"}:
        original = next(c["config"] for c in cases if c["initialization"] == "scratch")
        calibrated = prepare_native_neighbors(original)
        for case in cases:
            if case["initialization"] == "scratch":
                configs[case["id"]]["backbone"]["neighbor_statistics"] = copy.deepcopy(calibrated["backbone"]["neighbor_statistics"])
    result = dict(status="running", model=model, probe_sha256=canonical(probe),
                  cpu_smoke_sha256=digest(smoke_path), cases={}, slurm_job_id=os.environ["SLURM_JOB_ID"])
    write_json(output / "report.json", result)
    for name in PROPERTIES:
        selected = {c["initialization"]: c for c in cases if c["property"] == name}
        pair = {mode: configs[selected[mode]["id"]] for mode in MODES}
        folder = output / name
        capacity = run_paired_capacity(pair, folder, probe=probe, timeout=7200)
        if not capacity["passed"]:
            raise RuntimeError("QM9 paired CUDA capacity failed; preserve attempts, do not retry unknown errors")
        for mode in MODES:
            case = selected[mode]
            resolved_path = folder / f"config.{mode}.resolved.json"
            config = json.loads(resolved_path.read_bytes())
            trials = [t for t in capacity["trials"] if t["initialization"] == mode]
            final = json.loads((Path(trials[-1]["directory"]) / "report.json").read_bytes())
            worker_path = Path(final["attempts"][-1]["directory"]) / "result.json"
            worker = json.loads(worker_path.read_bytes())
            if worker["status"] != "passed" or worker["measured_batches"] < 100:
                raise ValueError("Require actual100-batch CUDA timing")
            target = output / (case["id"] + ".json")
            write_json(target, config)
            result["cases"][case["id"]] = dict(config=str(target), config_sha256=canonical(config),
                structures_per_second=worker["structures_per_second"], batch_size=config["batch_size"],
                worker_sha256=digest(worker_path), peak_reserved_bytes=worker["peak_reserved_bytes"])
        write_json(output / "report.json", result)
    result.update(status="passed", device=torch.cuda.get_device_name(), wall_seconds=time.perf_counter() - start)
    counts = json.loads((Path(definitions) / "definitions.json").read_bytes())["data_report"]["split_counts"]
    result["projected_gpu_hours"] = {str(epochs):sum(
        ((counts["train"] + counts["validation"]) * epochs + 6 * counts["train"] + counts["test"])
        / entry["structures_per_second"] * 1.5 / 3600 for entry in result["cases"].values())
        for epochs in (50, 150, 300)}
    result["timing_scope"] = "Measured CUDA candidate batches; full train+validation+six auxiliary train traversals+test, 1.5 overhead factor. Epoch scenarios, not guaranteed early stopping or queue ETA."
    write_json(output / "report.json", result)
    return result


def train(definitions, identifier, preparation):
    from universal_gnn.engine.training import run_training
    from universal_gnn.engine.initialization.policy import inherit_neighbor_statistics

    case = load_case(definitions, identifier)
    preparation = Path(preparation)
    report = json.loads((preparation / "report.json").read_bytes())
    if report["status"] != "passed" or set(report["cases"]) != {c["id"] for c in model_cases(definitions, case["model"])}:
        raise ValueError("QM9 requires the complete eight-case model CUDA preparation")
    entry = report["cases"][identifier]
    config = json.loads(Path(entry["config"]).read_bytes())
    if canonical(config) != entry["config_sha256"]:
        raise ValueError("QM9 resolved config changed")
    expected = inherit_neighbor_statistics(case["config"], config)
    expected["batch_size"] = config["batch_size"]
    if expected != config:
        raise ValueError("Preflight changed more than batch/native scratch statistics")
    output = Path(case["run_directory"])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "config.requested.json", case["config"])
    status = dict(status="running", case_id=identifier, slurm_job_id=os.environ["SLURM_JOB_ID"],
                  preparation_sha256=digest(preparation / "report.json"))
    write_json(output / "formal-status.json", status)
    def event(kind, **values):
        status.update(stage=kind, **values)
        write_json(output / "formal-status.json", status)
    try:
        result = run_training(config, output, event_callback=event)
        if result["selected_structures"] != result["heldout"]["declared_train_structures"]:
            raise ValueError("QM9 training did not use the complete training split")
        status.update(status="training_passed_independent_pending", completed_epochs=result["completed_epochs"],
                      report_sha256=digest(output / "report.json"), checkpoint_sha256=digest(result["best_checkpoint"]))
    except Exception as error:
        status.update(status="failed", error_type=type(error).__name__, error=str(error))
        write_json(output / "formal-status.json", status)
        raise
    write_json(output / "formal-status.json", status)
    return status
