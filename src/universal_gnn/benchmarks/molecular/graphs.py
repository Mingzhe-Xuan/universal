"""Complete original nonperiodic inputs; graph-only scans never evaluate a GNN."""

import copy
import gzip
import json
import os
from pathlib import Path
import shutil
import time
from types import SimpleNamespace

from ..execution.gates import compatible_sources, file_sha
from ..experiments.registry import canonical_digest
from ..preflight import write_json
from ..probes.native_scan import auxiliary_modules, count_graphs, edge_statistics, forbid_model_forward, implementation_sources
from ..probes.selection import METRICS, select_probe
from .contracts import checked_graph_metadata, selected_group
from .source import AUDIT_SHA, SOURCE_SHA, SPLIT_FILE_SHA


def write_graph_rows(source, records, training_indices, counter, source_path, training_path):
    """Stream all source records and their source-ordered training subset; keep failed prefixes."""
    if (len(source) != len(records) or not isinstance(training_indices, list) or not training_indices
            or any(type(i) is not int or not 0 <= i < len(source) for i in training_indices)
            or training_indices != sorted(set(training_indices))):
        raise ValueError("Molecular complete source/training indices differ")
    training = set(training_indices)
    maxima = {k: 0 for k in METRICS}
    sums = {k: 0 for k in METRICS}
    train_count = count = 0
    with Path(source_path).open("x", encoding="utf8", newline="\n") as all_stream, \
            Path(training_path).open("x", encoding="utf8", newline="\n") as train_stream:
        for index in range(len(source)):
            structure = source[index]
            if structure.identifier != records[index]["id"]:
                raise ValueError("Molecular source identity changed during native graph scan")
            values = counter(structure)
            if (not isinstance(values, dict) or any(type(values.get(k)) is not int or values[k] < (1 if k == "atoms" else 0) for k in METRICS)
                    or type(values.get("valid_directed_edges")) is not int
                    or not 0 <= values["valid_directed_edges"] <= values["native_edges"]
                    or values["maximum_degree"] > values["native_edges"] + values["auxiliary_edges"]
                    or (values["native_edges"] + values["auxiliary_edges"] > 0 and values["maximum_degree"] == 0)
                    or (values["native_edges"] == 0 and values["native_triplets"] != 0)):
                raise ValueError("Molecular native graph counts or valid/padded edge semantics differ")
            row = dict(values, index=index, id=structure.identifier, source_index=index)
            all_stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            for key in METRICS:
                sums[key] += values[key]
                maxima[key] = max(maxima[key], values[key])
            if index in training:
                row["index"] = train_count
                train_stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                train_count += 1
            count += 1
            if count % 100 == 0:
                all_stream.flush()
                train_stream.flush()
    if count != len(records) or train_count != len(training_indices):
        raise ValueError("Molecular source/training graph stream is incomplete")
    return dict(source_structures=count, training_structures=train_count, source_sums=sums, source_maxima=maxima)


def _count_original(model_name, backbone, auxiliary, batch):
    import torch

    if len(batch.numbers) != 9 or batch.num_graphs != 1 or bool(batch.pbc.any()):
        raise ValueError("Molecular native scan cannot introduce periodic structures")
    if model_name == "custom_knn_gcn":
        builder = backbone.graph_builder
        if any(True for _ in builder.parameters()):
            raise ValueError("This frozen molecular plugin graph builder must not contain learned parameters")
        graph = builder.forward(batch)
        if graph.geometry is not batch:
            raise ValueError("Plugin graph builder changed the supplied molecular geometry")
        graph.validate()
        if bool(graph.cell_shifts.any()):
            raise ValueError("Nonperiodic plugin graph introduced periodic images")
        edges, degree = edge_statistics(len(batch.numbers), graph.src.cpu().tolist(), graph.dst.cpu().tolist())
        if bool((graph.src == graph.dst).any()):
            raise ValueError("The registered KNN plugin inserts self updates inside its GNN, not in the physical graph")
        return dict(atoms=len(batch.numbers), native_edges=edges, native_triplets=0, auxiliary_edges=0,
                    maximum_degree=degree, valid_directed_edges=edges, internal_self_messages_per_layer=len(batch.numbers))
    native = backbone.native_input(batch)
    snapshot = SimpleNamespace(native_input=lambda _: native)
    values = count_graphs(model_name, snapshot, auxiliary, batch)
    valid = values["native_edges"]
    if model_name == "cgcnn":
        if (getattr(backbone, "input_profile", {}).get("name") != "molecular_radius"
                or not hasattr(native, "valid_mask") or native.valid_mask.dtype != torch.bool
                or native.valid_mask.shape != native[2].shape):
            raise ValueError("CGCNN molecular input must expose actual valid neighbors separately from padding")
        valid = int(native.valid_mask.sum())
        src = torch.arange(len(batch.numbers), device=native[2].device)[:, None].expand_as(native[2])
        if bool((src[native.valid_mask] == native[2][native.valid_mask]).any()):
            raise ValueError("Molecular CGCNN input introduced a physical self edge")
    elif model_name == "alignn":
        if bool(native[0].edata["images"].any()):
            raise ValueError("Molecular ALIGNN input introduced periodic images")
    else:
        for key in ("shifts", "unit_shifts", "edge_cell_shift"):
            if key in native and bool(native[key].any()):
                raise ValueError("Original molecular provider introduced periodic images")
    values["valid_directed_edges"] = valid
    return values


