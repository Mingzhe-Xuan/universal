"""Slurm-only file verification; no model execution or job submission."""

import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from ...execution.gates import (checked_config, compatible_sources,
    read_json, file_sha, check_artifact_identity)
from ...experiments.registry import canonical_digest
from ...pairing.evidence import verify_capacity_evidence
from ...prediction_assessment.runtime import verify_physics
from ...preflight import write_json
from ...preparation.specification import physical_indices
from ...probes.selection import METRICS, select_probe
from ..capacity import single_worker_evidence, validate_workers
from ..contracts import selected_group, checked_graph_metadata, PRIMARY_PATH, DEFINITION_PATH
from ..parity.contracts import checked_report, checked_rows, training_records, plugin_identity
from ..parity.runtime import ENVIRONMENTS, verified_configs
from ..source import AUDIT_SHA, SOURCE_SHA, SPLIT_FILE_SHA
from .contracts import checked_capacity, checked_capacity_summary, checked_probe
from .evidence import Evidence, successful_parent


def graph_rows(evidence, directory, graph, manifest, records):
    source = evidence.bind(directory / "source-graph-sizes.jsonl", graph["source_graph_rows_sha256"])
    training = evidence.bind(directory / "training-graph-sizes.jsonl", graph["training_graph_rows_sha256"])
    selected = set(manifest["partitions"]["train"])
    sums, maxima = {k: 0 for k in METRICS}, {k: 0 for k in METRICS}
    count, source_count = 0, 0
    with source.open(encoding="utf8") as full, training.open(encoding="utf8") as train:
        for i, line in enumerate(full):
            source_count += 1
            row = json.loads(line)
            if (i >= 100000 or row.get("index") != i or row.get("source_index") != i
                    or row.get("id") != manifest["records"][i]["id"]
                    or any(type(row.get(k)) is not int or row[k] < (1 if k == "atoms" else 0) for k in METRICS)):
                raise ValueError("Complete CUDA source-graph stream differs from the accepted source")
            for key in METRICS:
                sums[key] += row[key]
                maxima[key] = max(maxima[key], row[key])
            if i in selected:
                expected = dict(row, index=count)
                if json.loads(next(train, "null")) != expected:
                    raise ValueError("CUDA training graph rows are not the exact900 source rows")
                count += 1
        if source_count != 100000 or count != 900 or next(train, None) is not None:
            raise ValueError("Incomplete100000 source/900 training CUDA graph stream")
    if graph.get("source_sums") != sums or graph.get("source_maxima") != maxima:
        raise ValueError("Complete CUDA graph aggregate counts differ")
    probe = evidence.read(directory / "probe.json")
    with training.open(encoding="utf8") as stream:
        binding = probe["coverage"]["binding"]
        expected_binding = dict(source_sha256=SOURCE_SHA,
            split_manifest_sha256=canonical_digest(manifest), graph_definition_sha256=graph["graph_definition_sha256"],
            dtype="float32", native_edge_kind=graph["native_edge_kind"])
        if binding != expected_binding:
            raise ValueError("CUDA probe source/graph/split binding differs")
        rebuilt = select_probe((json.loads(line) for line in stream), records, binding)
    checked_probe(probe, rebuilt, graph)
    return probe


def _same_source(commits, paths):
    for commit in set(commits):
        if subprocess.check_output(["git", "diff", "--name-only", commit, "HEAD", "--", *paths], text=True).strip():
            raise ValueError("Molecular implementation changed after the retained evidence")


