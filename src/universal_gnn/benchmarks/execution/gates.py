"""Read complete preparation evidence before allowing a formal predictive case."""

import copy
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess

from ..experiments.recipes import build_matrix, TASK_DATASETS
from ..experiments.registry import canonical_digest, NEQUIP_ARCHITECTURE
from ..pairing.capacity import select_pair
from ..pairing.evidence import verify_capacity_evidence
from ..probes.selection import select_probe
from universal_gnn.data.splits import validate_manifest

CRITICAL = ("backbones", "contracts", "engine", "tasks", "data", "adapters", "readouts", "properties")
CAPACITY_SOURCES = ("preflight.py", "probe_worker.py", "resolution.py", "pairing/capacity.py", "probes")
PACKAGES = ("torch", "e3nn", "numpy", "ase", "mace-torch", "nequip", "alignn", "dgl", "torch-geometric")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def case_spec(matrix, identifier, *, allow_generation=False):
    """Check the full144 definition and selected original recipe without model imports."""
    if (matrix.get("kind") != "arxiv_v1_primary_matrix" or matrix.get("definition_revision") != 2 or
            matrix.get("expected_training_runs") != 144 or len(matrix.get("cases", [])) != 144 or
            matrix.get("registry_sha256") != canonical_digest(matrix.get("registry"))):
        raise ValueError("Require the complete corrected144-case primary matrix")
    rebuilt = build_matrix(matrix["registry"])
    expected = {c["id"]: c for c in rebuilt["cases"]}
    ids = [c["id"] for c in matrix["cases"]]
    if len(set(ids)) != 144 or set(ids) != set(expected):
        raise ValueError("Primary matrix does not cover all model/task/mode/seed cases")
    cases = [c for c in matrix["cases"] if c["id"] == identifier]
    if len(cases) != 1:
        raise ValueError("Select exactly one primary case")
    case = copy.deepcopy(cases[0])
    if case["task"] == "generation" and not allow_generation:
        raise ValueError("Generation requires its independent training and1000-attempt quality orchestration")
    baseline = expected[identifier]
    if (case["config"] != baseline["config"] or case["config_sha256"] != canonical_digest(case["config"]) or
            any(case.get(k) != baseline[k] for k in ("pair_id", "model", "task", "seed", "initialization")) or
            Path(case.get("run_directory", "")).as_posix() != "runs/arxiv-v1/cases/" + identifier):
        raise ValueError("Selected primary identity, full recipe or output path differs")
    configs = select_pair(matrix, case["pair_id"])
    for mode, config in configs.items():
        other = expected[case["pair_id"] + "--" + mode]
        if config != other["config"]:
            raise ValueError("Paired case differs from its frozen full training recipe")
    source = matrix["registry"]["datasets"][TASK_DATASETS[case["task"]]]
    return dict(case=case, configs=configs, counts=source["split_counts"],
                source_structures=source["structures"], matrix_sha256=canonical_digest(matrix))


def compatible_sources(commits):
    repository = Path(__file__).resolve().parents[4]
    if Path.cwd().resolve() != repository:
        raise ValueError("Run from the immutable source checkout with its data/models/runs links")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise ValueError("Formal execution requires clean tracked source")
    paths = ["src/universal_gnn/" + name for name in CRITICAL]
    paths += ["src/universal_gnn/benchmarks/" + name for name in CAPACITY_SOURCES]
    for previous in set(commits):
        if not isinstance(previous, str) or len(previous) != 40:
            raise ValueError("Preparation worker lacks its executed source commit")
        changed = subprocess.check_output(["git", "diff", "--name-only", previous, head, "--", *paths], text=True).splitlines()
        if any(name.endswith(".py") for name in changed):
            raise ValueError("Model/training/graph code differs from the accepted preparation")
    return head


