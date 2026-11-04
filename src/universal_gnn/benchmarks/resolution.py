"""Accept only declared generation defaults from a successful capacity worker."""

import copy
import math
import re


def resolved_candidate(candidate, worker):
    resolved = copy.deepcopy(candidate)
    _resolve_native_initialization(resolved, worker)
    generation = candidate.get("task", {}).get("kind") == "generation"
    if not generation:
        if "resolved_generation" in worker:
            raise ValueError("Non-generation worker supplied generation defaults")
        return resolved
    value = worker.get("resolved_generation")
    if not isinstance(value, dict) or set(value) != {"generation_corruption", "generation_prior", "sampling"}:
        raise ValueError("Generation worker must report its resolved noise, prior and sampling")
    from universal_gnn.engine.generative.protocol import corruption_mode

    mode = corruption_mode(candidate)
    if value["generation_corruption"] != mode:
        raise ValueError("Worker changed the generation corruption objective")
    sampling, previous = value["sampling"], candidate["task"].get("sampling", {})
    if not isinstance(sampling, dict) or not isinstance(previous, dict):
        raise ValueError("Generation sampling must be a mapping")
    if any(key not in sampling or sampling[key] != setting for key, setting in previous.items()):
        raise ValueError("Worker changed an explicit sampling setting")
    if set(sampling) - set(previous) - {"volume_per_atom"}:
        raise ValueError("Worker injected an undeclared sampling setting")
    prior = value["generation_prior"]
    if "generation_prior" in candidate and candidate["generation_prior"] != prior:
        raise ValueError("Worker changed an explicit generation prior")
    if mode == "per_epoch_structure_v2":
        if not isinstance(prior, dict) or prior.get("sampling_volume_source") not in {"train_fit", "explicit_config"}:
            raise ValueError("Generation worker lacks its training prior provenance")
        statistics = prior.get("statistics")
        if (not isinstance(statistics, dict) or statistics.get("version") != 1 or
                statistics.get("kind") != "train_log_volume_per_atom_v1" or
                statistics.get("fitted_partition") != "train" or type(statistics.get("structures")) is not int or
                statistics["structures"] < 1 or not isinstance(statistics.get("training_fingerprint"), str) or
                not re.fullmatch(r"[0-9a-f]{64}", statistics["training_fingerprint"])):
            raise ValueError("Generation worker lacks complete training prior statistics")
        volume = sampling.get("volume_per_atom")
        if type(volume) not in (int, float) or not math.isfinite(volume) or volume <= 0:
            raise ValueError("Generation worker lacks a finite positive sampling volume")
        if prior["sampling_volume_source"] == "train_fit" and volume != statistics.get("volume_per_atom"):
            raise ValueError("Worker sampling volume differs from its training fit")
        if prior["sampling_volume_source"] == "explicit_config" and "volume_per_atom" not in previous:
            raise ValueError("Worker claimed an explicit volume absent from the request")
        resolved["generation_prior"] = copy.deepcopy(prior)
    elif prior != candidate.get("generation_prior") or sampling != previous:
        raise ValueError("Legacy generation worker changed its fixed-noise protocol")
    resolved["generation_corruption"] = mode
    resolved["task"]["sampling"] = copy.deepcopy(sampling)
    return resolved


def _resolve_native_initialization(resolved, worker):
    from universal_gnn.backbones.blueprints import neighbor_normalization
    from universal_gnn.engine.initialization.policy import requires_native_neighbor_statistics

    value = worker.get("resolved_native_initialization")
    if not requires_native_neighbor_statistics(resolved):
        if "resolved_native_initialization" in worker:
            raise ValueError("Worker supplied native calibration for a different initialization path")
        return
    if not isinstance(value, dict) or set(value) != {"neighbor_statistics"}:
        raise ValueError("Scratch worker must report its resolved native initialization")
    statistics = value["neighbor_statistics"]
    execution = worker.get("execution")
    if not isinstance(execution, dict) or not isinstance(execution.get("official"), dict):
        raise ValueError("Scratch worker lacks actual official model construction provenance")
    official = execution["official"]
    if (official.get("initialization") != "scratch" or official.get("state_layout_verified") is not True or
            any(type(official.get(key)) not in (int, float) or official[key] != 0. for key in ("parameter_coverage", "buffer_coverage")) or
            statistics != official.get("neighbor_statistics")):
        raise ValueError("Worker native statistics differ from its actual fresh model")
    cutoff = execution.get("backbone_cutoff")
    if type(cutoff) not in (int, float) or not math.isfinite(cutoff) or cutoff <= 0:
        raise ValueError("Scratch worker lacks its original native cutoff")
    neighbor_normalization(statistics, provider=resolved["backbone"]["name"], cutoff=cutoff)
    if (statistics["dtype"] != resolved.get("dtype", "float32") or
            type(worker.get("selected_training_structures")) is not int or
            statistics["structures"] != worker["selected_training_structures"]):
        raise ValueError("Worker native calibration differs from training coverage or input precision")
    dataset = resolved.get("dataset", {})
    if resolved.get("graph") is not None:
        raise ValueError("Native calibration cannot accept a graph override")
    if not dataset.get("split_manifest") or dataset.get("partition") != "train":
        raise ValueError("Native calibration requires the complete training split")
    selected = resolved.get("structures")
    if selected is not None and selected != "all" and (type(selected) is not int or selected != statistics["structures"]):
        raise ValueError("Native calibration cannot certify a partial training selection")
    graph = statistics.get("native_graph")
    if (not isinstance(graph, dict) or graph.get("artifact_sha256") != official.get("sha256") or
            not isinstance(graph.get("artifact_sha256"), dict) or not graph["artifact_sha256"] or
            any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in graph["artifact_sha256"].values()) or
            not isinstance(graph.get("adapter_source_sha256"), str) or
            not re.fullmatch(r"[0-9a-f]{64}", graph["adapter_source_sha256"]) or
            graph.get("provider_version") != execution.get("backend_version") or
            not all(isinstance(graph.get(key), str) and graph[key] for key in ("provider_version", "ase_version", "torch_version"))):
        raise ValueError("Worker lacks matching native graph/artifact provenance")
    if "neighbor_statistics" in resolved["backbone"] and resolved["backbone"]["neighbor_statistics"] != statistics:
        raise ValueError("Worker changed explicit native neighbor statistics")
    resolved["backbone"]["neighbor_statistics"] = copy.deepcopy(statistics)
