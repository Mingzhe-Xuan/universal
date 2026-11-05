"""Re-score saved generation geometry in a separate CPU Slurm process."""

import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import time

from ..execution.gates import compatible_sources, file_sha, read_json
from ..experiments.registry import DATASETS, canonical_digest
from ..preflight import write_json
from universal_gnn.data.splits import validate_manifest
from .evidence import checked_generation_config, validate_prior
from .execution import generation_case, verify_generation_training, verify_quality

SCORING_SOURCES = ("engine/generative/structure_quality.py", "engine/generative/protocol.py",
                   "data/indexed.py", "data/structures.py", "data/formats.py", "engine/runtime.py")
NUMERIC_PACKAGES = ("torch", "numpy", "ase", "pymatgen")


def compare_metrics(actual, expected, name="metrics"):
    """Compare nested observations, retaining boolean, count and null semantics."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(name + " keys differ")
        for key, value in expected.items():
            compare_metrics(actual[key], value, name + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(name + " length differs")
        for index, value in enumerate(expected):
            compare_metrics(actual[index], value, name + "." + str(index))
    elif type(expected) is float:
        if (type(actual) not in (int, float) or not math.isfinite(actual) or not math.isfinite(expected) or
                not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError(name + " numeric observation differs")
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(name + " observation differs")


def check_scoring_runtime(trained, quality):
    repository = Path(__file__).resolve().parents[4]
    if Path.cwd().resolve() != repository:
        raise ValueError("Assess from the clean immutable source checkout")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise ValueError("Scoring source must be clean")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    paths = ["src/universal_gnn/" + name for name in SCORING_SOURCES]
    for previous in {trained["execution"]["git_commit"], quality["execution"]["git_commit"]}:
        if not isinstance(previous, str) or len(previous) != 40:
            raise ValueError("Saved reports lack scoring source provenance")
        changed = subprocess.check_output(["git", "diff", "--name-only", previous, commit, "--", *paths], text=True)
        if changed.strip():
            raise ValueError("Raw-geometry/scoring source changed; review instead of silently rescoring")
    versions = {name: importlib.metadata.version(name) for name in NUMERIC_PACKAGES}
    for report in (trained, quality):
        if any(report["versions"].get(name) != value for name, value in versions.items()):
            raise ValueError("Numeric scoring versions differ from saved execution")
    return dict(git_commit=commit, device="cpu", versions=versions,
                source_sha256={path: file_sha(path) for path in paths + [str(Path(__file__).relative_to(repository))]})


def recompute_saved(trained, quality, manifest):
    """Load raw geometry at the original dtype; never load or run a model."""
    import torch
    from universal_gnn.data.indexed import JSONLStructures, SelectedStructures
    from universal_gnn.engine.runtime import data_fingerprint
    from universal_gnn.engine.generative.protocol import fit_volume_prior
    from universal_gnn.engine.generative.structure_quality import StructuralQuality

    config = trained["config"]
    if config["dtype"] not in {"float32", "float64"}:
        raise ValueError("Unsupported original geometry precision")
    source = JSONLStructures(config["dataset"]["path"], dtype=getattr(torch, config["dtype"]))
    if (source.sha256 != config["dataset"]["sha256"] or
            source.identifiers != [r["id"] for r in manifest["records"]]):
        raise ValueError("Raw source bytes or ordered identifiers changed")
    training = SelectedStructures(source, manifest["partitions"]["train"])

    def record(structure):
        return dict(id=structure.identifier, numbers=structure.numbers.tolist(),
                    positions=structure.positions.tolist(), cell=structure.cell.tolist(), pbc=structure.pbc.tolist())

    fingerprint = data_fingerprint(training)
    prior = dict(sampling_volume_source="train_fit", statistics=fit_volume_prior(
        (record(s) for s in training), training_fingerprint=fingerprint))
    compare_metrics(config["generation_prior"], prior, "raw_training_prior")
    if trained.get("data_fingerprint") != fingerprint:
        raise ValueError("Raw complete training fingerprint differs")
    scorer = StructuralQuality(training, record=record)
    by_id = {manifest["records"][i]["id"]: i for i in manifest["partitions"]["test"]}
    references = {}
    count = 0
    with Path(quality["samples"]).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            identifier = row["condition_id"]
            if identifier not in references:
                references[identifier] = record(source[by_id[identifier]])
            generated = row["structure"]
            failure = row["quality"]["reason"] if generated is None else None
            actual = scorer.update(generated, references[identifier], failure=failure)
            compare_metrics(row["quality"], actual, "sample." + str(count))
            count += 1
    metrics = scorer.result()
    compare_metrics({key: quality.get(key) for key in metrics}, metrics)
    return dict(samples_rescored=count, selected_references=len(references),
                training_structures=len(training), training_fingerprint=fingerprint,
                training_prior=prior, metrics=metrics,
                interpretation="Independent process replay of the original scorer and raw runtime-dtype geometry; saved numerical-failure events are retained, not regenerated")


def assess_saved_quality(training_report, quality_report, output, *, diagnostic=False, formal_gate=None):
    """Default formal mode requires a frozen case gate; diagnostics are explicit."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Generation assessment must run through Slurm")
    if not diagnostic and formal_gate is None:
        raise ValueError("Formal assessment requires the frozen matrix/case entry")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Assessment output must be new")
    trained, quality = read_json(training_report), read_json(quality_report)
    config = trained["config"]
    manifest = read_json(config["dataset"]["split_manifest"])
    counts = manifest["counts"]
    validate_manifest(manifest, source_sha256=config["dataset"]["sha256"], source_count=manifest["source_count"])
    if canonical_digest(manifest) != config["dataset"]["split_manifest_sha256"]:
        raise ValueError("Saved source manifest changed")
    if (not trained.get("passed") or not trained.get("checkpoint_reload") or config.get("structures") != "all" or
            config.get("max_atoms") is not None or config.get("dataset", {}).get("partition") != "train" or
            config.get("task", {}).get("kind") != "generation" or
            config["task"]["sampling"].get("steps") != 100 or config["task"]["sampling"].get("inner_steps") != 2 or
            trained.get("selected_structures") != counts["train"] or trained.get("available_structures") != manifest["source_count"]):
        raise ValueError("Require complete declared generation training and its original sampling steps")
    prior = config["generation_prior"]
    validate_prior(prior, counts["train"])
    if diagnostic:
        if counts != dict(train=64, validation=16, test=16) or manifest["source_count"] != 96:
            raise ValueError("Diagnostic assessment is limited to the registered64/16/16 protocol")
        gate = dict(config=config, training_prior=prior, counts=counts,
                    quality_protocol=dict(samples=8, draws_per_condition=1, seed=456))
    else:
        gate = formal_gate
        if (gate["config"] != config or gate["counts"] != counts or
                counts != dict(zip(("train", "validation", "test"), DATASETS["perov5"][1])) or
                config["dataset"]["sha256"] != DATASETS["perov5"][0] or manifest["source_count"] != 18928):
            raise ValueError("Formal assessment differs from the frozen case gate")
    integrity = verify_quality(quality, trained, gate, diagnostic=diagnostic)
    if file_sha(trained["best_checkpoint"]) != quality["checkpoint_sha256"]:
        raise ValueError("Saved quality references changed best weights")
    execution = check_scoring_runtime(trained, quality)
    inputs = dict(training_report=str(training_report), quality_report=str(quality_report),
                  samples=quality["samples"], source=config["dataset"]["path"],
                  manifest=config["dataset"]["split_manifest"], best=trained["best_checkpoint"])
    before = {name: file_sha(path) for name, path in inputs.items()}
    if before["source"] != config["dataset"]["sha256"] or before["samples"] != integrity["samples_sha256"]:
        raise ValueError("Assessment source or samples changed after integrity checks")
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = dict(status="running", stage="raw_geometry_rescore", scope="diagnostic" if diagnostic else "formal",
                  slurm_job_id=os.environ["SLURM_JOB_ID"], execution=execution, inputs=inputs,
                  input_sha256=before, integrity=integrity, formal_training_runs=0,
                  formal_generation_quality_verified=False, model_forward_executed=False,
                  model_deserialized=False, new_samples_generated=0,
                  measurement_scope="CPU wall covers raw geometry/prior/scoring and final input/source checks; excludes initial validation. Peak RSS includes process imports")
    write_json(output / "report.json", report)
    try:
        import resource

        result = recompute_saved(trained, quality, manifest)
        if {name: file_sha(path) for name, path in inputs.items()} != before:
            raise ValueError("Assessment inputs changed during independent scoring")
        if check_scoring_runtime(trained, quality) != execution:
            raise ValueError("Scoring source or versions changed during assessment")
        if result["samples_rescored"] != quality["attempted"]:
            raise ValueError("Independent score omitted attempted samples")
        report.update(status="passed", stage="complete", **result,
                      formal_generation_quality_verified=not diagnostic,
                      wall_seconds=time.perf_counter() - started,
                      peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        write_json(output / "report.json", report)
        return report
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        write_json(output / "report.json", report)
        raise


def assess_generation_case(matrix, identifier, output):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Generation assessment must run through Slurm")
    spec = generation_case(matrix, identifier)
    root = Path(spec["case"]["run_directory"])
    gate, status = read_json(root / "generation-gate.json"), read_json(root / "formal-status.json")
    if (gate["case"] != spec["case"] or gate["counts"] != spec["counts"] or
            gate["source_structures"] != spec["source_structures"] or
            gate["matrix_sha256"] != spec["matrix_sha256"] or gate["quality_protocol"] != spec["quality_protocol"] or
            status.get("case_id") != identifier or status.get("matrix_sha256") != spec["matrix_sha256"] or
            status.get("status") != "passed" or status.get("generation_quality_complete") is not True or
            status.get("formal_training_runs_completed") != 1):
        raise ValueError("Formal assessment requires the completed frozen generation case")
    checked_generation_config(gate["config"], spec["configs"][spec["case"]["initialization"]],
                              gate["common_batch_size"], gate["counts"], gate["training_prior"])
    trained = read_json(root / "report.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    verify_generation_training(trained, gate, events)
    if file_sha(trained["checkpoint"]) != status["last_checkpoint_sha256"]:
        raise ValueError("Last checkpoint changed after training")
    quality_path = Path(status["quality"])
    if not quality_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Quality report belongs outside the selected case")
    quality = read_json(quality_path)
    if verify_quality(quality, trained, gate) != status["quality_integrity"]:
        raise ValueError("Quality inputs differ from accepted execution integrity")
    compatible_sources([gate["git_commit"], trained["execution"]["git_commit"]])
    result = assess_saved_quality(root / "report.json", quality_path, output, formal_gate=gate)
    result.update(case_id=identifier, matrix_sha256=spec["matrix_sha256"],
                  interpretation="Independent saved-quality audit; formal training and other required paper gates remain separately accountable")
    write_json(Path(output) / "report.json", result)
    return result
