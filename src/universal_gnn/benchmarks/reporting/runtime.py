"""Single-seed48-row/24-pair summaries from verified acceptance archives only."""

import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from ..experiments.registry import canonical_digest
from .evidence import Inputs, accepted_case, sha

SCOPE_SHA = "9b33ab3f987bd9476c24711b7e0adc39cb4abfee666840fe086c6aea31837ea7"
METRICS = {"mae", "rmse", "mean_structure_frobenius_error", "mean_relative_structure_frobenius_error",
           "auroc", "average_precision", "f1", "balanced_accuracy", "accuracy", "precision", "recall", "mcc"}


def identity(identifier):
    match = re.fullmatch(r"seed-123--(classification|bandgap|dielectric|spectrum|forcefield|generation)--(cgcnn|alignn|mace|nequip)--(pretrained|scratch)", identifier)
    if not match:
        raise ValueError("Select only the fixed six-task/four-model/two-initialization seed123 scope")
    return dict(case_id=identifier, task=match[1], model=match[2], initialization=match[3], seed=123)


def protocol(config):
    result = copy.deepcopy(config)
    result.pop("resolved_components", None)
    result["backbone"].pop("initialization", None)
    result["backbone"].pop("neighbor_statistics", None)
    return result


def costs(proof, trained, evidence):
    raw = proof["resource_costs"]
    result = {}
    for source, target in [("wall_seconds", "train_validation_test_save_wall_seconds"),
            ("peak_gpu_allocated_bytes", "train_peak_gpu_allocated_bytes"),
            ("peak_gpu_reserved_bytes", "train_peak_gpu_reserved_bytes"),
            ("peak_process_rss_bytes", "train_peak_process_rss_bytes"), ("final_artifact_bytes", "final_artifact_bytes")]:
        value = raw.get(source)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("Actual training cost must be finite positive recorded evidence")
        result[target] = value
    post = evidence.get("cpu_postevaluation_cost", proof.get("cpu_postevaluation_cost", {}))
    result.update(cpu_postprocess_physics_allsource_wall_seconds=post.get("wall_seconds"),
        cpu_postprocess_peak_process_rss_bytes=post.get("peak_process_rss_bytes"),
        cpu_independent_verification_seconds=evidence.get("cpu_independent_verification_seconds", proof.get("cpu_independent_verification_seconds")),
        isolated_inference_seconds=None, peak_disk_bytes=None,
        components=trained.get("components", {}),
        interpretation="Recorded process wall time includes training/validation/test/save; CPU post combines raw-label/physics/all-source work. Final artifact bytes are not peak disk; missing measurements stay null. Component effective counts are declared upper bounds, not measured nonzero-gradient counts.")
    for key in ["cpu_postprocess_physics_allsource_wall_seconds", "cpu_postprocess_peak_process_rss_bytes", "cpu_independent_verification_seconds"]:
        value = result[key]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
            raise ValueError("Recorded CPU costs must be finite positive, or explicitly unavailable")
    return result


def scalar_metrics(tree, prefix=""):
    for key, value in tree.items():
        name = prefix + key
        if isinstance(value, dict):
            yield from scalar_metrics(value, name + ".")
        elif key in METRICS and value is not None:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Reported scalar performance metrics must be finite or null")
            yield name, value


def reporter_provenance():
    repository = Path(__file__).resolve().parents[4]
    files = sorted(Path(__file__).parent.glob("*.py")) + [repository / "scripts/summarize_arxiv_results.py"]
    files += [repository / "src/universal_gnn/benchmarks" / name for name in
        ["experiments/registry.py", "experiments/recipes.py", "prediction_assessment/contracts.py", "prediction_assessment/runtime.py"]]
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, capture_output=True, text=True)
    commit = result.stdout.strip() if result.returncode == 0 else None
    sources = {}
    for path in files:
        name = path.relative_to(repository).as_posix()
        raw = path.read_bytes()
        blob = subprocess.run(["git", "show", str(commit) + ":" + name], cwd=repository, capture_output=True)
        normalized = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        sources[name] = dict(actual_sha256=sha(path), normalized_lf_sha256=normalized,
            git_blob_sha256=hashlib.sha256(blob.stdout).hexdigest() if blob.returncode == 0 else None)
    return dict(git_commit=commit, source_sha256=sources,
        committed_source=all(row["normalized_lf_sha256"] == row["git_blob_sha256"] for row in sources.values()))


