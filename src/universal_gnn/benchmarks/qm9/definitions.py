"""Independent 32-case extension; the original primary matrix is immutable."""

import copy
import hashlib
import json
from pathlib import Path

from universal_gnn.data.preparation.qm9.conversion import write_json
from universal_gnn.data.preparation.qm9.source import CLEAN_COUNT, UNITS, digest

MODELS = ("cgcnn", "alignn", "mace", "nequip")
MODES = ("pretrained", "scratch")
PROPERTIES = tuple(UNITS)


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def build_definitions(primary, data_report):
    if data_report.get("status") != "passed" or data_report.get("clean_count") != CLEAN_COUNT:
        raise ValueError("Require the complete cleaned QM9 source")
    if data_report.get("units") != UNITS:
        raise ValueError("QM9 target units differ")
    cases = []
    for name in PROPERTIES:
        for model in MODELS:
            for mode in MODES:
                matches = [c for c in primary["cases"] if c["task"] == "bandgap" and
                           c["model"] == model and c["initialization"] == mode and c["seed"] == 123]
                if len(matches) != 1:
                    raise ValueError("Require one original seed123 official scalar recipe")
                template = matches[0]
                config = copy.deepcopy(template["config"])
                config["task"] = dict(kind="supervised", property=name)
                config["dataset"] = dict(copy.deepcopy(data_report["dataset"]), partition="train")
                if model in {"cgcnn", "alignn"}:
                    config["backbone"].update(input_profile="molecular_radius", input_cutoff=6.)
                config["prediction"]["head_mode"] = "reset"
                config["prediction"]["readout"]["pooling"] = "mean"
                identifier = f"qm9--seed-123--{name}--{model}--{mode}"
                cases.append(dict(id=identifier, model=model, property=name, initialization=mode,
                                  python_environment=template["python_environment"], config=config,
                                  config_sha256=canonical(config),
                                  run_directory="runs/qm9-v1/cases/" + identifier))
    return dict(version=1, kind="qm9_four_scalar_matrix", cases=cases, training_seeds=[123],
                defined_training_runs=32, primary_matrix_sha256=canonical(primary),
                data_report=copy.deepcopy(data_report),
                interpretation="Separate QM9 extension; four direct graph scalars, same complete source/split, no new DFT")


def define(primary_path, data_directory, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    data = json.loads((Path(data_directory) / "report.json").read_bytes())
    if digest(data["dataset"]["path"]) != data["dataset"]["sha256"]:
        raise ValueError("QM9 source changed before definition")
    primary = json.loads(Path(primary_path).read_bytes())
    if canonical(primary) != "b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651":
        raise ValueError("Require original immutable947 primary recipes")
    definitions = build_definitions(primary, data)
    write_json(output / "definitions.json", definitions)
    for case in definitions["cases"]:
        write_json(output / (case["id"] + ".json"), case["config"])
    return definitions


def load_case(definitions, identifier):
    matrix = json.loads((Path(definitions) / "definitions.json").read_bytes())
    matches = [case for case in matrix["cases"] if case["id"] == identifier]
    if len(matches) != 1:
        raise ValueError("Unknown or duplicate QM9 case")
    case = matches[0]
    if canonical(case["config"]) != case["config_sha256"]:
        raise ValueError("QM9 requested configuration changed")
    return case
