"""Retain separate, source-bound training and sampling capacity evidence."""

import copy
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

from ..experiments.registry import DATASETS, canonical_digest
from ..pairing.capacity import select_pair
from ..pairing.evidence import verify_capacity_evidence
from ..preflight import write_json


def generation_spec(matrix, pair_id):
    """Check frozen full-data recipes without importing any numerical runtime."""
    configs = select_pair(matrix, pair_id)
    cases = [case for case in matrix["cases"] if case["pair_id"] == pair_id]
    if matrix.get("definition_revision") != 2 or len(cases) != 2:
        raise ValueError("Require the corrected full matrix and exactly two cases")
    for case in cases:
        config = case["config"]
        if (case.get("task") != "generation" or config.get("task") !=
                {"kind": "generation", "sampling": {"steps": 100, "inner_steps": 2}} or
                config.get("generation_corruption") != "per_epoch_structure_v2" or
                config.get("validate_sampling") is not False):
            raise ValueError("Generation must preserve its frozen corruption and100x2 steps")
        if (config.get("dtype") != "float32" or config.get("batch_size") != 16 or
                config.get("epochs") != 300 or config.get("evaluation") != {"patience": 30, "min_delta": 0.}):
            raise ValueError("Full generation training recipe differs")
        if (config["dataset"].get("sha256") != DATASETS["perov5"][0] or
                config["dataset"].get("path") != "data/arxiv-v1/perov5/structures.jsonl"):
            raise ValueError("Require the frozen complete Perov-5 source")
        if case.get("generation_quality") != {
                "samples": 1000, "draws_per_condition": 5, "seed": 456,
                "interpretation": "conditional geometry only; no DFT stability claim"}:
            raise ValueError("Formal generation quality protocol differs")
        if case.get("sampling_preflight") != {
                "warmup_batches": 1, "measure_batches": 5, "initial_batch_size": 4}:
            raise ValueError("Sampling preflight protocol differs")
        if case.get("preflight") != {
                "warmup_batches": 2, "measure_batches": 100, "initial_batch_size": 16}:
            raise ValueError("Training preflight protocol differs")
    return dict(pair_id=pair_id, configs=configs, matrix_sha256=canonical_digest(matrix),
                counts=dict(zip(("train", "validation", "test"), DATASETS["perov5"][1])),
                quality=copy.deepcopy(cases[0]["generation_quality"]),
                sampling_preflight=copy.deepcopy(cases[0]["sampling_preflight"]))


def verify_resolved(actual, expected, batch, prior, training_count):
    """Permit only tested batch, train-fit prior and declared scratch calibration."""
    clean = copy.deepcopy(actual)
    stats = clean["backbone"].pop("neighbor_statistics", None)
    if expected["backbone"]["initialization"] == "scratch" and expected["backbone"]["name"] in {"mace", "nequip"}:
        if (not isinstance(stats, dict) or stats.get("structures") != training_count or
                stats.get("declared_training_structures") != training_count or
                stats.get("source_sha256") != expected["dataset"]["sha256"] or
                stats.get("dtype") != expected["dtype"]):
            raise ValueError("Scratch native calibration does not cover complete training data")
    elif stats is not None:
        raise ValueError("Unexpected native calibration")
    target = copy.deepcopy(expected)
    target["batch_size"] = batch
    target["generation_prior"] = copy.deepcopy(prior)
    target["task"]["sampling"]["volume_per_atom"] = prior["statistics"]["volume_per_atom"]
    if clean != target:
        raise ValueError("Resolved configuration changed beyond batch/prior/native calibration")


def phase_probes(train_probe, settings):
    """Retain all scanned worst cases; the scheduler may measure more than five."""
    sample = copy.deepcopy(train_probe)
    sample["warmup_batches"] = settings["warmup_batches"]
    sample["measure_batches"] = settings["measure_batches"]
    return sample


