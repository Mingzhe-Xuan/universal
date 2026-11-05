"""Separate full-data rank3/4 experiment definitions; never launch training."""

import copy
import hashlib
import json
from pathlib import Path

from ..execution.gates import case_spec, file_sha
from ..experiments.registry import MODELS, canonical_digest
from ..pairing.capacity import validate_pair
from ..prediction_assessment.contracts import finite_shape
from universal_gnn.data.splits import validate_manifest
from universal_gnn.properties import property_spec

PRIMARY_SHA = "b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651"
DATASETS = {
    "piezoelectric": dict(sha256="0a95db91e59ef60a36007f6e333fd3507b1c01356474bf817e6f30aa9e820cd3",
        split_manifest_sha256="e38c37d147488ba17ed9b3bb289c5f54a51853528edc62e26104ccea65ea09ad",
        counts=dict(train=3998, validation=502, test=500), structures=5000),
    "elastic": dict(sha256="32749c56441bf47b4411596ca68afb27d3aa2d8aba7698551c239eea2002793f",
        split_manifest_sha256="d3e9a3c8ac74b0d73e38a3cc9c02afaaeca5867f179f13040133a59e77d1d34e",
        counts=dict(train=11587, validation=1442, test=1470), structures=14499),
}
DATA_ROOT = "data/arxiv-v1/supplemental-rank34-1074"
PREPARATION_SHA = "db6422c176e5f17124d95772f24c4615a4f613cc3c813807a216b09192dbb43e"
VERIFICATION_SHA = "aba30b9e893c1ab41cd9c16679cf815f9ac9fa16c20a9e63f02ed1bdb603a059"


def build_tensor_definitions(primary):
    if canonical_digest(primary) != PRIMARY_SHA:
        raise ValueError("Require the original frozen947 primary matrix")
    cases, pairs = [], []
    for task, source in DATASETS.items():
        spec = property_spec(task)
        for provider in MODELS:
            pair = "rank34--seed-123--" + task + "--" + provider
            configs, identifiers = {}, []
            for mode in ("pretrained", "scratch"):
                template = case_spec(primary, "seed-123--dielectric--" + provider + "--" + mode)["case"]
                config = copy.deepcopy(template["config"])
                config["task"] = dict(kind="supervised", property=task)
                config["dataset"] = dict(path=DATA_ROOT + "/" + task + "/structures.jsonl", sha256=source["sha256"],
                    split_manifest=DATA_ROOT + "/" + task + "/split.json", split_manifest_sha256=source["split_manifest_sha256"],
                    partition="train", bindings={task: dict(key=task, unit=spec.unit)})
                identifier = pair + "--" + mode
                case = dict(id=identifier, pair_id=pair, task=task, model=provider, seed=123, initialization=mode,
                    config=config, config_sha256=canonical_digest(config), config_path="configs/" + identifier + ".json",
                    run_directory="runs/arxiv-v1/supplemental-cases/" + identifier,
                    python_environment=template["python_environment"], counts=copy.deepcopy(source["counts"]),
                    source_structures=source["structures"], tensor_shape=list(spec.shape), unit=spec.unit,
                    slurm=copy.deepcopy(template["slurm"]), preflight=copy.deepcopy(template["preflight"]),
                    required_gates=copy.deepcopy(template["required_gates"]), status="defined_not_preflighted")
                cases.append(case); identifiers.append(identifier); configs[mode] = config
            validate_pair(configs)
            pairs.append(dict(id=pair, cases=identifiers,
                batch_policy="common minimum accepted size; revalidate both after typed OOM"))
    return dict(version=1, kind="arxiv_v1_supplemental_tensor_definitions", primary_matrix_sha256=PRIMARY_SHA,
        training_seeds=[123], cases=cases, pairs=pairs, defined_training_runs=16, formal_training_runs=0,
        interpretation="Separate full rank3/4 definitions; all graphs/capacity/derivative/training/post gates remain. Not part of primary48.")


def inspect_tensor_inputs():
    root = Path(DATA_ROOT)
    if (file_sha(root / "report.json") != PREPARATION_SHA or
            file_sha("runs/supplemental-tensor-verification-1075/report.json") != VERIFICATION_SHA):
        raise ValueError("Full source conversion or independent Cartesian/group proof changed")
    result = {}
    for task, source in DATASETS.items():
        path, split = root / task / "structures.jsonl", root / task / "split.json"
        manifest = json.loads(split.read_text(encoding="utf8"))
        validate_manifest(manifest, source_sha256=source["sha256"], source_count=source["structures"])
        if manifest["counts"] != source["counts"] or canonical_digest(manifest) != source["split_manifest_sha256"]:
            raise ValueError("Complete supplemental source split changed")
        digest, count, scalars = hashlib.sha256(), 0, 0
        zero_structures = 0
        with path.open("rb") as stream:
            for raw in stream:
                digest.update(raw)
                row = json.loads(raw)
                if count >= source["structures"] or row.get("id") != manifest["records"][count]["id"]:
                    raise ValueError("Full supplemental ordered source IDs changed")
                target = row["targets"][task]
                spec = property_spec(task)
                scalars += finite_shape(target, spec.shape)
                def leaves(value):
                    if isinstance(value, list):
                        for child in value:yield from leaves(child)
                    else:yield value
                zero_structures += all(value == 0 for value in leaves(target))
                count += 1
        if count != source["structures"] or digest.hexdigest() != source["sha256"]:
            raise ValueError("Complete supplemental source bytes/count changed")
        result[task] = dict(structures=count, finite_cartesian_components=scalars, whole_zero_labels=zero_structures,
            source_sha256=digest.hexdigest(), manifest_sha256=canonical_digest(manifest), counts=copy.deepcopy(source["counts"]))
    return result


def write_tensor_definitions(primary, output):
    definitions = build_tensor_definitions(primary)
    inputs = inspect_tensor_inputs()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "configs").mkdir()
    for case in definitions["cases"]:
        (output / case["config_path"]).write_bytes(json.dumps(case["config"], indent=2, allow_nan=False).encode())
    definitions["full_input_audit"] = inputs
    (output / "definitions.json").write_bytes(json.dumps(definitions, indent=2, allow_nan=False).encode())
    return definitions
