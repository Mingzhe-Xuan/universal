"""Prepare all planned primary comparisons; no training or Slurm submission."""

import copy
import json
import math
from pathlib import Path

from .registry import DATASETS, MODELS, NEQUIP_ARCHITECTURE, PROFILES, canonical_digest

TASKS = ("classification", "bandgap", "dielectric", "spectrum", "forcefield", "generation")
INITIALIZATIONS = ("pretrained", "scratch")
SEEDS = (123, 456, 789)
TASK_DATASETS = dict(classification="jarvis-gap", bandgap="jarvis-gap", dielectric="gmtnet-dielectric",
                     spectrum="jarvis-phonon-dos", forcefield="mlearn-forcefield", generation="perov5")
BATCHES = dict(classification=32, bandgap=32, dielectric=4, spectrum=32, forcefield=4, generation=16)
GATES = ("official_initialization_numerical", "whole_backbone_update", "original_prediction_equivalence", "derivative_numerical",
         "complete_training_graph_scan", "paired_cuda_capacity", "minimum_20GiB_disk_reserve")


def validate_registry(registry):
    if (not isinstance(registry, dict) or type(registry.get("version")) is not int or
            registry["version"] != 1 or registry.get("kind") != "arxiv_v1_full_inputs"):
        raise ValueError("A frozen full-input registry is required")
    if (not isinstance(registry.get("datasets"), dict) or not isinstance(registry.get("artifacts"), dict) or
            set(registry["datasets"]) != set(DATASETS) or set(registry["artifacts"]) != set(MODELS)):
        raise ValueError("Require all five full datasets and four original models")
    for name, (sha, counts) in DATASETS.items():
        entry = registry["datasets"][name]
        if not isinstance(entry, dict):
            raise ValueError("Dataset registry entries must be mappings")
        if (entry.get("sha256") != sha or entry.get("structures") != sum(counts) or
                entry.get("split_counts") != dict(zip(("train", "validation", "test"), counts))):
            raise ValueError(f"{name}: registry does not describe the registered complete data")
        from universal_gnn.data.identity import check_expected_digest

        check_expected_digest(entry.get("split_manifest_sha256"), entry.get("split_manifest_sha256"), "split_manifest_sha256")
        if entry.get("split_manifest_sha256") is None:
            raise ValueError("A frozen canonical split SHA is required")
        if (entry.get("path") != f"data/arxiv-v1/{name}/structures.jsonl" or
                entry.get("split_manifest") != f"data/arxiv-v1/{name}/split.json"):
            raise ValueError(f"{name}: registry source paths differ from the registered complete dataset")
    for model in MODELS:
        source = registry["artifacts"][model]
        if not isinstance(source, dict) or not isinstance(source.get("files"), dict):
            raise ValueError("Original artifact entries must be mappings")
        expected = dict(PROFILES[model]["files"])
        if model == "nequip":
            expected[NEQUIP_ARCHITECTURE[0]] = NEQUIP_ARCHITECTURE[1]
        if source.get("source") != PROFILES[model]["source"] or set(source.get("files", {})) != set(expected):
            raise ValueError(f"{model}: registry lacks its original source artifacts")
        for filename, sha in expected.items():
            entry = source["files"][filename]
            if not isinstance(entry, dict) or entry.get("sha256") != sha or type(entry.get("bytes")) is not int or entry["bytes"] < 1:
                raise ValueError(f"{model}: registry original artifact digest/size is invalid")


def _config(registry, model, task, mode, seed, *, epochs, learning_rate, patience):
    source = registry["datasets"][TASK_DATASETS[task]]
    dataset = {key: copy.deepcopy(source[key]) for key in ("path", "sha256", "split_manifest", "split_manifest_sha256")}
    dataset["partition"] = "train"
    config = dict(schema_version=1, seed=seed, structures="all", dtype="float32", device="cuda",
                  batch_size=BATCHES[task], max_atoms=None, shuffle=True, epochs=epochs, learning_rate=learning_rate,
                  checkpoint_every=1, clip_grad_norm=10., report_predictions=False, report_structure_limit=0,
                  evaluation=dict(patience=patience, min_delta=0.), backbone=dict(name=model, implementation="official", initialization=mode),
                  dataset=dataset)
    if task == "generation":
        config.update(task=dict(kind="generation", sampling=dict(steps=100, inner_steps=2)),
                      generation_corruption="per_epoch_structure_v2", validate_sampling=False)
        return config
    if task == "forcefield":
        config["task"] = dict(kind="forcefield", supervised_outputs=["energy", "forces"], loss_weights=dict(energy=1., forces=1.))
        dataset["bindings"] = dict(energy=dict(key="energy", unit="eV"), forces=dict(key="forces", unit="eV/angstrom"))
        readout = dict(name="node_mlp", pooling="sum", hidden_features=[128, 64], activation="silu")
    else:
        config["task"] = dict(kind="supervised", property=task)
        units = dict(classification="class", bandgap="eV", dielectric="dimensionless", spectrum="dataset_defined")
        dataset["bindings"] = {task: dict(key=task, unit=units[task])}
        if task == "spectrum":
            config["task"]["channels"] = 200
        readout = (dict(name="response", pooling="mean") if task == "dielectric" else
                   dict(name="graph_mlp", pooling="mean", hidden_features=[128, 64], activation="silu"))
    if task == "dielectric" and model in ("mace", "nequip"):
        readout["feature_processing"] = dict(name="equivariant", profile="small_response", basis_version=2)
    elif task != "dielectric" and model in ("mace", "nequip"):
        readout["feature_processing"] = dict(name="scalar_invariants")
    config["prediction"] = dict(version=1, head_mode="reset", readout=readout)
    config["optimization"] = dict(train_backbone=True, train_readout=True)
    if task == "forcefield" and model == "cgcnn":
        config["optimization"]["backbone_eval"] = True
    return config


