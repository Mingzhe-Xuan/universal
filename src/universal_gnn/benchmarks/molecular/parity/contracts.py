"""Metadata checks only; execution and file provenance must be verified separately."""

import math
import re

from ..source import COUNTS, SOURCE_SHA


def expected_comparisons(model):
    if model in {"cgcnn", "alignn"}:
        return {"node_features", "native_head"}
    if model in {"mace", "nequip"}:
        return {"node_features", "native_energy", "native_forces"}
    if model == "custom_knn_gcn":
        return {"node_features"}
    raise ValueError("Unsupported molecular reference provider")


def training_records(manifest):
    """Retain the complete source-ordered900 train IDs; never select test examples."""
    indices = manifest.get("partitions", {}).get("train")
    records = manifest.get("records", [])
    if (manifest.get("counts") != COUNTS or len(records) != 100000 or not isinstance(indices, list)
            or len(indices) != 900 or any(type(i) is not int or not 0 <= i < len(records) for i in indices)
            or indices != sorted(set(indices))):
        raise ValueError("Require the full accepted100000 source and900 training partition")
    if any(not isinstance(records[i], dict) or not isinstance(records[i].get("id"), str) or not records[i]["id"] for i in indices):
        raise ValueError("Training reference metadata lack source identifiers")
    selected = [{"id": records[i]["id"], "source_index": i} for i in indices]
    if len({r["id"] for r in selected}) != 900 or any(not isinstance(r["id"], str) or not r["id"] for r in selected):
        raise ValueError("Training reference IDs must be unique and ordered")
    return selected


def checked_rows(rows, records, model):
    expected = expected_comparisons(model)
    if len(records) != 900:
        raise ValueError("Reference rows must cover all900 training records")
    maxima = {key: 0. for key in expected}
    count = 0
    for row in rows:
        if (count >= len(records) or not isinstance(row, dict) or type(row.get("index")) is not int
                or type(row.get("source_index")) is not int or row.get("index") != count
                or row.get("id") != records[count]["id"] or row.get("source_index") != records[count]["source_index"]
                or row.get("passed") is not True or row.get("no_periodic_images") is not True
                or set(row.get("comparisons", {})) != expected):
            raise ValueError("Reference row identity/order/complete comparison scope differs")
        for name, item in row["comparisons"].items():
            error = item.get("max_absolute_error")
            shape = item.get("shape")
            if (not isinstance(error, (int, float)) or isinstance(error, bool) or not math.isfinite(error) or error < 0
                    or not isinstance(shape, list) or not shape or any(type(v) is not int or v <= 0 for v in shape)
                    or item.get("rtol") != (2e-5 if model == "mace" else 3e-5)
                    or item.get("atol") != (2e-6 if model == "mace" else 3e-6)
                    or any(not isinstance(item.get(k), str) or not re.fullmatch(r"[0-9a-f]{64}", item[k])
                           for k in ["actual_sha256", "reference_sha256"])):
                raise ValueError("Reference row lacks finite same-tolerance numerical evidence")
            maxima[name] = max(maxima[name], error)
        count += 1
    if count != len(records):
        raise ValueError("Incomplete900-row original-model comparison")
    return dict(structures=count, maximum_absolute_errors=maxima)


def checked_report(report, spec):
    modes = {"pretrained", "scratch"} if spec["official"] else {"scratch"}
    if (type(report.get("version")) is not int or report.get("version") != 1 or report.get("kind") != "complete_molecular_same_state_reference"
            or report.get("status") != "passed" or report.get("stage") != "all_initializations_complete" or report.get("model") != spec["model"]
            or report.get("definition_sha256") != spec["definition_sha256"] or report.get("source_sha256") != SOURCE_SHA
            or report.get("counts") != COUNTS or report.get("source_structures") != 100000
            or report.get("training_structures") != 900 or report.get("partition") != "train"
            or report.get("device") != "cpu" or report.get("dtype") != "float32" or report.get("seed") != 123
            or type(report.get("formal_training_runs")) is not int or report.get("formal_training_runs") != 0 or report.get("formal_training_ready") is not False
            or report.get("cuda_capacity_acceptance") is not False or type(report.get("parameter_updates")) is not int or report.get("parameter_updates") != 0
            or report.get("original_package_parity_verified") is not spec["official"]
            or report.get("direct_plugin_parity_verified") is not (not spec["official"])
            or set(report.get("initializations", {})) != modes):
        raise ValueError("Incomplete or overstated molecular reference scope")
    for mode, row in report["initializations"].items():
        if (row.get("initialization") != mode or row.get("structures") != 900 or row.get("state_unchanged") is not True
                or row.get("reference_state_unchanged") is not True
                or row.get("model_state_before_sha256") != row.get("model_state_after_sha256")
                or row.get("reference_state_before_sha256") != row.get("reference_state_after_sha256")
                or row.get("native_reference_state_sha256") != row.get("reference_state_before_sha256")
                or set(row.get("maximum_absolute_errors", {})) != expected_comparisons(spec["model"])):
            raise ValueError("Both complete same-state initialization comparisons are required")
        for key in ["model_state_before_sha256", "model_state_after_sha256", "reference_state_before_sha256",
                    "reference_state_after_sha256", "native_reference_state_sha256", "rows_sha256", "config_sha256"]:
            if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise ValueError("Reference state/config/row fingerprints are missing")
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0
               for v in row["maximum_absolute_errors"].values()):
            raise ValueError("Reference errors must be finite nonnegative values")
        if spec["official"]:
            official = row.get("official", {})
            coverage = 1. if mode == "pretrained" else 0.
            if (not isinstance(official, dict) or official.get("initialization") != mode
                    or official.get("parameter_coverage") != coverage or official.get("buffer_coverage") != coverage
                    or (mode == "scratch" and official.get("state_layout_verified") is not True)):
                raise ValueError("Original reference initialization coverage/layout differs")
        elif row.get("official") is not None:
            raise ValueError("Directory plugin cannot claim an official checkpoint")
    return report
