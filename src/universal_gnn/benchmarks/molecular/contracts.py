"""Closed accepted molecular inputs and explicit graph-only device/coverage scope."""

import copy
from pathlib import Path
import re

from ..execution.gates import file_sha, read_json
from .definitions import build_molecular_definitions
from .source import COUNTS, SOURCE_SHA


DEFINITION_PATH = Path("runs/molecular-definition-control-1692/definitions/definitions.json")
DEFINITION_SHA = "68255484022ac5aaf3ad69ffb65eee35c5ff3dcdc8dd5001f2380b14b888ca79"
PRIMARY_PATH = Path("runs/arxiv-v1/definition-947/matrix.json")
MODELS = ("cgcnn", "alignn", "mace", "nequip", "custom_knn_gcn")


def molecular_group_spec(primary, definitions, model, *, repository="."):
    if model not in MODELS or not isinstance(definitions, dict):
        raise ValueError("Select one of the four original molecular providers or the existing directory plugin")
    expected = build_molecular_definitions(primary, definitions.get("input_audit"), repository=repository)
    actual = {k: v for k, v in definitions.items() if k != "definition_execution"}
    if actual != expected:
        raise ValueError("Require all nine original accepted molecular supplement definitions")
    cases = [copy.deepcopy(c) for c in expected["cases"] if c["model"] == model]
    official = model != "custom_knn_gcn"
    if len(cases) != (2 if official else 1):
        raise ValueError("Molecular provider group must preserve its complete initialization comparison")
    configs = {c["initialization"]: copy.deepcopy(c["config"]) for c in cases}
    if set(configs) != ({"pretrained", "scratch"} if official else {"scratch"}):
        raise ValueError("Molecular initialization group differs")
    reference_mode = "pretrained" if official else "scratch"
    return dict(model=model, official=official, cases=cases, configs=configs,
        reference_mode=reference_mode, reference_config=copy.deepcopy(configs[reference_mode]),
        counts=dict(COUNTS), source_structures=100000, definition_sha256=DEFINITION_SHA,
        primary_sha256=expected["primary_matrix_sha256"], input_audit=copy.deepcopy(expected["input_audit"]))


def selected_group(model, *, definitions=DEFINITION_PATH, primary=PRIMARY_PATH):
    if file_sha(definitions) != DEFINITION_SHA:
        raise ValueError("Accepted molecular definition file bytes changed")
    return molecular_group_spec(read_json(primary), read_json(definitions), model)


def checked_graph_metadata(report, spec, *, require_cuda=False):
    """Check metadata scope only; file/Slurm/counter provenance remains separate evidence."""
    if (not isinstance(report, dict) or type(report.get("version")) is not int or report["version"] != 1
            or report.get("kind") != "complete_molecular_native_graph_scan" or report.get("status") != "complete"
            or report.get("model") != spec["model"] or report.get("definition_sha256") != spec["definition_sha256"]
            or report.get("source_sha256") != SOURCE_SHA or report.get("counts") != COUNTS
            or type(report.get("source_structures")) is not int or report["source_structures"] != 100000
            or type(report.get("training_structures")) is not int or report["training_structures"] != 900
            or report.get("complete_source_scan") is not True or report.get("complete_training_scan") is not True
            or report.get("no_periodic_images") is not True or report.get("model_forward_executed") is not False
            or report.get("model_state_unchanged") is not True or report.get("numerical_capacity_acceptance") is not False
            or report.get("formal_training_runs") != 0 or report.get("dtype") != "float32"):
        raise ValueError("Incomplete or incompatible full molecular graph-only scope")
    device = report.get("device")
    if not isinstance(device, str) or not (device == "cpu" or re.fullmatch(r"cuda(?::[0-9]+)?", device)):
        raise ValueError("Molecular graph scan must declare its actual CPU/CUDA device")
    cuda = device.startswith("cuda")
    if report.get("cuda_input_graph_validation") is not cuda or (require_cuda and not cuda):
        raise ValueError("CPU graph evidence cannot replace required actual CUDA input validation")
    if report.get("native_edge_kind") != ("padded_neighbor_slots" if spec["model"] == "cgcnn" else "directed_edges"):
        raise ValueError("Molecular native edge computation semantics differ")
    for key in ("source_graph_rows_sha256", "training_graph_rows_sha256", "probe_sha256", "graph_definition_sha256",
                "model_state_before_sha256", "model_state_after_sha256"):
        if not isinstance(report.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", report[key]):
            raise ValueError("Molecular graph source/state/probe fingerprints are missing")
    if report["model_state_before_sha256"] != report["model_state_after_sha256"]:
        raise ValueError("Graph construction changed model parameters or persistent buffers")
    return report