def prepare_generation_pair(matrix, pair_id, output, *, timeout=7200):
    """Run through Slurm. No trained checkpoint or scientific quality is produced."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Generation pair preparation must run through Slurm")
    spec = generation_spec(matrix, pair_id)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version=1, kind="full_generation_pair_preparation", status="running",
                  stage="complete_training_partition", slurm_job_id=os.environ["SLURM_JOB_ID"],
                  pair_id=pair_id, matrix_sha256=spec["matrix_sha256"],
                  formal_training_runs=0, formal_training_launched=False,
                  required_formal_quality=spec["quality"], full_data_quality_evaluated=False)

    def record(**values):
        report.update(values, updated_at=time.time())
        write_json(output / "report.json", report)

    try:
        record()
        import torch
        from dataclasses import replace
        from universal_gnn.backbones.factory import make_backbone
        from universal_gnn.benchmarks.probes.native_scan import scan_training_graphs
        from universal_gnn.engine.batching import model_dtype
        from universal_gnn.engine.generation import resolve_sampling_prior
        from universal_gnn.engine.runtime import data_fingerprint
        from universal_gnn.engine.training import dataset
        from universal_gnn.benchmarks.pairing.capacity import run_paired_capacity

        free = shutil.disk_usage(output).free
        if free < 20 * 1024**3:
            raise RuntimeError("Less than20GiB disk reserve")
        configs = spec["configs"]
        structures = dataset(configs["pretrained"])
        manifest = json.loads(Path(configs["pretrained"]["dataset"]["split_manifest"]).read_text())
        if (len(structures) != spec["counts"]["train"] or len(structures.source) != sum(spec["counts"].values()) or
                list(structures.indices) != manifest["partitions"]["train"] or
                any(len(manifest["partitions"][role]) != count for role, count in spec["counts"].items())):
            raise ValueError("Incomplete source or changed full frozen partitions")
        for mode, config in configs.items():
            write_json(output / ("input-" + mode + ".json"), config)
        fitted = copy.deepcopy(configs["pretrained"])
        resolve_sampling_prior(fitted, structures, data_fingerprint(structures))
        prior = fitted["generation_prior"]
        if (prior["sampling_volume_source"] != "train_fit" or
                prior["statistics"]["structures"] != len(structures)):
            raise ValueError("Prior must fit the entire actual training geometry only")
        record(stage="original_prediction_parity", initial_free_bytes=free,
               counts=spec["counts"], training_prior=prior)
        # Imported only here: this reference invokes the original external package.
        sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
        from validate_official import independent_reference

        examples = [structures[0], structures[1]]
        reference_config = copy.deepcopy(configs["pretrained"])
        if reference_config["backbone"]["name"] == "cgcnn":
            reference_config["task"]["property"] = "_unused_cif_csv_slot"
            examples = [replace(item, targets={"_unused_cif_csv_slot": 0.}) for item in examples]
        torch.manual_seed(configs["pretrained"]["seed"])
        options = {key: value for key, value in configs["pretrained"]["backbone"].items() if key != "name"}
        backbone = make_backbone(configs["pretrained"]["backbone"]["name"], **options).to(
            dtype=model_dtype(configs["pretrained"])).eval()
        parity = independent_reference(backbone, examples, reference_config)
        del backbone
        record(stage="full_clean_training_graph_scan", native_parity=parity,
               parity_scope="unconditioned original features/public head; CSV slot is reference-reader-only")
        probe = scan_training_graphs(configs["pretrained"], output / "graph-scan",
                                     warmup_batches=2, measure_batches=100)
        if not probe["coverage"]["verified_full_training_scan"] or probe["coverage"]["structures"] != len(structures):
            raise ValueError("Missing full clean training graph coverage")
        record(stage="paired_training_capacity")
        train = run_paired_capacity(configs, output / "train-capacity", probe=probe, timeout=timeout)
        if not train["passed"]:
            raise RuntimeError("Training capacity failed; retain attempts")
        train_evidence = verify_capacity_evidence(output / "train-capacity", probe)
        train_resolved = {}
        for mode in ("pretrained", "scratch"):
            actual = json.loads((output / "train-capacity" / train["final_configs"][mode]).read_text())
            verify_resolved(actual, configs[mode], train["common_batch_size"], prior, len(structures))
            train_resolved[mode] = actual
        sample_configs = copy.deepcopy(train_resolved)
        for config in sample_configs.values():
            config["batch_size"] = spec["sampling_preflight"]["initial_batch_size"]
        sample_probe = phase_probes(probe, spec["sampling_preflight"])
        record(stage="paired_sampling_capacity", training_batch_size=train["common_batch_size"])
        sample = run_paired_capacity(sample_configs, output / "sample-capacity", probe=sample_probe,
                                     phase="sample", timeout=timeout)
        if not sample["passed"]:
            raise RuntimeError("Sampling capacity failed; retain attempts without shortening denoising")
        sample_evidence = verify_capacity_evidence(output / "sample-capacity", sample_probe, minimum_batches=5)
        for mode in ("pretrained", "scratch"):
            actual = json.loads((output / "sample-capacity" / sample["final_configs"][mode]).read_text())
            verify_resolved(actual, configs[mode], sample["common_batch_size"], prior, len(structures))
        slow_train = max(w["elapsed_seconds"] / w["measured_batches"] for w in train_evidence["successful_workers"])
        slow_sample = max(w["elapsed_seconds"] / w["measured_structures"] for w in sample_evidence["successful_workers"])
        record(status="passed", stage="complete", sampling_batch_size=sample["common_batch_size"],
               train_configs={k: str(output / "train-capacity" / v) for k, v in train["final_configs"].items()},
               sample_configs={k: str(output / "sample-capacity" / v) for k, v in sample["final_configs"].items()},
               train_evidence={k: v for k, v in train_evidence.items() if k != "successful_workers"},
               sample_evidence={k: v for k, v in sample_evidence.items() if k != "successful_workers"},
               resource_estimate=dict(train_only_300_epoch_seconds=slow_train * math.ceil(len(structures) / train["common_batch_size"]) * 300,
                                      sample_probe_seconds_per_structure=slow_sample),
               interpretation="Complete clean graphs; actual corrupted training and100x2 evolving sampling probes. No bound on all possible noisy graphs. Formal quality currently samples singly and needs a separate1000-attempt run; probe throughput is not its measured cost.")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error))
        raise
