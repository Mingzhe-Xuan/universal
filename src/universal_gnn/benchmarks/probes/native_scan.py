"""Construct every original training graph under Slurm without evaluating the GNN."""

from contextlib import contextmanager
import copy
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

from .selection import select_probe


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def reference_config(config):
    """Use the identical original graph, independently of weight initialization."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Complete graph construction must run through Slurm")
    if (config.get("structures") != "all" or config.get("max_atoms") is not None or
            config.get("graph") is not None):
        raise ValueError("Graph scanning requires all structures with no graph or atom-count override")
    data, backbone = config.get("dataset", {}), config.get("backbone", {})
    if data.get("partition") != "train" or not data.get("split_manifest"):
        raise ValueError("Graph scanning requires the explicit training split manifest")
    if (backbone.get("name") not in {"cgcnn", "alignn", "mace", "nequip"} or
            backbone.get("implementation", "official") != "official"):
        raise ValueError("Graph scanning currently supports the four original official providers")
    if config.get("prediction", {}).get("head_mode", "reset") != "reset":
        raise ValueError("This scanner describes the reset-head experiment task paths")
    if config.get("dtype", "float32") not in {"float32", "float64"}:
        raise ValueError("Graph scanning requires explicit supported floating precision")
    if not str(config.get("device", "")).startswith("cuda"):
        raise ValueError("Graph scanning must use the experiment CUDA device")
    mode = backbone.get("initialization", "pretrained")
    if mode not in {"pretrained", "scratch"}:
        raise ValueError("Unknown original initialization mode")
    result = copy.deepcopy(config)
    result["backbone"].pop("initialization", None)
    result["backbone"].pop("neighbor_statistics", None)
    if backbone["name"] == "nequip":
        result["backbone"].pop("architecture", None)
    return result


def edge_statistics(nodes, src, dst):
    """Count directed edges and both endpoint degrees, including periodic self images."""
    if type(nodes) is not int or nodes < 1 or len(src) != len(dst):
        raise ValueError("Invalid graph dimensions")
    outgoing, incoming = [0] * nodes, [0] * nodes
    for first, second in zip(src, dst):
        if type(first) is not int or type(second) is not int or not 0 <= first < nodes or not 0 <= second < nodes:
            raise ValueError("Native graph endpoint is outside its structure")
        outgoing[first] += 1
        incoming[second] += 1
    return len(src), max(max(outgoing), max(incoming))


def auxiliary_modules(model):
    from universal_gnn.adapters.features import EquivariantAdapter
    from universal_gnn.tasks.generation import DirectionReadout

    return [(name, module) for name, module in model.named_modules()
            if isinstance(module, EquivariantAdapter) or
            (isinstance(module, DirectionReadout) and not module.native_polar)]


@contextmanager
def forbid_model_forward(model):
    """Global hooks cover scripted children without installing unsupported local hooks."""
    from torch.nn.modules.module import register_module_forward_pre_hook

    forbidden = {id(module) for module in model.modules()}

    def reject(module, inputs):
        if id(module) in forbidden:
            raise RuntimeError("Graph scanning must not execute model forward")

    handle = register_module_forward_pre_hook(reject)
    try:
        yield
    finally:
        handle.remove()


def count_graphs(provider, backbone, auxiliary, batch):
    from universal_gnn.data.geometry import radius_graph

    nodes = len(batch.numbers)
    native = backbone.native_input(batch)
    triplets = 0
    if provider == "cgcnn":
        atoms, features, neighbors, mappings = native
        if (atoms.shape[0] != nodes or len(neighbors.shape) != 2 or neighbors.shape[0] != nodes or
                features.shape[:2] != neighbors.shape or len(mappings) != 1):
            raise ValueError("Original CGCNN returned incompatible padded graph dimensions")
        width = int(neighbors.shape[1])
        flat = neighbors.detach().cpu().flatten().tolist()
        edges, _ = edge_statistics(nodes, [i for i in range(nodes) for _ in range(width)], flat)
        degree = width
    elif provider == "alignn":
        graph, line, _ = native
        if graph.num_nodes != nodes or line.num_nodes != graph.num_edges:
            raise ValueError("Original ALIGNN graph/line graph dimensions disagree")
        edges, degree = edge_statistics(nodes, graph.src.detach().cpu().tolist(), graph.dst.detach().cpu().tolist())
        if edges != graph.num_edges:
            raise ValueError("Original ALIGNN directed edge count disagrees")
        triplets = line.num_edges
        if triplets:
            observed, _ = edge_statistics(edges, line.src.detach().cpu().tolist(), line.dst.detach().cpu().tolist())
            if observed != triplets:
                raise ValueError("Original ALIGNN triplet count disagrees")
    else:
        index = native["edge_index"]
        if len(index.shape) != 2 or index.shape[0] != 2:
            raise ValueError("Original provider returned incompatible edge_index")
        edges, degree = edge_statistics(nodes, *index.detach().cpu().tolist())
    extra = 0
    for _, module in auxiliary:
        graph = radius_graph(batch, module.cutoff)
        count, maximum = edge_statistics(nodes, graph.src.detach().cpu().tolist(), graph.dst.detach().cpu().tolist())
        extra += count
        degree = max(degree, maximum)
    return dict(atoms=nodes, native_edges=edges, native_triplets=triplets,
                auxiliary_edges=extra, maximum_degree=degree)


def write_training_rows(structures, records, counter, path):
    """Preserve failed-prefix evidence; only a complete stream may reach selection."""
    if len(structures) != len(records):
        raise ValueError("Training partition length differs from its identity list")
    with Path(path).open("x", encoding="utf-8") as stream:
        for index, expected in enumerate(records):
            structure = structures[index]
            if structure.identifier != expected["id"]:
                raise ValueError("Training structure identity changed while scanning")
            row = dict(counter(structure), index=index, id=expected["id"], source_index=expected["source_index"])
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            if index % 100 == 0:
                stream.flush()


def implementation_sources(backbone):
    prefixes = ("universal_gnn", "alignn", "jarvis", "cgcnn", "mace", "nequip", "ase",
                "pymatgen", "torch_geometric", "numpy", "scipy")
    paths = {}
    for name, module in tuple(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if name.split(".")[0] in prefixes and path and Path(path).suffix == ".py" and Path(path).is_file():
            paths[name] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    adapter = Path(inspect.getsourcefile(type(backbone)))
    paths["executed_native_input_adapter"] = hashlib.sha256(adapter.read_bytes()).hexdigest()
    return paths


def scan_training_graphs(config, output, **selection_options):
    """Publish a bound clean-geometry probe only after every original graph succeeds."""
    reference = reference_config(config)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Graph scan output must be a new directory")
    output.mkdir(parents=True)
    from universal_gnn.benchmarks.preflight import write_json

    report = dict(version=1, status="running", slurm_job_id=os.environ["SLURM_JOB_ID"],
                  config_sha256=canonical_sha(config), reference_config_sha256=canonical_sha(reference),
                  topology_reference="original_pretrained_constructor", model_forward_executed=False,
                  numerical_capacity_acceptance=False, formal_training_runs=0)
    report_path = output / "report.json"
    write_json(report_path, report)
    try:
        import torch
        from universal_gnn.contracts import StructureBatch
        from universal_gnn.data.splits.loading import load_partition
        from universal_gnn.engine.batching import model_dtype
        from universal_gnn.engine.training import build_model, dataset, version_record

        device, dtype = torch.device(config["device"]), model_dtype(config)
        if device.type == "cuda" and device.index is None:
            device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_device(device)
        torch.manual_seed(config.get("seed", 123))
        torch.cuda.manual_seed_all(config.get("seed", 123))
        structures = dataset(reference)
        executed_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        source = getattr(structures, "source", None)
        indices, manifest, manifest_sha = load_partition(source, reference["dataset"])
        if manifest is None or list(structures.indices) != list(indices):
            raise ValueError("Graph scan must traverse the entire source-ordered train partition")
        if list(indices) != sorted(indices):
            raise ValueError("Graph scan requires source-ordered training indices")
        records = [dict(id=source.identifiers[index], source_index=index) for index in indices]
        model = build_model(reference).to(device=device, dtype=dtype)
        backbone = model.backbone
        provider = config["backbone"]["name"]
        if backbone.official_artifact["provider"] != provider:
            raise ValueError("Loaded original provider differs from experiment")
        auxiliary = auxiliary_modules(model)

        def counter(structure):
            batch = StructureBatch.from_structures([structure]).to(device, dtype)
            return count_graphs(provider, backbone, auxiliary, batch)

        with forbid_model_forward(model), torch.no_grad():
            write_training_rows(structures, records, counter, output / "graph-sizes.jsonl")
        torch.cuda.synchronize(device)
        source_digest = hashlib.sha256()
        with Path(source.path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024**2), b""):
                source_digest.update(chunk)
        _, _, final_manifest_sha = load_partition(source, reference["dataset"])
        if source_digest.hexdigest() != source.sha256 or final_manifest_sha != manifest_sha:
            raise ValueError("Source or split changed during complete graph construction")
        definition = dict(provider=provider, cutoff=backbone.cutoff, dtype=config.get("dtype", "float32"),
                          device=str(device), auxiliary=[dict(path=name, cutoff=module.cutoff,
                                                             class_name=type(module).__name__) for name, module in auxiliary],
                          artifact_sha256=backbone.official_artifact["sha256"],
                          provider_settings=getattr(backbone, "settings", getattr(backbone, "configuration", None)),
                          sources=implementation_sources(backbone), versions=version_record())
        definition["dependencies"] = {name:importlib.metadata.version(name) for name in ("torch", "numpy", "scipy", "ase")}
        if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != executed_commit:
            raise ValueError("Source checkout changed during graph scan; rerun with a stable published commit")
        binding = dict(source_sha256=source.sha256, split_manifest_sha256=manifest_sha,
                       graph_definition_sha256=canonical_sha(definition), dtype=config.get("dtype", "float32"),
                       native_edge_kind="padded_neighbor_slots" if provider == "cgcnn" else "directed_edges")
        with (output / "graph-sizes.jsonl").open(encoding="utf-8") as stream:
            probe = select_probe((json.loads(line) for line in stream), records, binding, **selection_options)
        probe["coverage"].update(verified_full_training_scan=True, kind="original_native_and_active_auxiliary_clean_train_graphs",
                                 geometry_scope="clean_training_structures_only", model_forward_executed=False,
                                 graph_definition=definition, scan_slurm_job_id=os.environ["SLURM_JOB_ID"])
        report.update(status="complete", structures=len(records), graph_binding=binding,
                      git_commit=executed_commit,
                      probe_sha256=canonical_sha(probe))
        write_json(output / "probe.json", probe)
        write_json(report_path, report)
        return probe
    except Exception as error:
        (output / "probe.json").unlink(missing_ok=True)
        report.update(status="failed", error=str(error), error_type=type(error).__name__)
        write_json(report_path, report)
        raise
