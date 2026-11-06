"""Slurm CPU numerical parity for every900 accepted molecular training record."""

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import time

from ...execution.gates import checked_config, compatible_sources, file_sha, read_json, check_artifact_identity
from ...experiments.registry import canonical_digest, NEQUIP_ARCHITECTURE
from ...preflight import write_json
from ..contracts import PRIMARY_PATH, selected_group, checked_graph_metadata
from ..source import AUDIT_SHA, SOURCE_SHA, SPLIT_FILE_SHA
from .contracts import checked_report, checked_rows, training_records, plugin_identity


ENVIRONMENTS = dict(cgcnn="universal-official", alignn="universal-official", mace="universal-mace",
                    nequip="universal", custom_knn_gcn="universal-official")


def verified_configs(spec, graph_path, expected_sha):
    """Accept only the reviewed full graph report and its exact exported recipes."""
    graph_path = Path(graph_path)
    if file_sha(graph_path / "report.json") != expected_sha:
        raise ValueError("Reviewed complete graph-report bytes changed")
    graph = read_json(graph_path / "report.json")
    checked_graph_metadata(graph, spec)
    configs = {}
    for mode, expected in spec["configs"].items():
        config = read_json(graph_path / ("config." + mode + ".json"))
        if canonical_digest(config) != graph["final_config_sha256"][mode]:
            raise ValueError("Complete graph-scan configuration changed")
        if spec["official"]:
            checked_config(config, expected, expected["batch_size"], spec["counts"])
        elif config != expected:
            raise ValueError("Direct plugin reference must retain its original recipe")
        configs[mode] = config
    return graph, configs