def build_matrix(registry, *, seeds=SEEDS, epochs=300, learning_rate=3e-4, patience=30, run_root="runs/arxiv-v1/cases"):
    validate_registry(registry)
    seeds = tuple(seeds)
    if (not seeds or len(set(seeds)) != len(seeds) or
            any(type(seed) is not int or not 0 <= seed < 2**63 for seed in seeds)):
        raise ValueError("Training seeds must be distinct nonnegative 63-bit integers")
    if type(epochs) is not int or epochs < 1 or type(patience) is not int or patience < 1:
        raise ValueError("Epochs and patience must be positive integers")
    if type(learning_rate) not in (int, float) or not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("Learning rate must be finite and positive")
    cases, pairs = [], []
    for seed in seeds:
        for task in TASKS:
            for model in MODELS:
                pair = f"seed-{seed}--{task}--{model}"
                identifiers = []
                for mode in INITIALIZATIONS:
                    identifier = pair + "--" + mode
                    config = _config(registry, model, task, mode, seed, epochs=epochs, learning_rate=learning_rate, patience=patience)
                    case = dict(id=identifier, pair_id=pair, model=model, task=task, initialization=mode, seed=seed,
                                config=config, config_sha256=canonical_digest(config), config_path=f"configs/{identifier}.json",
                                run_directory=str(Path(run_root) / identifier), python_environment="universal-mace" if model == "mace" else
                                "universal" if model == "nequip" else "universal-official",
                                slurm=dict(partition="compute", node="node42", gpus=1, cpus_per_task=2,
                                           memory_gib=64 if task in ("dielectric", "forcefield") else 32, time="24:00:00"),
                                preflight=dict(warmup_batches=2, measure_batches=100, initial_batch_size=BATCHES[task]),
                                required_gates=list(GATES), status="planned_not_launched")
                    if task == "generation":
                        case["generation_quality"] = dict(samples=1000, draws_per_condition=5, seed=456,
                                                          interpretation="conditional geometry only; no DFT stability claim")
                        case["sampling_preflight"] = dict(warmup_batches=1, measure_batches=5, initial_batch_size=4)
                        case["required_gates"].extend(("heldout_generation_protocol", "sampling_cuda_capacity"))
                    cases.append(case);identifiers.append(identifier)
                pairs.append(dict(id=pair, cases=identifiers, batch_policy="common minimum accepted size; revalidate both before training"))
    return dict(version=1, kind="arxiv_v1_primary_matrix", status="prepared_not_launched", seeds=list(seeds),
                registry=copy.deepcopy(registry), registry_sha256=canonical_digest(registry), cases=cases, pairs=pairs,
                expected_training_runs=len(MODELS)*len(TASKS)*len(INITIALIZATIONS)*len(seeds), completed_training_runs=0,
                interpretation="full primary definitions only; runtime/capacity gates and independent evaluation still required")


def write_matrix(matrix, output):
    cases = matrix.get("cases", [])
    if not cases or len(cases) != matrix.get("expected_training_runs"):
        raise ValueError("A complete primary definition matrix is required")
    identifiers = [case.get("id") for case in cases]
    if (any(not isinstance(name, str) or not name or "/" in name or "\\" in name or Path(name).name != name for name in identifiers) or
            len(set(identifiers)) != len(identifiers)):
        raise ValueError("Case IDs must be unique safe basenames")
    if any(case.get("config_sha256") != canonical_digest(case["config"]) for case in cases):
        raise ValueError("Case configuration differs from its recorded digest")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    config_directory = output / "configs";config_directory.mkdir()
    for case in cases:
        with (config_directory / (case["id"] + ".json")).open("x", encoding="utf-8") as stream:
            json.dump(case["config"], stream, indent=2, allow_nan=False)
            stream.write("\n")
    with (output / "matrix.json").open("x", encoding="utf-8") as stream:
        json.dump(matrix, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return output / "matrix.json"
