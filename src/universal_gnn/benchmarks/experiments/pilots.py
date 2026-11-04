"""Prepare diagnostic subsets inside frozen partitions; never launch or count formal runs."""

import copy
import hashlib
import json
from pathlib import Path

from universal_gnn.data.splits.manifest import PARTITIONS, create_manifest, validate_manifest
from .recipes import INITIALIZATIONS, SEEDS, TASK_DATASETS, TASKS, validate_registry
from .registry import DATASETS, MODELS, canonical_digest


def select_pilot_indices(manifest, *, counts=None, seed=123):
    counts = dict(train=64, validation=16, test=16) if counts is None else dict(counts)
    if (set(counts) != set(PARTITIONS) or any(type(value) is not int or value < 1 for value in counts.values()) or
            type(seed) is not int or seed < 0):
        raise ValueError("Pilot selection requires positive partition counts and a nonnegative integer seed")
    validate_manifest(manifest, source_sha256=manifest["source_sha256"], source_count=manifest["source_count"])
    selected = {}
    for role in PARTITIONS:
        candidates = manifest["partitions"][role]
        if len(candidates) < counts[role]:
            raise ValueError(f"{role} has fewer records than requested; no silent count reduction")
        rank = lambda index: (hashlib.sha256(json.dumps(["ugnn-pilot-v1", seed, role, manifest["records"][index]["id"]],
                                                       separators=(",", ":")).encode()).hexdigest(), index)
        selected[role] = sorted(sorted(candidates, key=rank)[:counts[role]])
    return selected