def _compress(path):
    target = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as original, target.open("xb") as encoded:
        with gzip.GzipFile(filename="", mode="wb", fileobj=encoded, mtime=0) as compressed:
            shutil.copyfileobj(original, compressed, length=1024**2)
    return dict(path=str(target), sha256=file_sha(target), raw_path=str(path), raw_sha256=file_sha(path), raw_bytes=path.stat().st_size)


def scan_molecular_graphs(model_name, output, *, device="cpu", definitions=None, primary=None):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("All original graph construction and full molecular scans require Slurm")
    options = {k: v for k, v in dict(definitions=definitions, primary=primary).items() if v is not None}
    spec = selected_group(model_name, **options)
    if device != "cpu" and not str(device).startswith("cuda"):
        raise ValueError("Molecular graph scans support explicit CPU or CUDA devices")
    if shutil.disk_usage(Path.cwd()).free < 20 * 1024**3:
        raise RuntimeError("Keep20GiB free disk reserve before complete graph construction")
    output = Path(output);output.mkdir(parents=True, exist_ok=False)
    commit = compatible_sources([])
    started = time.perf_counter()
    report = dict(version=1, kind="complete_molecular_native_graph_scan", status="running", model=model_name,
        git_commit=commit, slurm_job_id=os.environ["SLURM_JOB_ID"], definition_sha256=spec["definition_sha256"],
        source_sha256=SOURCE_SHA, counts=spec["counts"], dtype="float32", model_forward_executed=False,
        numerical_capacity_acceptance=False, formal_training_runs=0)
    def record(**fields):
        report.update(fields)
        write_json(output / "report.json", report)
    record(stage="full_source_identity")
    try:
        import torch
        from universal_gnn.contracts import StructureBatch
        from universal_gnn.data.splits.loading import load_partition
        from universal_gnn.engine.initialization.neighbors import prepare_native_neighbors
        from universal_gnn.engine.training import build_model, dataset, version_record
        from ..native_heads.evaluation import state_digest

        torch.set_num_threads(1)
        actual_device = torch.device(device)
        if actual_device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("An actual CUDA allocation is required for CUDA graph evidence")
        reference = copy.deepcopy(spec["reference_config"])
        reference["device"] = str(actual_device)
        structures = dataset(reference)
        source = structures.source
        indices, manifest, manifest_sha = load_partition(source, reference["dataset"])
        if (len(source) != 100000 or len(structures) != 900 or list(structures.indices) != indices
                or indices != sorted(indices) or manifest["counts"] != spec["counts"] or source.sha256 != SOURCE_SHA):
            raise ValueError("Molecular complete source/training partition differs")
        if file_sha(Path(reference["dataset"]["split_manifest"])) != SPLIT_FILE_SHA:
            raise ValueError("Molecular raw split-file bytes changed")
        audit_path = Path(reference["dataset"]["path"]).parent / "audit.json"
        if file_sha(audit_path) != AUDIT_SHA:
            raise ValueError("Molecular accepted conversion audit changed")
        torch.manual_seed(123)
        model = build_model(reference).to(device=actual_device, dtype=torch.float32).eval()
        actual_device = next(model.parameters()).device
        before = state_digest(model)
        backbone = model.backbone
        auxiliary = auxiliary_modules(model)
        if not spec["official"] and auxiliary:
            raise ValueError("Registered scalar KNN+GCN forcefield must not invent auxiliary graph paths")
        definition = dict(provider=model_name, device=str(actual_device), dtype="float32", cutoff=backbone.cutoff,
            reference_mode=spec["reference_mode"], reference_config_sha256=canonical_digest(reference),
            native_graph=backbone.native_graph_provenance() if spec["official"] else copy.deepcopy(backbone.extension_provenance),
            auxiliary=[dict(path=name, cutoff=module.cutoff, class_name=type(module).__name__) for name, module in auxiliary],
            sources=implementation_sources(backbone), versions=version_record())
        record(stage="complete100000_original_inputs", device=str(actual_device), graph_definition=definition)
        def counter(structure):
            batch = StructureBatch.from_structures([structure]).to(actual_device, torch.float32)
            return _count_original(model_name, backbone, auxiliary, batch)
        with forbid_model_forward(model), torch.no_grad():
            observed = write_graph_rows(source, manifest["records"], indices, counter,
                output / "source-graph-sizes.jsonl", output / "training-graph-sizes.jsonl")
        if actual_device.type == "cuda":
            torch.cuda.synchronize(actual_device)
        if (file_sha(source.path) != SOURCE_SHA or file_sha(reference["dataset"]["split_manifest"]) != SPLIT_FILE_SHA
                or file_sha(audit_path) != AUDIT_SHA):
            raise ValueError("Molecular source/split/audit changed during complete native graph construction")
        binding = dict(source_sha256=SOURCE_SHA, split_manifest_sha256=manifest_sha,
            graph_definition_sha256=canonical_digest(definition), dtype="float32",
            native_edge_kind="padded_neighbor_slots" if model_name == "cgcnn" else "directed_edges")
        records = [dict(id=manifest["records"][i]["id"], source_index=i) for i in indices]
        with (output / "training-graph-sizes.jsonl").open(encoding="utf8") as stream:
            probe = select_probe((json.loads(line) for line in stream), records, binding)
        probe["coverage"].update(verified_full_training_scan=True, complete_source_graphs=100000,
            kind="complete_molecular_source_and_training_native_graphs", geometry_scope="all_source_and_source_ordered_train",
            device=str(actual_device), verified_full_cuda_training_scan=actual_device.type == "cuda",
            model_forward_executed=False, graph_definition=definition, scan_slurm_job_id=os.environ["SLURM_JOB_ID"])
        resolved = copy.deepcopy(spec["configs"])
        record(stage="training_only_native_statistics")
        if model_name in {"mace", "nequip"}:
            resolved["scratch"] = prepare_native_neighbors(resolved["scratch"], structures)
            stats = resolved["scratch"]["backbone"]["neighbor_statistics"]
            if (stats["structures"] != 900 or stats["declared_training_structures"] != 900 or stats["partition"] != "train"
                    or stats["atomic_nodes"] != 8100 or stats["source_sha256"] != SOURCE_SHA
                    or stats["manifest_sha256"] != manifest_sha):
                raise ValueError("Molecular native calibration may use only900training structures")
            write_json(output / "native-neighbor-statistics.json", stats)
        after = state_digest(model)
        if before != after or any(module.training for module in model.modules()):
            raise ValueError("Native graph construction changed model state or eval modes")
        for mode, config in resolved.items():
            write_json(output / ("config." + mode + ".json"), config)
        write_json(output / "probe.json", probe)
        compressed = {name: _compress(output / name) for name in ("source-graph-sizes.jsonl", "training-graph-sizes.jsonl")}
        record(status="complete", stage="graph_only_complete", **observed,
            complete_source_scan=True, complete_training_scan=True, no_periodic_images=True,
            cuda_input_graph_validation=actual_device.type == "cuda", native_edge_kind=binding["native_edge_kind"],
            model_state_unchanged=True, model_state_before_sha256=before, model_state_after_sha256=after,
            source_graph_rows_sha256=file_sha(output / "source-graph-sizes.jsonl"),
            training_graph_rows_sha256=file_sha(output / "training-graph-sizes.jsonl"), probe_sha256=canonical_digest(probe),
            graph_definition_sha256=canonical_digest(definition), compressed_graph_rows=compressed,
            final_config_sha256={mode: canonical_digest(c) for mode, c in resolved.items()},
            wall_seconds=time.perf_counter() - started,
            interpretation="Full source/training native inputs and900training-only statistics, no GNN forward. CPU is preparatory only; CUDA input graphs still do not prove100batch capacity/physics/training/quality.")
        checked_graph_metadata(report, spec)
        return report
    except Exception as error:
        (output / "probe.json").unlink(missing_ok=True)
        record(status="failed", error_type=type(error).__name__, error=str(error), wall_seconds=time.perf_counter() - started)
        raise