def check_molecular_readiness(model, capacity, capacity_terminal, parity, parity_terminal, output):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Joint molecular evidence checks require CPU Slurm")
    if model not in ENVIRONMENTS or Path(sys.prefix).name != ENVIRONMENTS[model]:
        raise RuntimeError("Use the registered original-provider environment")
    output = Evidence().path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version=1, kind="joint_molecular_preparation_evidence", status="running", model=model,
        slurm_job_id=os.environ["SLURM_JOB_ID"], formal_training_runs=0, formal_training_ready=False,
        preparation_gate_passed=False)
    write_json(output / "report.json", report)
    evidence = Evidence()
    try:
        spec = selected_group(model)
        evidence.bind(DEFINITION_PATH, spec["definition_sha256"])
        evidence.bind(PRIMARY_PATH)
        capacity, parity = evidence.path(capacity), evidence.path(parity)
        prepared = evidence.read(capacity / "report.json")
        graph_path = capacity / "graph-scan"
        graph = evidence.read(graph_path / "report.json", prepared.get("graph_report_sha256"))
        checked_graph_metadata(graph, spec, require_cuda=True)
        common = checked_capacity(prepared, graph, spec)
        cap_entry = successful_parent(evidence, capacity_terminal, capacity / "report.json")
        parity_parent_path = Path(parity_terminal).parent / "report.json"
        parity_entry = successful_parent(evidence, parity_terminal, parity_parent_path)
        if "--gres=gpu:1" not in cap_entry["sbatch_argv"] or any(
                token.startswith("--gres") for token in parity_entry["sbatch_argv"]):
            raise ValueError("Require the original GPU capacity and separate CPU comparison allocations")
        reference = evidence.read(parity / "report.json")
        checked_report(reference, spec)
        parent = evidence.read(parity_parent_path)
        if (parent.get("status") != "passed" or parent.get("parity_report_sha256") != file_sha(parity / "report.json")
                or reference["slurm_job_id"] != parity_entry["job"] or reference["git_commit"] != parity_entry["git_commit"]):
            raise ValueError("Original comparison is not bound to the retained successful CPU parent")
        commit = compatible_sources([prepared["git_commit"], reference["git_commit"]])
        molecular = "src/universal_gnn/benchmarks/molecular/"
        _same_source([prepared["git_commit"]], [molecular + name for name in
            ["capacity.py", "worker.py", "mixed.py", "schedule.py", "graphs.py", "contracts.py", "definitions.py", "source.py"]])
        _same_source([reference["git_commit"]], [molecular + "parity", molecular + "contracts.py", molecular + "source.py"])
        cpu_graph_path = Path(reference["graph_report"]).parent
        evidence.bind(cpu_graph_path / "report.json", reference["graph_report_sha256"])
        for mode in spec["configs"]:
            evidence.bind(cpu_graph_path / ("config." + mode + ".json"))
        cpu_graph, cpu_configs = verified_configs(spec, cpu_graph_path, reference["graph_report_sha256"])
        configs = {}
        for mode, expected in spec["configs"].items():
            original = evidence.read(graph_path / ("config." + mode + ".json"))
            if canonical_digest(original) != graph["final_config_sha256"][mode]:
                raise ValueError("CUDA graph configuration bytes changed")
            if spec["official"]:
                checked_config(original, expected, expected["batch_size"], spec["counts"])
            elif original != expected:
                raise ValueError("Plugin CUDA graph recipe differs")
            config = evidence.read(capacity / ("config." + mode + ".resolved.json"))
            if dict(config, batch_size=expected["batch_size"]) != original or config["batch_size"] != common:
                raise ValueError("Resolved molecular recipe changed beyond the common batch")
            configs[mode] = config
        dataset = spec["reference_config"]["dataset"]
        if file_sha(dataset["path"]) != SOURCE_SHA or file_sha(dataset["split_manifest"]) != SPLIT_FILE_SHA:
            raise ValueError("Accepted complete molecular source/split bytes changed")
        audit = Path(dataset["path"]).parent / "audit.json"
        if file_sha(audit) != AUDIT_SHA:
            raise ValueError("Accepted molecular conversion audit changed")
        manifest = read_json(dataset["split_manifest"])
        records = training_records(manifest)
        probe = graph_rows(evidence, graph_path, graph, manifest, records)
        if canonical_digest(graph["graph_definition"]) != graph["graph_definition_sha256"]:
            raise ValueError("Actual CUDA graph implementation fingerprint differs")
        for path in (capacity / "capacity").rglob("*"):
            if path.is_file() and path.suffix in {".json", ".jsonl"}:
                evidence.bind(path)
        if spec["official"]:
            if graph["graph_definition"]["native_graph"] != cpu_graph["graph_definition"]["native_graph"]:
                raise ValueError("CPU reference and CUDA capacity use different original inputs")
            workers = verify_capacity_evidence(capacity / "capacity", probe)
        else:
            plugin_identity(graph["graph_definition"]["native_graph"], cpu_graph["graph_definition"]["native_graph"],
                current_checkout=prepared["source_checkout"],
                reference_checkout=Path(cpu_graph["graph_definition"]["native_graph"]["gnn"]["path"]).parent.parent,
                reference_commit=cpu_graph["git_commit"])
            workers = single_worker_evidence(capacity / "capacity", probe)
        validate_workers(workers, probe)
        checked_capacity_summary(prepared, workers)
        physical_ids = [records[i]["id"] for i in physical_indices(probe, 900)]
        observed_versions = [graph["graph_definition"]["versions"], reference["versions"]]
        for worker in workers["successful_workers"]:
            observed_versions.append(worker["versions"])
            if spec["official"]:
                official = worker["execution"]["official"]
                mode = official["initialization"]
                coverage = 1. if mode == "pretrained" else 0.
                if (official.get("parameter_coverage") != coverage or official.get("buffer_coverage") != coverage
                        or (mode == "scratch" and official.get("state_layout_verified") is not True)):
                    raise ValueError("Actual CUDA worker original parameter/buffer coverage differs")
                check_artifact_identity(official, graph["graph_definition"]["native_graph"],
                    read_json(PRIMARY_PATH)["registry"]["artifacts"][model]["files"], model)
        names = set(reference["versions"])
        versions = {}
        for name in names:
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                versions[name] = None
        for value in observed_versions:
            if set(value) != names or value != versions:
                raise ValueError("Original comparison and CUDA preparation package versions differ")
        for mode in configs:
            physics = evidence.read(capacity / ("physics." + mode + ".json"))
            verify_physics(physics, "forcefield", dict(ids=physical_ids), device=graph["device"])
            if set(physics.get("mixed_parameter_gradient_norms", {})) != {"backbone", "readout"}:
                raise ValueError("Both model components require original mixed gradients")
            row = reference["initializations"][mode]
            config = evidence.read(parity / ("config." + mode + ".json"))
            if canonical_digest(config) != row["config_sha256"] or config != dict(cpu_configs[mode], device="cpu"):
                raise ValueError("Original900-frame comparison configuration changed")
            evidence.bind(cpu_graph_path / ("config." + mode + ".json"))
            if row.get("graph_config_sha256") != canonical_digest(cpu_configs[mode]):
                raise ValueError("Original comparison does not bind its complete CPU graph recipe")
            path = evidence.bind(row["rows"], row["rows_sha256"])
            if path.resolve() != (parity / ("comparisons." + mode + ".jsonl")).resolve():
                raise ValueError("Original comparison rows escaped the selected initialization")
            with path.open(encoding="utf8") as stream:
                checked = checked_rows((json.loads(line) for line in stream), records, model)
            if checked["maximum_absolute_errors"] != row["maximum_absolute_errors"]:
                raise ValueError("Original comparison aggregate errors differ")
        evidence.unchanged()
        source_inputs = {dataset["path"]: SOURCE_SHA, dataset["split_manifest"]: SPLIT_FILE_SHA, str(audit): AUDIT_SHA}
        if any(file_sha(path) != digest for path, digest in source_inputs.items()):
            raise ValueError("Molecular source/split/audit changed during joint preparation checks")
        for mode, config in configs.items():
            write_json(output / ("config." + mode + ".resolved.json"), config)
        report.update(status="passed", preparation_gate_passed=True, git_commit=commit,
            source_checkout=str(Path.cwd().resolve()), counts=spec["counts"], definition_sha256=spec["definition_sha256"],
            common_batch_size=common, initializations=list(configs), capacity_parent=cap_entry, parity_parent=parity_entry,
            input_sha256=dict(evidence.sha256, **source_inputs),
            versions=versions, interpretation="Complete CUDA preparation plus900-frame original-network CPU reference only; formal budget/launch/fitting/heldout quality remain separate.")
        write_json(output / "report.json", report)
        return report
    except Exception as error:
        report.update(status="failed", error_type=type(error).__name__, error=str(error))
        write_json(output / "report.json", report)
        raise