def installed_versions():
    values = {}
    for name in PACKAGES:
        try:
            values[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            values[name] = None
    return values


def checked_config(actual, expected, common, counts):
    result = copy.deepcopy(actual)
    statistics = result["backbone"].pop("neighbor_statistics", None)
    if expected["backbone"]["initialization"] == "scratch" and expected["backbone"]["name"] in {"mace", "nequip"}:
        if (not isinstance(statistics, dict) or statistics.get("structures") != counts["train"] or
                statistics.get("declared_training_structures") != counts["train"] or statistics.get("partition") != "train" or
                statistics.get("source_sha256") != expected["dataset"]["sha256"] or
                statistics.get("manifest_sha256") != expected["dataset"]["split_manifest_sha256"] or
                statistics.get("dtype") != expected["dtype"]):
            raise ValueError("Native scratch normalization must cover the full bound training partition")
    elif statistics is not None:
        raise ValueError("Unexpected native calibration")
    result["batch_size"] = expected["batch_size"]
    if actual["batch_size"] != common or result != expected:
        raise ValueError("Resolved case changed beyond common batch and native training statistics")


def check_artifact_identity(official, definition, artifacts, provider):
    expected = dict(definition.get("artifact_sha256", {}))
    if provider == "nequip" and official.get("initialization") == "scratch":
        expected["blueprint"] = artifacts[NEQUIP_ARCHITECTURE[0]]["sha256"]
    if (not expected or official.get("sha256") != expected or
            not set(expected.values()) <= {a["sha256"] for a in artifacts.values()}):
        raise ValueError("Capacity/original graph used a different public artifact")


def check_preparation(matrix, identifier, preparation, *, budget_seconds, allow_generation=False):
    """Slurm-only full-source gate; reads evidence and never trains or submits jobs."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal preparation checks must run through Slurm")
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or budget_seconds <= 0:
        raise ValueError("Declare a finite positive wall-time budget in seconds")
    spec = case_spec(matrix, identifier, allow_generation=allow_generation)
    return _check_prepared_spec(matrix, spec, preparation, budget_seconds=budget_seconds)


def _check_prepared_spec(matrix, spec, preparation, *, budget_seconds):
    """Evidence checks for a caller-validated, closed primary or supplemental spec."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal preparation checks must run through Slurm")
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or budget_seconds <= 0:
        raise ValueError("Declare a finite positive wall-time budget in seconds")
    case, configs, counts = spec["case"], spec["configs"], spec["counts"]
    generation = case["task"] == "generation"
    supplemental = spec.get("definition_kind") == "arxiv_v1_supplemental_tensor_definitions"
    preparation = Path(preparation)
    prepared = read_json(preparation / "report.json")
    identity_ok = (prepared.get("pair_id") == case["pair_id"] and
                   prepared.get("kind") == "full_generation_pair_preparation") if generation else (
                   prepared.get("model") == case["model"] and prepared.get("task") == case["task"])
    if supplemental:
        identity_ok = (identity_ok and prepared.get("kind") == "full_supplemental_tensor_pair_preparation" and
                       prepared.get("pair_id") == case["pair_id"] and prepared.get("seed") == case["seed"])
    if (prepared.get("status") != "passed" or prepared.get("stage") != "complete" or
            prepared.get("definition_sha256" if supplemental else "matrix_sha256") != spec["matrix_sha256"] or not identity_ok or
            prepared.get("cuda_acceptance") is False):
        raise ValueError("Preparation is incomplete, not CUDA-accepted, or belongs to another case")
    capacity_root = preparation / "train-capacity" if generation else Path(prepared.get("capacity_path", str(preparation / "capacity")))
    graph_root = Path(prepared.get("graph_scan_path", str(preparation / "graph-scan")))
    scan, probe = read_json(graph_root / "report.json"), read_json(graph_root / "probe.json")
    capacity = read_json(capacity_root / "report.json")
    config = configs["pretrained"]
    manifest = read_json(config["dataset"]["split_manifest"])
    validate_manifest(manifest, source_sha256=config["dataset"]["sha256"], source_count=spec["source_structures"])
    if manifest["counts"] != counts or canonical_digest(manifest) != config["dataset"]["split_manifest_sha256"]:
        raise ValueError("Frozen complete split differs")
    if file_sha(config["dataset"]["path"]) != config["dataset"]["sha256"]:
        raise ValueError("Current full source bytes differ")
    coverage = probe.get("coverage", {})
    definition = coverage.get("graph_definition", {})
    if (scan.get("status") != "complete" or scan.get("structures") != counts["train"] or
            scan.get("probe_sha256") != canonical_digest(probe) or
            scan.get("graph_binding") != coverage.get("binding") or
            not coverage.get("verified_full_training_scan") or coverage.get("structures") != counts["train"] or
            coverage["binding"].get("source_sha256") != config["dataset"]["sha256"] or
            coverage["binding"].get("split_manifest_sha256") != config["dataset"]["split_manifest_sha256"] or
            coverage["binding"].get("graph_definition_sha256") != canonical_digest(definition) or
            definition.get("provider") != case["model"] or definition.get("dtype") != config["dtype"]):
        raise ValueError("Missing source-bound full original/auxiliary graph coverage")
    records = [dict(id=manifest["records"][i]["id"], source_index=i) for i in manifest["partitions"]["train"]]
    selection = probe["selection"]
    with (graph_root / "graph-sizes.jsonl").open(encoding="utf-8") as stream:
        rebuilt = select_probe((json.loads(line) for line in stream), records, coverage["binding"],
            **{k: selection[k] for k in ("seed", "worst_per_metric", "ordinary_count")},
            warmup_batches=probe["warmup_batches"], measure_batches=probe["measure_batches"])
    if (any(rebuilt[k] != probe[k] for k in ("indices", "worst_indices", "selection")) or
            any(rebuilt["coverage"][k] != coverage[k] for k in ("sums", "maxima", "graph_size_rows_sha256"))):
        raise ValueError("Full graph rows or selected extrema differ from accepted evidence")
    if (capacity.get("configs") != configs or capacity.get("phase") != "train" or
            capacity.get("input_config_sha256") != {k: canonical_digest(v) for k, v in configs.items()}):
        raise ValueError("Capacity belongs to another original task/seed/configuration")
    evidence = verify_capacity_evidence(capacity_root, probe)
    common, workers = evidence["common_batch_size"], evidence["successful_workers"]
    if common > config["batch_size"]:
        raise ValueError("Capacity cannot increase the frozen initial batch")
    resolved = {}
    prior, generation_definition = None, None
    if generation:
        from ..generation.preparation import generation_spec
        from ..generation.evidence import validate_prior, checked_generation_config, check_sampling_capacity

        generation_definition = generation_spec(matrix, case["pair_id"])
        prior = prepared.get("training_prior")
        validate_prior(prior, counts["train"])
    for mode in ("pretrained", "scratch"):
        actual = read_json(capacity_root / ("config." + mode + ".resolved.json"))
        if generation:
            checked_generation_config(actual, configs[mode], common, counts, prior)
        else:
            checked_config(actual, configs[mode], common, counts)
        if canonical_digest(actual) != capacity["resolved_config_sha256"][mode]:
            raise ValueError("Final resolved capacity configuration hash differs")
        resolved[mode] = actual
    train_worker_count = len(workers)
    sampling_evidence = None
    if generation:
        sampling_evidence = check_sampling_capacity(preparation, configs, resolved, probe, counts, prior,
                                                    generation_definition["sampling_preflight"])
        if (prepared.get("training_batch_size") != common or
                prepared.get("sampling_batch_size") != sampling_evidence["common_batch_size"]):
            raise ValueError("Generation preparation mixed its training and sampling batches")
        workers = workers + sampling_evidence["successful_workers"]
    versions, seconds = installed_versions(), []
    artifacts = matrix["registry"]["artifacts"][case["model"]]["files"]
    for name, artifact in artifacts.items():
        if file_sha(Path("models/official") / name) != artifact["sha256"]:
            raise ValueError("Current public checkpoint/constructor artifact differs")
    for index, worker in enumerate(workers):
        official = worker["execution"]["official"]
        check_artifact_identity(official, definition, artifacts, case["model"])
        if (worker.get("selected_training_structures") != counts["train"] or
                worker.get("measured_structures") != worker["measured_batches"] * worker["batch_size"] or
                any(worker["versions"].get(k) != v for k, v in versions.items())):
            raise ValueError("Worker data coverage or current dependency versions differ")
        mode = official["initialization"]
        if mode == "scratch":
            if official.get("parameter_coverage") != 0. or official.get("buffer_coverage") != 0. or not official.get("state_layout_verified"):
                raise ValueError("Scratch must freshly initialize the whole original backbone")
        elif mode != "pretrained" or official.get("parameter_coverage") != 1.:
            raise ValueError("Missing complete original pretrained parameters")
        elapsed = worker["elapsed_seconds"]
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0:
            raise ValueError("Missing measured capacity timing")
        if generation and worker.get("resolved_generation", {}).get("generation_prior") != prior:
            raise ValueError("Generation worker used another fitted training prior")
        if index < train_worker_count:
            seconds.append(elapsed / worker["measured_batches"])
    physical = {}
    if case["task"] in {"forcefield", "dielectric", "piezoelectric", "elastic"}:
        for mode in ("pretrained", "scratch"):
            path = preparation / ("derivatives-" + mode + ".json")
            value = read_json(path)
            mandatory = ("forces_finite_difference", "stress_finite_difference") if case["task"] == "forcefield" else ("response_auxiliary_finite_difference",)
            if (not value.get("passed") or not str(value.get("device", "")).startswith("cuda") or
                    value.get("dtype") != "torch.float32" or not value.get("checks") or
                    any(not value["checks"].get(k, {}).get("required") for k in mandatory) or
                    any(not c["passed"] for c in value["checks"].values() if c["required"])):
                raise ValueError("Both initializations require passed derivative/geometry evidence")
            physical[mode] = file_sha(path)
    commit = compatible_sources([prepared["git_commit"], scan["git_commit"]] + [w["execution"]["git_commit"] for w in workers])
    train_estimate = max(seconds) * math.ceil(counts["train"] / common) * config["epochs"]
    if budget_seconds < 1.5 * train_estimate:
        raise ValueError("Declared budget lacks the measured training estimate plus50% validation/IO reserve")
    result = dict(status="passed", kind="formal_generation_execution_gate" if generation else "formal_predictive_execution_gate", case=case,
                config=resolved[case["initialization"]], counts=counts, source_structures=spec["source_structures"],
                matrix_sha256=spec["matrix_sha256"], git_commit=commit, versions=versions,
                preparation=str(preparation), preparation_sha256=file_sha(preparation / "report.json"),
                physical_evidence_sha256=physical, common_batch_size=common,
                backbone_cutoff=definition["cutoff"],
                capacity_evidence={k: v for k, v in evidence.items() if k != "successful_workers"},
                budget_seconds=budget_seconds, probed_train_only_seconds=train_estimate,
                interpretation="Full source/graph/paired-capacity/physical evidence; timing is a probe estimate, not a runtime guarantee. No training launched by this check.")
    if generation:
        result.update(training_prior=prior, quality_protocol=generation_definition["quality"],
                      sampling_batch_size=sampling_evidence["common_batch_size"],
                      probed_sample_batch_seconds=max(w["elapsed_seconds"] / w["measured_batches"] for w in sampling_evidence["successful_workers"]),
                      sampling_capacity_evidence={k: v for k, v in sampling_evidence.items() if k != "successful_workers"})
    return result
