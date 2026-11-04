"""Revalidate both initializations at a common batch; never launch formal training."""

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from ..preflight import run_preflight, write_json
from ..experiments.registry import canonical_digest

MODES = ("pretrained", "scratch")


def comparable_config(config, mode):
    """Only initialization, batch and scratch-native normalization may differ."""
    if not isinstance(config, dict) or not isinstance(config.get("backbone"), dict):
        raise ValueError("Paired capacity requires complete configuration mappings")
    result = copy.deepcopy(config)
    backbone = result["backbone"]
    if backbone.get("initialization") != mode or backbone.get("implementation") != "official":
        raise ValueError("Pair must explicitly select official pretrained and scratch initialization")
    batch = result.pop("batch_size", 32)
    if type(batch) is not int or batch < 1:
        raise ValueError("Pair batch_size must be a positive integer")
    if not str(result.get("device", "cpu")).startswith("cuda"):
        raise ValueError("Paired capacity requires an explicit CUDA device")
    if result.get("max_atoms") is not None:
        raise ValueError("Paired capacity cannot truncate structures with max_atoms")
    if result.get("structures") != "all":
        raise ValueError("Formal paired capacity requires structures=all")
    dataset = result.get("dataset")
    if not isinstance(dataset, dict) or not dataset.get("split_manifest") or dataset.get("partition") != "train":
        raise ValueError("Paired capacity requires an explicit training split manifest")
    backbone.pop("initialization")
    if "neighbor_statistics" in backbone:
        if mode != "scratch" or backbone.get("name") not in {"mace", "nequip"}:
            raise ValueError("Native neighbor statistics belong only to MACE/NequIP scratch")
        backbone.pop("neighbor_statistics")
    return result


def validate_pair(configs):
    if not isinstance(configs, dict) or set(configs) != set(MODES):
        raise ValueError("Require exactly pretrained and scratch configurations")
    if comparable_config(configs["pretrained"], "pretrained") != comparable_config(configs["scratch"], "scratch"):
        raise ValueError("Paired task, seed, graph, data, readout, precision and optimization must match")


def select_pair(matrix, pair_id):
    """Read selected frozen definitions, without treating them as runtime evidence."""
    if (not isinstance(matrix, dict) or type(matrix.get("version")) is not int or matrix["version"] != 1 or
            matrix.get("kind") != "arxiv_v1_primary_matrix"):
        raise ValueError("A full primary definition matrix is required")
    if matrix.get("registry_sha256") != canonical_digest(matrix.get("registry")):
        raise ValueError("Matrix frozen input registry digest differs")
    pairs = [pair for pair in matrix.get("pairs", []) if pair.get("id") == pair_id]
    if len(pairs) != 1 or len(pairs[0].get("cases", [])) != 2 or len(set(pairs[0]["cases"])) != 2:
        raise ValueError("Select one unambiguous pair containing exactly two cases")
    configs = {}
    for identifier in pairs[0]["cases"]:
        cases = [case for case in matrix.get("cases", []) if case.get("id") == identifier]
        if len(cases) != 1 or cases[0].get("pair_id") != pair_id:
            raise ValueError("Matrix pair case identities differ")
        case = cases[0]
        if case.get("config_sha256") != canonical_digest(case.get("config")):
            raise ValueError("Matrix case configuration digest differs")
        mode = case.get("initialization")
        if mode not in MODES or mode in configs:
            raise ValueError("Matrix pair initialization identities differ")
        configs[mode] = copy.deepcopy(case["config"])
    validate_pair(configs)
    return configs


def run_paired_capacity(configs, output, *, probe, phase="train", python=None, timeout=3600,
                        worker_module="universal_gnn.benchmarks.probe_worker"):
    """Success proves common capacity for this probe, never full-data readiness."""
    validate_pair(configs)
    if phase not in {"train", "sample"}:
        raise ValueError("phase must be train or sample")
    if phase == "sample" and configs["pretrained"].get("task", {}).get("kind") != "generation":
        raise ValueError("Sampling capacity applies only to generation")
    if not isinstance(probe, dict) or not isinstance(probe.get("indices"), list) or not probe["indices"]:
        raise ValueError("An explicit training probe is required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version=1, kind="paired_capacity", status="running", passed=False, phase=phase,
                  started_at=datetime.now(timezone.utc).isoformat(), configs=copy.deepcopy(configs),
                  input_config_sha256={mode:canonical_digest(configs[mode]) for mode in MODES},
                  probe=copy.deepcopy(probe), common_batch_size=None, trials=[],
                  full_training_graph_coverage_certified=False,
                  interpretation="common capacity of supplied probe only; no formal training launched")
    write_json(output / "report.json", report)
    resolved = copy.deepcopy(configs)

    def trial(mode, stage, batch=None):
        candidate = copy.deepcopy(resolved[mode])
        if batch is not None:
            candidate["batch_size"] = batch
        target = output / stage / mode
        result = run_preflight(candidate, target, probe=probe, phase=phase, python=python,
                               timeout=timeout, worker_module=worker_module)
        report["trials"].append(dict(stage=stage, initialization=mode, directory=str(target),
                                     passed=result["passed"], final_batch_size=result["final_batch_size"],
                                     report_sha256=canonical_digest(result)))
        write_json(output / "report.json", report)
        if not result["passed"]:
            report.update(status="failed", failed_initialization=mode, failed_stage=stage)
            write_json(output / "report.json", report)
            return False
        resolved[mode] = json.loads((target / "config.resolved.json").read_text(encoding="utf-8"))
        return True

    try:
        for mode in MODES:
            if not trial(mode, "individual"):
                return report
        common = min(resolved[mode]["batch_size"] for mode in MODES)
        round_number = 0
        while True:
            round_number += 1
            stage = f"common-{round_number:02d}-b{common}"
            for mode in MODES:
                if not trial(mode, stage, common):
                    return report
            accepted = min(resolved[mode]["batch_size"] for mode in MODES)
            if accepted == common:
                break
            if accepted >= common:
                raise RuntimeError("Common capacity did not decrease after a repeated OOM")
            common = accepted
        validate_pair(resolved)
        for mode in MODES:
            write_json(output / f"config.{mode}.resolved.json", resolved[mode])
        report.update(status="passed", passed=True, common_batch_size=common,
                      effective_batch_size=common, gradient_accumulation_steps=1,
                      resolved_config_sha256={mode:canonical_digest(resolved[mode]) for mode in MODES},
                      final_configs={mode:f"config.{mode}.resolved.json" for mode in MODES})
        write_json(output / "report.json", report)
        return report
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        write_json(output / "report.json", report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--pair", required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("train", "sample"), default="train")
    parser.add_argument("--timeout", type=float, default=3600)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Paired model capacity checks must run through Slurm")
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    configs = select_pair(matrix, args.pair)
    report = run_paired_capacity(configs, args.output,
                                 probe=json.loads(args.probe.read_text(encoding="utf-8")),
                                 phase=args.phase, timeout=args.timeout)
    print(json.dumps({key:report[key] for key in ("status", "phase", "common_batch_size")}))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
