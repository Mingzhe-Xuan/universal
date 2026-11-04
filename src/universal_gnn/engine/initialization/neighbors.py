"""Scan original graph inputs only; numerical graph construction must run on a compute node."""

import copy


def prepare_native_neighbors(config, structures=None, *, official_artifact=None):
    """Return a resolved copy for original MACE/NequIP scratch; never execute a GNN forward."""
    import torch

    from universal_gnn.backbones.blueprints import aggregate_native_neighbor_counts
    from universal_gnn.backbones.factory import make_backbone
    from universal_gnn.backbones.official.profiles import official_options
    from universal_gnn.contracts import StructureBatch
    from universal_gnn.data.splits.loading import load_partition
    from universal_gnn.engine.batching import model_dtype
    from universal_gnn.engine.runtime import data_fingerprint
    from universal_gnn.engine.training import dataset

    from .policy import training_identity, validate_bound_statistics

    resolved = copy.deepcopy(config)
    backbone = resolved["backbone"]
    provider = backbone["name"]
    if (provider not in {"mace", "nequip"} or backbone.get("implementation", "official") != "official" or
            backbone.get("initialization", "pretrained") != "scratch"):
        raise ValueError("Native neighbor preparation applies to original MACE/NequIP scratch only")
    if resolved.get("graph") is not None:
        raise ValueError("Native calibration cannot override the original graph builder")
    structures = dataset(resolved) if structures is None else structures
    source = getattr(structures, "source", None)
    if not hasattr(source, "sha256") or not hasattr(structures, "indices"):
        raise ValueError("Native calibration requires the complete indexed JSONL training partition")
    indices, manifest, manifest_sha = load_partition(source, resolved["dataset"])
    if manifest is None:
        raise ValueError("Native calibration requires an explicit training split manifest")
    identity = training_identity(resolved["dataset"], structures.indices, indices,
                                 source_sha256=source.sha256, manifest_sha256=manifest_sha,
                                 training_fingerprint=data_fingerprint(structures),
                                 dtype=str(model_dtype(resolved)).removeprefix("torch."))
    options = {key: value for key, value in backbone.items()
               if key not in {"name", "implementation", "feature_dim", "neighbor_statistics"}}
    if official_artifact is not None:
        options["_artifact"] = copy.deepcopy(official_artifact)
        # Calibration loads the source package; a saved scratch implementation describes the fresh body.
        options["_artifact"].pop("implementation", None)
    options = official_options(provider, options)
    options.update(initialization="pretrained", context_dim=0)
    devices = list(range(torch.cuda.device_count())) if torch.cuda.is_initialized() else []
    with torch.random.fork_rng(devices=devices):
        reference = make_backbone(provider, **options)
        if provider == "nequip" and "blueprint" not in reference.official_artifact["files"]:
            raise ValueError("Native scratch calibration requires the original NequIP author blueprint")
        graph_contract = reference.native_graph_provenance()
        previous = backbone.get("neighbor_statistics")
        if previous is not None:
            validate_bound_statistics(previous, identity, provider=provider, cutoff=reference.cutoff,
                                      native_graph=graph_contract)
        else:
            def counts():
                with torch.no_grad():
                    for structure in structures:
                        batch = StructureBatch.from_structures([structure])
                        native = reference.native_input(batch)
                        edges = native["edge_index"]
                        if edges.ndim != 2 or edges.shape[0] != 2 or edges.dtype != torch.long:
                            raise ValueError("Original native graph returned an invalid edge_index")
                        if edges.numel() and (int(edges.min()) < 0 or int(edges.max()) >= len(structure.numbers)):
                            raise ValueError("Original native graph edge index is outside its structure")
                        axis = 1 if provider == "mace" else 0
                        yield dict(atomic_nodes=len(structure.numbers), directed_edges=edges.shape[1],
                                   active_receivers=int(torch.unique(edges[axis]).numel()))
            statistics = aggregate_native_neighbor_counts(counts(), provider=provider, cutoff=reference.cutoff,
                                                           **identity)
            statistics["native_graph"] = graph_contract
            validate_bound_statistics(statistics, identity, provider=provider, cutoff=reference.cutoff,
                                      native_graph=graph_contract)
            backbone["neighbor_statistics"] = statistics
    return resolved