def write_pilot_dataset(entry, output, *, counts=None, seed=123):
    """Hash and verify the full parent stream while retaining only selected raw records."""
    manifest = json.loads(Path(entry["split_manifest"]).read_text(encoding="utf-8"))
    if canonical_digest(manifest) != entry["split_manifest_sha256"]:
        raise ValueError("Parent split manifest fingerprint changed")
    if manifest["source_sha256"] != entry["sha256"]:
        raise ValueError("Parent source and split identities disagree")
    selected = select_pilot_indices(manifest, counts=counts, seed=seed)
    roles = {index:role for role in PARTITIONS for index in selected[role]}
    output = Path(output);output.mkdir(parents=True, exist_ok=False)
    partial = output / "structures.jsonl.partial"
    parent_digest, subset_digest = hashlib.sha256(), hashlib.sha256()
    source_index, records, assignments = 0, [], {}
    with Path(entry["path"]).open("rb") as stream, partial.open("xb") as target:
        for line in stream:
            parent_digest.update(line)
            if not line.strip():
                continue
            row = json.loads(line)
            if (source_index >= manifest["source_count"] or
                    row.get("id") != manifest["records"][source_index]["id"]):
                raise ValueError("Parent source-ordered structure identities changed")
            if source_index in roles:
                payload = line if line.endswith(b"\n") else line + b"\n"
                target.write(payload);subset_digest.update(payload)
                records.append(dict(manifest["records"][source_index]))
                assignments[row["id"]] = roles[source_index]
            source_index += 1
    if (parent_digest.hexdigest() != entry["sha256"] or source_index != manifest["source_count"] or
            len(records) != len(roles)):
        raise ValueError("Parent source fingerprint/count changed; diagnostic subset is not published")
    sha = subset_digest.hexdigest()
    subset = create_manifest(records, source_sha256=sha, official=assignments)
    subset["protocol"] = dict(kind="diagnostic_id_hash_inside_frozen_parent_roles", seed=seed,
                              parent_source_sha256=entry["sha256"],
                              parent_split_manifest_sha256=entry["split_manifest_sha256"])
    partial.replace(output / "structures.jsonl")
    (output / "split.json").write_text(json.dumps(subset, indent=2), encoding="utf-8")
    audit = dict(kind="arxiv_v1_diagnostic_subset", formal_training_runs=0, selected_counts=subset["counts"],
                 selected_parent_indices=selected, source_sha256=entry["sha256"],
                 parent_split_manifest_sha256=entry["split_manifest_sha256"],
                 selection="ID hash within each existing role; no atom-count or label-based selection",
                 all_parent_records_verified=source_index)
    (output / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return dict(path=str(output / "structures.jsonl"), sha256=sha, split_manifest=str(output / "split.json"),
                split_manifest_sha256=canonical_digest(subset), structures=len(records), split_counts=subset["counts"])


def pilot_config(config, dataset, *, epochs=3, batch_size=2):
    if any(type(value) is not int or value < 1 for value in (epochs, batch_size)):
        raise ValueError("Diagnostic epochs and batch size must be positive integers")
    if (config.get("structures") != "all" or config.get("dataset", {}).get("partition") != "train" or
            config.get("max_atoms") is not None or config.get("backbone", {}).get("initialization") not in INITIALIZATIONS or
            config.get("backbone", {}).get("implementation") != "official"):
        raise ValueError("Pilot configs must derive from complete original training definitions")
    if config["backbone"].get("neighbor_statistics") is not None or config.get("generation_prior") is not None:
        raise ValueError("Do not reuse fitted full-data statistics in a diagnostic subset")
    result = copy.deepcopy(config)
    result.update(epochs=epochs, batch_size=batch_size)
    result.setdefault("evaluation", {}).update(patience=None)
    result["dataset"].update({key:dataset[key] for key in ("path", "sha256", "split_manifest", "split_manifest_sha256")})
    return result


def prepare_pilots(parent_matrix, output, *, counts=None, seed=123, epochs=3, batch_size=2):
    """Create 48 single-seed definitions and five shared subsets; require runtime gates later."""
    if (parent_matrix.get("kind") != "arxiv_v1_primary_matrix" or parent_matrix.get("expected_training_runs") != 144 or
            parent_matrix.get("registry_sha256") != canonical_digest(parent_matrix.get("registry"))):
        raise ValueError("Require the frozen complete primary matrix")
    validate_registry(parent_matrix["registry"])
    complete = {(model, task, mode, value) for model in MODELS for task in TASKS for mode in INITIALIZATIONS for value in SEEDS}
    if (len(parent_matrix["cases"]) != 144 or
            {(case["model"], case["task"], case["initialization"], case["seed"]) for case in parent_matrix["cases"]} != complete):
        raise ValueError("Parent matrix must retain all 144 original comparisons")
    cases = [case for case in parent_matrix["cases"] if case["seed"] == seed]
    expected = {(model,task,mode) for model in MODELS for task in TASKS for mode in INITIALIZATIONS}
    if len(cases) != 48 or {(case["model"],case["task"],case["initialization"]) for case in cases} != expected:
        raise ValueError("Require all four models, six tasks and two initializations for the selected seed")
    for case in cases:
        identity = f"seed-{seed}--{case['task']}--{case['model']}"
        if case["pair_id"] != identity or case["id"] != identity + "--" + case["initialization"]:
            raise ValueError("Parent case IDs must match the frozen model/task/initialization identity")
        if case["config_sha256"] != canonical_digest(case["config"]):
            raise ValueError("Parent case configuration fingerprint changed")
        if (case["config"].get("seed") != seed or case["config"]["backbone"].get("name") != case["model"] or
                case["config"]["backbone"].get("initialization") != case["initialization"]):
            raise ValueError("Parent case model/seed/initialization configuration disagrees with its identity")
        dataset = parent_matrix["registry"]["datasets"][TASK_DATASETS[case["task"]]]
        if any(case["config"]["dataset"].get(key) != dataset[key]
               for key in ("path", "sha256", "split_manifest", "split_manifest_sha256")):
            raise ValueError("Parent case is not bound to its registered complete dataset")
        pilot_config(case["config"], dataset, epochs=epochs, batch_size=batch_size)
    output = Path(output);output.mkdir(parents=True, exist_ok=False)
    datasets = {name:write_pilot_dataset(parent_matrix["registry"]["datasets"][name], output / "data" / name,
                                       counts=counts, seed=seed) for name in DATASETS}
    config_directory = output / "configs";config_directory.mkdir()
    prepared, pairs = [], {}
    for case in cases:
        identifier = "pilot--" + case["id"]
        config = pilot_config(case["config"], datasets[TASK_DATASETS[case["task"]]], epochs=epochs, batch_size=batch_size)
        target = config_directory / (identifier + ".json")
        target.write_text(json.dumps(config, indent=2, allow_nan=False), encoding="utf-8")
        item = dict(id=identifier, parent_case=case["id"], parent_config_sha256=case["config_sha256"],
                    model=case["model"], task=case["task"], initialization=case["initialization"], seed=seed,
                    config=config, config_sha256=canonical_digest(config), config_path=str(target),
                    python_environment=case["python_environment"], run_directory=str(output / "runs" / identifier),
                    required_gates=copy.deepcopy(case["required_gates"]), status="awaiting_runtime_acceptance")
        if case["task"] == "generation":
            item["generation_diagnostic"] = dict(samples=8, draws_per_condition=1, seed=456,
                                                  interpretation="shape/path diagnostic only; no benchmark-quality claim")
        prepared.append(item)
        pair_id = "pilot--" + case["pair_id"]
        pairs.setdefault(pair_id, dict(id=pair_id, cases=[]))["cases"].append(identifier)
    result = dict(version=1, kind="arxiv_v1_diagnostic_pilots", status="prepared_not_launched", seed=seed,
                  parent_matrix_sha256=canonical_digest(parent_matrix), parent_registry_sha256=parent_matrix["registry_sha256"],
                  datasets=datasets, cases=prepared, pairs=list(pairs.values()), expected_pilot_runs=48,
                  expected_formal_runs=144, completed_pilot_runs=0, formal_training_runs=0,
                  interpretation="diagnostic subsets only; original-model numerical acceptance and paired capacity still required")
    (output / "matrix.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result