def build_summary(index_path, scope_path):
    inputs = Inputs()
    scope = inputs.read(scope_path, SCOPE_SHA)
    ids = scope["active_case_ids"]
    if scope.get("training_seeds") != [123] or scope.get("expected_training_runs") != 48 or len(ids) != len(set(ids)) or len(ids) != 48:
        raise ValueError("Require the unchanged complete48 single-seed execution scope")
    rows = {identifier: dict(identity(identifier), status="not_independently_accepted", metrics=None, costs=None) for identifier in ids}
    index_path = Path(index_path);index = inputs.read(index_path)
    if (index.get("status") != "passed" or index.get("formal_cases_submitted") != 48
            or len(index["cases"]) != index.get("formal_training_runs_independently_verified")):
        raise ValueError("Acceptance index counts/status differ")
    seen, configs = set(), {}
    for entry in index["cases"]:
        identifier = entry["case_id"]
        if identifier not in rows or identifier in seen:
            raise ValueError("Duplicate or out-of-scope accepted case")
        seen.add(identifier)
        proof, trained, evidence = accepted_case(inputs, index_path.parent, entry, rows[identifier])
        configs[identifier] = trained["config"]
        held = trained["heldout"]
        rows[identifier].update(status="independently_accepted", job=str(entry["job"]), metrics=proof["metrics"],
            completed_epochs=proof["completed_epochs"], best_epoch=proof["best_epoch"],
            counts=dict(train=held["declared_train_structures"], validation=held["validation_structures"], test=held["test_structures"]),
            source_structures=held["source_structures"], batch_size=trained["config"]["batch_size"], dtype=trained["config"]["dtype"],
            source_sha256=trained["config"]["dataset"]["sha256"], split_manifest_sha256=trained["config"]["dataset"]["split_manifest_sha256"],
            target_bindings=trained["config"]["dataset"].get("bindings", {}),
            best_checkpoint_sha256=proof["best_checkpoint_sha256"], costs=costs(proof, trained, evidence), evidence=evidence,
            protocol_sha256=canonical_digest(protocol(trained["config"])))
    pairs = []
    for task in ["classification", "bandgap", "dielectric", "spectrum", "forcefield", "generation"]:
        for model in ["cgcnn", "alignn", "mace", "nequip"]:
            prefix = "seed-123--" + task + "--" + model
            ft, scratch = rows[prefix + "--pretrained"], rows[prefix + "--scratch"]
            pair = dict(task=task, model=model, seed=123, pretrained=ft["case_id"], scratch=scratch["case_id"],
                status="incomplete", missing=[row["case_id"] for row in [ft, scratch] if row["status"] != "independently_accepted"], differences={})
            if not pair["missing"]:
                if (ft["protocol_sha256"] != scratch["protocol_sha256"] or ft["counts"] != scratch["counts"]
                        or ft["source_sha256"] != scratch["source_sha256"] or ft["split_manifest_sha256"] != scratch["split_manifest_sha256"]):
                    raise ValueError("Initialization pair changed data/head/optimization/common-batch protocol")
                left, right = dict(scalar_metrics(ft["metrics"])), dict(scalar_metrics(scratch["metrics"]))
                if set(left) != set(right):
                    raise ValueError("Paired performance metric schemas differ")
                pair.update(status="complete", differences={key: dict(pretrained=left[key], scratch=right[key],
                    pretrained_minus_scratch=left[key] - right[key]) for key in left})
            pairs.append(pair)
    inputs.unchanged()
    return dict(version=1, kind="single_seed_accepted_primary_summary", training_seeds=[123], required_cases=48,
        accepted_cases=len(seen), missing_cases=48-len(seen), rows=[rows[k] for k in ids], pairs=pairs,
        complete_pairs=sum(pair["status"] == "complete" for pair in pairs), input_sha256=inputs.sha256,
        reporter=reporter_provenance(),
        interpretation="Accepted scientific index only; pending/diagnostic/native/supplemental results are not primary completion. Raw same-seed paired differences, no cross-seed mean/std or general pretraining benefit. Missing peak disk and isolated inference timing remain unavailable.")


def markdown(summary):
    lines = ["# Accepted primary experiment snapshot", "",
        f"Seed123: {summary['accepted_cases']}/48 independently accepted; {summary['complete_pairs']}/24 complete initialization pairs.", "",
        "| Task | Model | Initialization | Status | Epoch / best | Train / val / test |", "|---|---|---|---|---|---|"]
    for row in summary["rows"]:
        counts = row.get("counts", {})
        lines.append("| " + " | ".join(str(value) for value in [row["task"], row["model"], row["initialization"], row["status"],
            str(row.get("completed_epochs", ""))+" / "+str(row.get("best_epoch", "")),
            " / ".join(str(counts.get(key, "")) for key in ["train", "validation", "test"])]) + " |")
    lines += ["", "| Task | Model | Metric | Pretrained | Scratch | Pretrained minus scratch |",
        "|---|---|---|---:|---:|---:|"]
    for pair in summary["pairs"]:
        for metric, values in pair["differences"].items():
            lines.append("| " + " | ".join(str(v) for v in [pair["task"], pair["model"], metric, values["pretrained"], values["scratch"], values["pretrained_minus_scratch"]]) + " |")
    lines += ["", "| Case | Original scalar metric | Value |", "|---|---|---:|"]
    for row in summary["rows"]:
        for name, value in scalar_metrics(row["metrics"] or {}):
            lines.append("| " + row["case_id"] + " | " + name + " | " + str(value) + " |")
    lines += ["", "| Case | Train+validation+test+save wall s | GPU allocated bytes | GPU reserved bytes | Train process RSS bytes | CPU combined post s | Independent check s | Final artifact bytes | Peak disk bytes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    names = ["train_validation_test_save_wall_seconds", "train_peak_gpu_allocated_bytes", "train_peak_gpu_reserved_bytes",
        "train_peak_process_rss_bytes", "cpu_postprocess_physics_allsource_wall_seconds", "cpu_independent_verification_seconds", "final_artifact_bytes", "peak_disk_bytes"]
    for row in summary["rows"]:
        if row["costs"]:
            lines.append("| " + row["case_id"] + " | " + " | ".join(str(row["costs"][name]) if row["costs"][name] is not None else "unavailable" for name in names) + " |")
    lines += ["", "Training wall time includes validation, test and save; CPU post includes physics and all-source inference.",
        "Costs, original metrics, component parameter bounds and input hashes are retained in summary.json.",
        "Target unit bindings are retained in JSON; signed differences use original metric units without percent normalization.",
        "Peak disk and isolated inference timing were not recorded; final artifact bytes are not peak disk.",
        "No cross-seed statistics or universal pretraining-benefit claim.", ""]
    return "\n".join(lines)


def write_summary(index_path, scope_path, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite a result summary")
    summary = build_summary(index_path, scope_path)
    output.mkdir(parents=True, exist_ok=False)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf8")
    (output / "summary.md").write_text(markdown(summary), encoding="utf8")
    return summary