def verify_molecular_parity(model_name, graph_path, graph_report_sha256, output):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Original numerical comparisons require a Slurm allocation")
    if model_name not in ENVIRONMENTS or Path(sys.prefix).name != ENVIRONMENTS[model_name]:
        raise RuntimeError("Use the registered original-provider environment")
    spec = selected_group(model_name)
    graph, configs = verified_configs(spec, graph_path, graph_report_sha256)
    commit = compatible_sources([])
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB disk reserve before molecular references")
    output = Path(output);output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = dict(version=1, kind="complete_molecular_same_state_reference", status="running", model=model_name,
        stage="source_and_training_identity", git_commit=commit, slurm_job_id=os.environ["SLURM_JOB_ID"],
        source_checkout=str(Path.cwd().resolve()), python=sys.executable, definition_sha256=spec["definition_sha256"],
        source_sha256=SOURCE_SHA, counts=spec["counts"], source_structures=100000, training_structures=900,
        partition="train", device="cpu", dtype="float32", seed=123, graph_report=str(Path(graph_path)/"report.json"),
        graph_report_sha256=graph_report_sha256, formal_training_runs=0, formal_training_ready=False,
        cuda_capacity_acceptance=False, parameter_updates=0, original_package_parity_verified=False,
        comparison_precision="float32 model/geometry/features; preserve original native-head float32/float64 values; comparison promotes without rounding",
        direct_plugin_parity_verified=False, initializations={})
    def record(**fields):
        report.update(fields);write_json(output / "report.json", report)
    record()
    try:
        import torch
        from universal_gnn.data.splits.loading import load_partition
        from universal_gnn.engine.training import build_model, dataset, version_record
        from ...native_heads.evaluation import state_digest
        from .references import OriginalReference

        torch.set_num_threads(1)
        primary = read_json(PRIMARY_PATH)
        for mode, original in configs.items():
            plugin_source_identity = None
            config = copy.deepcopy(original);config["device"] = "cpu"
            structures = dataset(config)
            indices, manifest, manifest_sha = load_partition(structures.source, config["dataset"])
            records = training_records(manifest)
            if (len(structures) != 900 or len(structures.source) != 100000 or list(structures.indices) != indices
                    or structures.source.sha256 != SOURCE_SHA or manifest_sha != config["dataset"]["split_manifest_sha256"]):
                raise ValueError("Reference comparison must retain the complete frozen source and training set")
            audit = Path(config["dataset"]["path"]).parent / "audit.json"
            inputs = {config["dataset"]["path"]: SOURCE_SHA, config["dataset"]["split_manifest"]: SPLIT_FILE_SHA,
                      str(audit): AUDIT_SHA, str(Path(graph_path)/"report.json"): graph_report_sha256}
            if any(file_sha(path) != digest for path,digest in inputs.items()):
                raise ValueError("Reference source/split/audit/graph identity changed")
            torch.manual_seed(123)
            model = build_model(config).to(device="cpu", dtype=torch.float32).eval()
            backbone = model.backbone
            if spec["official"]:
                official = backbone.load_report
                check_artifact_identity(official, graph["graph_definition"]["native_graph"],
                    primary["registry"]["artifacts"][model_name]["files"], model_name)
                expected_graph = copy.deepcopy(graph["graph_definition"]["native_graph"])
                if model_name == "nequip" and mode == "scratch":
                    expected_graph["artifact_sha256"]["blueprint"] = primary["registry"]["artifacts"][model_name]["files"][NEQUIP_ARCHITECTURE[0]]["sha256"]
                if backbone.native_graph_provenance() != expected_graph:
                    raise ValueError("Original numerical reference changed the accepted input implementation")
                coverage = 1. if mode == "pretrained" else 0.
                if (official.get("initialization") != mode or official.get("parameter_coverage") != coverage
                        or official.get("buffer_coverage") != coverage or (mode == "scratch" and not official.get("state_layout_verified"))):
                    raise ValueError("Reference must preserve whole-backbone initialization coverage/layout")
            else:
                official = None
                expected_plugin = graph["graph_definition"]["native_graph"]
                previous_checkout = Path(expected_plugin["gnn"]["path"]).parent.parent
                plugin_source_identity = plugin_identity(backbone.extension_provenance, expected_plugin,
                    current_checkout=Path.cwd().resolve(), reference_checkout=previous_checkout, reference_commit=graph["git_commit"])
            before = state_digest(model)
            reference = OriginalReference(model_name, backbone)
            reference_before = reference.state()
            native_body = backbone.model if spec["official"] else backbone.gnn
            native_reference_state = state_digest(native_body)
            if native_reference_state != reference_before:
                raise ValueError("Independent original reference changed the supplied model state")
            record(stage="all900_original_comparisons", active_initialization=mode, completed_training_structures=0)
            row_path = output / ("comparisons."+mode+".jsonl")
            mode_started = time.perf_counter()
            with row_path.open("x", encoding="utf8", newline="\n") as stream:
                for index in range(len(structures)):
                    structure = structures[index]
                    if structure.identifier != records[index]["id"]:
                        raise ValueError("Reference source-ordered training identity changed")
                    comparisons = reference.compare(structure)
                    row = dict(index=index, **records[index], comparisons=comparisons, passed=True, no_periodic_images=True)
                    stream.write(json.dumps(row, sort_keys=True, allow_nan=False)+"\n")
                    if (index+1) % 100 == 0:
                        stream.flush();record(completed_training_structures=index+1)
            with row_path.open(encoding="utf8") as stream:
                summary = checked_rows((json.loads(line) for line in stream), records, model_name)
            after, reference_after = state_digest(model), reference.state()
            if before != after or reference_before != reference_after or any(module.training for module in model.modules()):
                raise ValueError("Read-only reference comparison changed parameters/buffers/evaluation modes")
            if any(parameter.grad is not None for parameter in model.parameters()):
                raise ValueError("Reference must not accumulate parameter gradients or perform optimization")
            if any(file_sha(path) != digest for path,digest in inputs.items()):
                raise ValueError("Reference input bytes changed during complete900 numerical comparisons")
            report["initializations"][mode] = dict(summary, initialization=mode, reference=reference.reference,
                state_unchanged=True, reference_state_unchanged=True,
                model_state_before_sha256=before, model_state_after_sha256=after,
                reference_state_before_sha256=reference_before, reference_state_after_sha256=reference_after,
                native_reference_state_sha256=native_reference_state,
                rows=str(row_path), rows_sha256=file_sha(row_path), config_sha256=canonical_digest(config),
                graph_config_sha256=canonical_digest(original), input_sha256=inputs, official=official,
                plugin_source_identity=plugin_source_identity,
                wall_seconds=time.perf_counter()-mode_started)
            write_json(output/("config."+mode+".json"), config)
            record()
            del reference, model
        report.update(status="passed", stage="all_initializations_complete", versions=version_record(),
            original_package_parity_verified=spec["official"], direct_plugin_parity_verified=not spec["official"],
            wall_seconds=time.perf_counter()-started,
            interpretation="Same-state original network/direct-plugin feature and native-head comparisons for all900 training frames. No target fitting, optimizer, CUDA capacity or heldout quality acceptance; artifact loading remains bound to accepted registered providers.")
        checked_report(report, spec)
        record()
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error), wall_seconds=time.perf_counter()-started)
        raise
