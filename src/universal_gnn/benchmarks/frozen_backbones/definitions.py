"""Full-data head-only dielectric/forcefield definitions and original source audit."""

import copy
import hashlib
import json
from pathlib import Path

from ..execution.gates import canonical_digest, case_spec, read_json
from ..experiments.recipes import TASK_DATASETS
from ..experiments.registry import DATASETS, MODELS, inspect_dataset
from ..prediction_assessment.contracts import UNITS, finite_shape

PRIMARY_SHA = "b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651"
TASKS = ("dielectric", "forcefield")


def build_frozen_definitions(primary):
    if canonical_digest(primary) != PRIMARY_SHA:
        raise ValueError("Require the original frozen947 primary matrix")
    cases = []
    for task in TASKS:
        for provider in MODELS:
            original = "seed-123--" + task + "--" + provider + "--pretrained"
            spec = case_spec(primary, original)
            template = spec["case"]
            config = copy.deepcopy(template["config"])
            if (config["optimization"]["train_backbone"] is not True or
                    config["optimization"]["train_readout"] is not True or
                    config["backbone"]["initialization"] != "pretrained" or config["prediction"]["head_mode"] != "reset"):
                raise ValueError("Frozen ablation requires the original full pretrained/reset recipe")
            config["optimization"]["train_backbone"] = False
            identifier = "frozen--seed-123--" + task + "--" + provider
            cases.append(dict(id=identifier, model=provider, task=task, seed=123, initialization="pretrained",
                optimization_mode="frozen_backbone", config=config, config_sha256=canonical_digest(config),
                counts=copy.deepcopy(spec["counts"]), source_structures=spec["source_structures"],
                config_path="configs/" + identifier + ".json", run_directory="runs/arxiv-v1/frozen-cases/" + identifier,
                python_environment=template["python_environment"], slurm=copy.deepcopy(template["slurm"]),
                preflight=copy.deepcopy(template["preflight"]), reference_finetune_case=original,
                reference_scratch_case=original.rsplit("--", 1)[0] + "--scratch",
                required_frozen_checks=["backbone_parameters_and_buffers_exact", "all_backbone_modules_eval",
                    "no_backbone_optimizer_ownership_or_gradients", "readout_mixed_gradients_nonzero",
                    "input_derivatives_remain_live", "original_full_data_capacity_and_physics",
                    "complete_validation_best_test_and_independent_acceptance"], status="defined_not_preflighted"))
    return dict(version=1, kind="arxiv_v1_frozen_backbone_definitions", primary_matrix_sha256=PRIMARY_SHA,
        training_seeds=[123], defined_training_runs=8, formal_training_runs=0, cases=cases,
        interpretation="Separate head-only pretrained ablations on complete original dielectric/forcefield data; only train_backbone changes. Not part of primary48 or high-rank16.")


def inspect_frozen_inputs(primary, *, repository="."):
    build_frozen_definitions(primary)
    repository = Path(repository)
    result = {}
    for task in TASKS:
        dataset = TASK_DATASETS[task]
        expected = primary["registry"]["datasets"][dataset]
        observed = inspect_dataset(repository, dataset, DATASETS[dataset])
        if observed != expected:
            raise ValueError("Complete source/split/audit differs from the original947 registry")
        config = case_spec(primary, "seed-123--" + task + "--cgcnn--pretrained")["case"]["config"]
        names = ("total_energy", "forces") if task == "forcefield" else ("dielectric",)
        bindings = config["dataset"]["bindings"]
        if set(bindings) != set(names) or any(bindings[name] != {"key": bindings[name].get("key"), "unit": UNITS[name]} or
                not isinstance(bindings[name].get("key"), str) or not bindings[name]["key"] for name in names):
            raise ValueError("Frozen ablation requires original explicit raw label/unit bindings")
        source = repository / observed["path"]
        manifest = read_json(repository / observed["split_manifest"])
        count, atoms, maximum = 0, 0, 0
        components = {name: 0 for name in names}
        zero_labels = {name: 0 for name in names}
        digest = hashlib.sha256()
        def leaves(value):
            if isinstance(value, list):
                for child in value: yield from leaves(child)
            else: yield value
        with source.open("rb") as stream:
            for raw in stream:
                digest.update(raw)
                if not raw.strip(): continue
                row = json.loads(raw)
                if count >= observed["structures"] or row.get("id") != manifest["records"][count]["id"]:
                    raise ValueError("Frozen complete ordered source IDs differ")
                geometry = row.get("atoms", row)
                numbers = geometry.get("numbers")
                if not isinstance(numbers, list) or not numbers or any(type(z) is not int or not 1 <= z <= 118 for z in numbers):
                    raise ValueError("Frozen source has invalid original atom numbers")
                for name in names:
                    value = row["targets"][bindings[name]["key"]]
                    shape = () if name == "total_energy" else (len(numbers), 3) if name == "forces" else (3, 3)
                    components[name] += finite_shape(value, shape)
                    zero_labels[name] += all(v == 0 for v in leaves(value))
                count += 1
                atoms += len(numbers)
                maximum = max(maximum, len(numbers))
        if count != observed["structures"] or digest.hexdigest() != observed["sha256"]:
            raise ValueError("Frozen complete source changed during raw label audit")
        result[task] = dict(dataset=dataset, structures=count, source_sha256=digest.hexdigest(),
            split_manifest_sha256=observed["split_manifest_sha256"], counts=observed["split_counts"],
            maximum_atoms=maximum, atoms=atoms, finite_raw_components=components,
            whole_zero_labels=zero_labels, original_bindings=copy.deepcopy(bindings), filtered_structures=0)
    return result


def write_frozen_definitions(primary, output, *, repository="."):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Frozen definition output must be fresh")
    definitions = build_frozen_definitions(primary)
    inputs = inspect_frozen_inputs(primary, repository=repository)
    output.mkdir(parents=True, exist_ok=False)
    (output / "configs").mkdir()
    for case in definitions["cases"]:
        (output / case["config_path"]).write_bytes(json.dumps(case["config"], indent=2, allow_nan=False).encode())
    definitions["full_input_audit"] = inputs
    (output / "definitions.json").write_bytes(json.dumps(definitions, indent=2, allow_nan=False).encode())
    return definitions
