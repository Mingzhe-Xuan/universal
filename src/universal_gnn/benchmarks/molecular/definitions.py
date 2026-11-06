"""Eight original-backbone and one directory-plugin nonperiodic supplements."""

import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

from ..execution.gates import case_spec
from ..experiments.registry import MODELS, canonical_digest
from ..pairing.capacity import validate_pair
from universal_gnn.data.preparation.rmd17.conversion import KCAL_MOL_TO_EV
from .source import AUDIT_SHA, COUNTS, DATA_ROOT, RAW_ROOT, SOURCE_SHA, SPLIT_FILE_SHA, inspect_molecular_inputs


PRIMARY_SHA = "b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651"
PLUGIN_DIRECTORY = "examples/custom_knn_gcn"
GATES = ["official_initialization_numerical", "original_prediction_equivalence",
         "complete_nonperiodic_source_and_native_graphs", "training_only_native_statistics",
         "actual_cuda_capacity_100batches_and_mixed_extrema", "unchanged_position_derivative_and_mixed_gradient_checks",
         "original_weights_and_parameter_layout", "full_validation_best_test_and_independent_acceptance",
         "minimum_20GiB_disk_reserve"]


def _source_contract(inputs):
    if (not isinstance(inputs, dict) or inputs.get("kind") != "arxiv_v1_complete_molecular_inputs"
            or inputs.get("status") != "passed" or type(inputs.get("version")) is not int or inputs["version"] != 1
            or inputs.get("audit_sha256") != AUDIT_SHA or inputs.get("split_file_sha256") != SPLIT_FILE_SHA
            or inputs.get("counts") != COUNTS or inputs.get("structures") != 100000
            or inputs.get("source_sha256") != SOURCE_SHA or inputs.get("energy_components") != 100000
            or inputs.get("force_components") != 2700000 or inputs.get("excluded_records") != 0
            or inputs.get("official_test_cohort_count") != 1000 or inputs.get("author_development_count") != 1000
            or inputs.get("training_rng_used_for_split") is not False
            or inputs.get("maximum_atoms") != 9 or inputs.get("atoms") != 900000
            or inputs.get("atomic_numbers_present") != [1, 6, 8]
            or inputs.get("unit_conversion_factor") != KCAL_MOL_TO_EV
            or inputs.get("units") != dict(positions="angstrom", total_energy="eV", forces="eV/angstrom")):
        raise ValueError("Require complete accepted ethanol source/count/author-split metadata")
    dataset = inputs.get("dataset")
    if (not isinstance(dataset, dict) or set(dataset) != {"path", "sha256", "split_manifest", "split_manifest_sha256"}
            or dataset.get("sha256") != SOURCE_SHA
            or any(not isinstance(dataset.get(k), str) or not dataset[k] for k in ("path", "split_manifest"))
            or not isinstance(dataset.get("split_manifest_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", dataset["split_manifest_sha256"])):
        raise ValueError("Molecular config requires frozen source and canonical manifest SHA")
    return dataset


def build_molecular_definitions(primary, inputs, *, repository="."):
    if canonical_digest(primary) != PRIMARY_SHA:
        raise ValueError("Require the original immutable947 primary recipes")
    source = _source_contract(inputs)
    cases, pairs = [], []
    reference = {}
    for provider in MODELS:
        pair = "molecular--seed-123--forcefield--" + provider
        configs, ids = {}, []
        for mode in ("pretrained", "scratch"):
            template = case_spec(primary, "seed-123--forcefield--" + provider + "--" + mode)["case"]
            reference[provider] = template
            config = copy.deepcopy(template["config"])
            config["dataset"] = dict(copy.deepcopy(source), partition="train",
                bindings=copy.deepcopy(template["config"]["dataset"]["bindings"]))
            if provider in {"cgcnn", "alignn"}:
                config["backbone"].update(input_profile="molecular_radius", input_cutoff=6.)
            identifier = pair + "--" + mode
            cases.append(dict(id=identifier, pair_id=pair, model=provider, task="forcefield", seed=123,
                initialization=mode, role="official_molecular_transfer", config=config,
                config_sha256=canonical_digest(config), config_path="configs/" + identifier + ".json",
                run_directory="runs/arxiv-v1/molecular-cases/" + identifier,
                python_environment=template["python_environment"], counts=dict(COUNTS), source_structures=100000,
                evaluation_cohorts=["official_test_01"], slurm=copy.deepcopy(template["slurm"]),
                preflight=copy.deepcopy(template["preflight"]), required_gates=list(GATES), status="defined_not_preflighted"))
            configs[mode] = config
            ids.append(identifier)
        validate_pair(configs)
        pairs.append(dict(id=pair, cases=ids, batch_policy="common minimum accepted size; only typed OOM may reduce and revalidate both"))
    template = reference["cgcnn"]
    config = copy.deepcopy(template["config"])
    config["dataset"] = dict(copy.deepcopy(source), partition="train",
        bindings=copy.deepcopy(template["config"]["dataset"]["bindings"]))
    config["backbone"] = dict(name="plugin:" + PLUGIN_DIRECTORY, implementation="legacy", width=16, layers=2, cutoff=6.)
    config["graph"] = dict(name="plugin:" + PLUGIN_DIRECTORY, k=2)
    config["optimization"] = dict(train_backbone=True, train_readout=True)
    identifier = "molecular-plugin--seed-123--forcefield--knn-gcn--scratch"
    paths = [PLUGIN_DIRECTORY + "/" + name for name in ("plugin.py", "model.py", "graph.py")]
    plugin = dict(directory=PLUGIN_DIRECTORY, source_line_endings="LF", source_sha256={
        name: hashlib.sha256((Path(repository) / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in paths})
    cases.append(dict(id=identifier, pair_id=None, model="custom_knn_gcn", task="forcefield", seed=123,
        initialization="scratch", role="directory_plugin_extension", config=config, config_sha256=canonical_digest(config),
        config_path="configs/" + identifier + ".json", run_directory="runs/arxiv-v1/molecular-cases/" + identifier,
        python_environment="universal-official", counts=dict(COUNTS), source_structures=100000,
        evaluation_cohorts=["official_test_01"], slurm=copy.deepcopy(template["slurm"]),
        preflight=copy.deepcopy(template["preflight"]), plugin=plugin,
        required_gates=[g for g in GATES if g not in {"original_weights_and_parameter_layout",
                       "official_initialization_numerical", "original_prediction_equivalence"}] +
                       ["directory_source_and_standard_graph_gnn_contract", "direct_plugin_feature_equivalence"],
        status="defined_not_preflighted"))
    return dict(version=1, kind="arxiv_v1_molecular_supplement_definitions", primary_matrix_sha256=PRIMARY_SHA,
        input_audit=copy.deepcopy(inputs), cases=cases, pairs=pairs, training_seeds=[123],
        defined_training_runs=9, official_training_runs=8, plugin_training_runs=1, formal_training_runs=0,
        interpretation="Separate900/100/99000 nonPBC ethanol supplements,8original-model paired transfers and1existingKNN+GCNplugin scratch case. Primary48/acceptedMLearn unchanged. Definitions/source audit are not graph/CUDA/capacity/physics/training/quality acceptance.")


def write_molecular_definitions(primary, output, *, data_directory=DATA_ROOT, raw_directory=RAW_ROOT, repository=".", execution=None):
    import os

    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Complete molecular source inspection/export requires Slurm")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Molecular definition output must be fresh")
    if shutil.disk_usage(repository).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB free disk reserve")
    inputs = inspect_molecular_inputs(data_directory, raw_directory)
    definitions = build_molecular_definitions(primary, inputs, repository=repository)
    if execution is not None:
        definitions["definition_execution"] = copy.deepcopy(execution)
    output.mkdir(parents=True, exist_ok=False)
    (output / "configs").mkdir()
    for case in definitions["cases"]:
        (output / case["config_path"]).write_bytes(json.dumps(case["config"], indent=2, allow_nan=False).encode())
    (output / "input-audit.json").write_bytes(json.dumps(inputs, indent=2, allow_nan=False).encode())
    temporary = output / "definitions.json.tmp"
    temporary.write_bytes(json.dumps(definitions, indent=2, allow_nan=False).encode())
    temporary.replace(output / "definitions.json")
    return definitions
