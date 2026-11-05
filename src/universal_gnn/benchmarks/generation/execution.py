"""Full generation training and independently scheduled sampling quality."""

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time
from contextlib import nullcontext

from ..execution.gates import case_spec, check_preparation, compatible_sources, file_sha, installed_versions, read_json
from ..execution.runner import allocation_budget, finite_shape
from ..experiments.registry import canonical_digest
from ..preflight import write_json
from .evidence import validate_prior


def generation_case(matrix, identifier):
    spec = case_spec(matrix, identifier, allow_generation=True)
    if spec["case"]["task"] != "generation":
        raise ValueError("This entry requires a full generation case")
    from .preparation import generation_spec

    definition = generation_spec(matrix, spec["case"]["pair_id"])
    return dict(spec, quality_protocol=definition["quality"])


def verify_generation_training(trained, gate, events):
    config, counts = gate["config"], gate["counts"]
    prior = gate["training_prior"]
    validate_prior(prior, counts["train"])
    epochs = trained.get("completed_epochs")
    if (not trained.get("passed") or not trained.get("checkpoint_reload") or
            trained.get("config") != config or trained.get("data_fingerprint") != prior["statistics"]["training_fingerprint"] or
            type(epochs) is not int or not 1 <= epochs <= config["epochs"] or
            trained.get("requested_epochs") != config["epochs"] or trained.get("selected_structures") != counts["train"] or
            trained.get("available_structures") != gate["source_structures"] or
            trained.get("resume") != {"path": None, "kind": "none", "completed_epochs_before": 0} or
            len(trained.get("history", [])) != epochs or len(trained.get("backbone_gradient_norms", [])) != epochs or
            any(not math.isfinite(g) or g <= 0 for g in trained["backbone_gradient_norms"])):
        raise ValueError("Generation did not preserve full fresh training and its training-only prior")
    if not all(trained.get("reload_verification", {}).get(k) for k in ("state_exact", "deterministic_algorithms")):
        raise ValueError("Generation requires exact-state deterministic reload verification")
    official = trained["execution"]["official"]
    if official["initialization"] != gate["case"]["initialization"]:
        raise ValueError("Generation used another initialization")
    if official["initialization"] == "scratch":
        if official.get("parameter_coverage") != 0. or official.get("buffer_coverage") != 0. or not official.get("state_layout_verified"):
            raise ValueError("Generation scratch reused source parameters or changed original layout")
    elif official.get("parameter_coverage") != 1.:
        raise ValueError("Generation did not preserve all pretrained body parameters")
    train = [e for e in events if e["event"] == "epoch"]
    validation = [e for e in events if e["event"] == "validation"]
    if (len(train) != epochs or len(validation) != epochs or
            [r["epoch"] for r in train] != list(range(1, epochs + 1)) or
            [r["epoch"] for r in validation] != list(range(1, epochs + 1)) or
            any(type(loss) not in (int, float) or not math.isfinite(loss) for loss in trained["history"]) or
            any(type(e.get("loss")) not in (int, float) or not math.isfinite(e["loss"]) for e in train + validation) or
            [e["loss"] for e in train] != trained["history"] or
            any(e["structures"] != counts["train"] or e["minibatches"] != math.ceil(counts["train"] / config["batch_size"]) for e in train) or
            any(e["structures"] != counts["validation"] for e in validation)):
        raise ValueError("Generation lacks complete train/validation epochs")
    held = trained["heldout"]
    tracker = held["selection"]["tracker"]
    if (held.get("structures") != counts["test"] or held.get("validation_structures") != counts["validation"] or
            held.get("declared_train_structures") != counts["train"] or held.get("source_structures") != gate["source_structures"] or
            held.get("partition") != "test" or held.get("checkpoint_role") != "validation_best" or
            held.get("source_sha256") != config["dataset"]["sha256"] or
            tracker["manifest_sha256"] != config["dataset"]["split_manifest_sha256"] or
            len(tracker["history"]) != epochs or
            any(e["epoch"] != h["epoch"] or e["loss"] != h["loss"] for e, h in zip(validation, tracker["history"]))):
        raise ValueError("Generation selection/test provenance differs from complete validation")
    best = min(tracker["history"], key=lambda row: row["loss"])
    if best["epoch"] != tracker["best_epoch"] or best["loss"] != tracker["best_loss"]:
        raise ValueError("Generation weights were not selected by the true validation minimum")
    if epochs < config["epochs"] and (not trained.get("early_stopped") or tracker["bad_epochs"] != config["evaluation"]["patience"]):
        raise ValueError("Generation stopped without its declared patience")
    if file_sha(trained["best_checkpoint"]) != held["selection"]["best_sha256"]:
        raise ValueError("Generation best checkpoint bytes changed")
    manifest = read_json(config["dataset"]["split_manifest"])
    if canonical_digest(manifest) != config["dataset"]["split_manifest_sha256"] or file_sha(config["dataset"]["path"]) != config["dataset"]["sha256"]:
        raise ValueError("Generation source/split changed during training")
    expected = [manifest["records"][i]["id"] for i in manifest["partitions"]["test"]]
    seen = []
    with Path(held["predictions"]).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("noise_phase") != "test" or set(row["predictions"]) != {"fractional_score", "cell_score"} or set(row["targets"]) != {"fractional_score", "cell_score"}:
                raise ValueError("Denoising output/noise phase differs")
            for key, shape in (("fractional_score", (5, 3)), ("cell_score", (1, 6))):
                finite_shape(row["predictions"][key], shape)
                finite_shape(row["targets"][key], shape)
            seen.append(row["id"])
    if seen != expected or len(seen) != counts["test"]:
        raise ValueError("Denoising test must cover all ordered frozen test IDs")
    return dict(completed_epochs=epochs, best_epoch=tracker["best_epoch"],
                test_structures=len(seen), best_checkpoint_sha256=held["selection"]["best_sha256"])


def verify_quality(result, trained, gate, *, diagnostic=False):
    """Audit every attempted condition/draw, including explicitly invalid samples."""
    from universal_gnn.engine.generative.protocol import condition_indices

    protocol, counts, config = gate["quality_protocol"], gate["counts"], gate["config"]
    requested, draws, seed = protocol["samples"], protocol["draws_per_condition"], protocol["seed"]
    if (requested, draws, seed) != ((8, 1, 456) if diagnostic else (1000, 5, 456)):
        raise ValueError("Use the frozen formal1000/5 protocol or explicit diagnostic8/1 protocol")
    if (not result.get("execution_complete") or result.get("meets_v1_sample_count") is not (not diagnostic) or
            result.get("requested_samples") != requested or result.get("attempted") != requested or
            result.get("draws_per_condition") != draws or result.get("seed") != seed or result.get("sampling_batch_size") != 1 or
            result.get("training_structures") != counts["train"] or result.get("declared_training_structures") != counts["train"] or
            not result.get("full_training_partition") or result.get("available_test_conditions") != counts["test"] or
            result.get("partition") != "test" or result.get("checkpoint_role") != "validation_best" or
            result.get("checkpoint_sha256") != trained["heldout"]["selection"]["best_sha256"] or
            result.get("source_sha256") != config["dataset"]["sha256"] or result.get("manifest_sha256") != config["dataset"]["split_manifest_sha256"] or
            result.get("training_prior") != gate["training_prior"] or result.get("sampling") != config["task"]["sampling"]):
        raise ValueError("Quality did not complete the frozen full test/prior/best/1000-attempt protocol")
    geometry = dict(three_dimensional_pbc=True, positive_volume=True,
                    fractional_coordinates_in_unit_cell=True, minimum_periodic_distance_angstrom=.5)
    matching = dict(implementation="pymatgen.StructureMatcher", ltol=.3, stol=.5, angle_tol=10.,
                    primitive_cell=False, scale=True, attempt_supercell=False, symmetric=True,
                    comparator="ElementComparator", rms_unit="normalized by (V/N)^(1/3)")
    if (result.get("geometry_definition") != geometry or result.get("matching") != matching or
            result.get("conditioning") != "given composition and atom count"):
        raise ValueError("Quality geometry/matching/conditioning protocol changed")
    manifest = read_json(config["dataset"]["split_manifest"])
    if canonical_digest(manifest) != config["dataset"]["split_manifest_sha256"]:
        raise ValueError("Quality source split changed")
    ids = [manifest["records"][i]["id"] for i in manifest["partitions"]["test"]]
    selected = condition_indices(ids, count=requested // draws, seed=seed)
    expected = [(ids[i], draw) for i in selected for draw in range(draws)]
    expected_numbers, training_compositions = {}, set()
    needed, training_indices = {ids[i] for i in selected}, set(manifest["partitions"]["train"])
    source_hash, source_count = hashlib.sha256(), 0
    with Path(config["dataset"]["path"]).open("rb") as source:
        for raw in source:
            source_hash.update(raw)
            if not raw.strip():
                continue
            record = json.loads(raw)
            if record["id"] != manifest["records"][source_count]["id"]:
                raise ValueError("Quality source ordered IDs changed")
            if source_count in training_indices or record["id"] in needed:
                atom = record.get("atoms", record)
                if "numbers" in atom:
                    numbers = atom["numbers"]
                else:
                    from ase.data import atomic_numbers

                    numbers = [atomic_numbers[symbol] for symbol in atom["elements"]]
                if len(numbers) != 5 or any(type(z) is not int or not 1 <= z <= 118 for z in numbers):
                    raise ValueError("Source violates the Perov-5 condition contract")
                if source_count in training_indices:
                    training_compositions.add(tuple(sorted(Counter(numbers).items())))
                if record["id"] in needed:
                    expected_numbers[record["id"]] = numbers
            source_count += 1
    if source_hash.hexdigest() != config["dataset"]["sha256"] or source_count != manifest["source_count"] or set(expected_numbers) != needed:
        raise ValueError("Quality full source or condition set changed")
    seen, digest, valid, unique, novel, matched, rms = [], hashlib.sha256(), 0, 0, 0, 0, []
    valid_compositions, seen_valid, seen_novel = Counter(), 0, 0
    with Path(result["samples"]).open("rb") as stream:
        sample_hash = hashlib.sha256()
        for raw in stream:
            sample_hash.update(raw)
            row = json.loads(raw)
            pair = (row["condition_id"], row["draw"])
            if type(row["draw"]) is not int or not 0 <= row["draw"] < draws or row["condition_id"] not in expected_numbers:
                raise ValueError("A quality row has an invalid condition/draw")
            payload = json.dumps(["ugnn-generation-sample-v1", seed, *pair], separators=(",", ":")).encode()
            digest.update(payload + b"\n")
            if row["sampling_seed"] != int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63):
                raise ValueError("A sampling draw changed its deterministic condition seed")
            quality, structure = row["quality"], row["structure"]
            if structure is not None:
                if (not isinstance(structure.get("numbers"), list) or len(structure["numbers"]) != 5 or
                        any(type(z) is not int or not 1 <= z <= 118 for z in structure["numbers"]) or
                        structure.get("pbc") != [True, True, True] or
                        structure["numbers"] != expected_numbers[row["condition_id"]]):
                    raise ValueError("Generated structure changed the Perov-5 condition format")
                finite_shape(structure["positions"], (5, 3))
                finite_shape(structure["cell"], (3, 3))
            if type(quality.get("geometrically_valid")) is not bool:
                raise ValueError("Missing geometric validity observation")
            if quality["geometrically_valid"]:
                if (structure is None or quality.get("reason") is not None or
                        type(quality.get("unique")) is not bool or type(quality.get("novel_to_train")) is not bool or
                        type(quality.get("matches_assigned_reference")) is not bool):
                    raise ValueError("A valid sample lacks its geometry or structural observations")
                valid += 1
                unique += int(quality["unique"])
                novel += int(quality["novel_to_train"])
                matched += int(quality["matches_assigned_reference"])
                composition = tuple(sorted(Counter(structure["numbers"]).items()))
                valid_compositions[composition] += 1
                if composition in training_compositions:
                    seen_valid += 1
                    seen_novel += int(quality["novel_to_train"])
                if quality["normalized_rms"] is not None:
                    value = quality["normalized_rms"]
                    if not quality["matches_assigned_reference"] or type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                        raise ValueError("Invalid matched RMS observation")
                    rms.append(value)
            elif (quality.get("unique") is not None or quality.get("novel_to_train") is not None or
                    quality.get("matches_assigned_reference") is not False or quality.get("normalized_rms") is not None or
                    not isinstance(quality.get("reason"), str) or not quality["reason"]):
                raise ValueError("Invalid samples cannot contribute structural successes")
            seen.append(pair)
    if (seen != expected or result.get("condition_sha256") != digest.hexdigest() or
            result.get("selected_test_conditions") != len(selected)):
        raise ValueError("Quality omitted, repeated or reordered a frozen condition/draw")
    totals = dict(geometrically_valid=valid, unique_valid_structures=unique,
                  novel_valid_structures=novel, matched_assigned_references=matched,
                  valid_samples_with_training_seen_composition=seen_valid,
                  valid_composition_groups=len(valid_compositions),
                  valid_samples_with_repeated_generated_composition=sum(n for n in valid_compositions.values() if n > 1))
    rates = dict(geometric_validity=valid / requested, paired_match_rate=matched / requested,
                 uniqueness_among_valid=unique / valid if valid else None,
                 novelty_among_valid=novel / valid if valid else None,
                 novelty_among_valid_with_training_seen_composition=seen_novel / seen_valid if seen_valid else None,
                 paired_match_rate_among_valid=matched / valid if valid else None,
                 mean_normalized_rms_among_matches=math.fsum(rms) / len(rms) if rms else None)
    for key, value in {**totals, **rates}.items():
        actual = result.get(key)
        if value is None:
            if actual is not None:
                raise ValueError("Empty quality group must remain null")
        elif type(actual) not in (int, float) or not math.isclose(actual, value, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Quality summary differs from all attempted sample rows")
    distributions = result.get("distribution_wasserstein_1", {})
    if set(distributions) != {"volume_per_atom_angstrom3", "density_g_cm3"} or any(
            (value is not None if not valid else type(value) not in (int, float) or not math.isfinite(value) or value < 0)
            for value in distributions.values()):
        raise ValueError("Quality distribution metrics do not describe its valid sample population")
    return dict(attempted=requested, selected_test_conditions=len(selected), samples_sha256=sample_hash.hexdigest(),
                checkpoint_sha256=result["checkpoint_sha256"], condition_sha256=digest.hexdigest(),
                interpretation="Attempt/seed/shape/rate integrity only; independent geometric matching and distribution re-score remain separate")


def run_generation_case(matrix, identifier, preparation, *, budget_seconds):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal generation training must run through Slurm")
    spec = generation_case(matrix, identifier)
    root = Path(spec["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing generation case")
    gate = check_preparation(matrix, identifier, preparation, budget_seconds=budget_seconds, allow_generation=True)
    return _run_generation_with_gate(identifier, gate, budget_seconds=budget_seconds)


def _run_generation_with_gate(identifier, gate, *, budget_seconds):
    """Shared unchanged training, after a caller has checked its closed recipe."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal generation training must run through Slurm")
    root = Path(gate["case"]["run_directory"])
    if root.exists() or root.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing generation case")
    budget = allocation_budget(budget_seconds, gate["probed_train_only_seconds"])
    import resource
    import torch
    from universal_gnn.engine.training import run_training

    if not torch.cuda.is_available() or shutil.disk_usage(root.parent.parent).free < 20 * 1024**3:
        raise RuntimeError("Generation requires CUDA and20GiB disk reserve")
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "generation-gate.json", gate)
    write_json(root / "config.requested.json", gate["config"])
    started = time.perf_counter()
    status = dict(status="running", stage="full_generation_training", case_id=identifier,
                  git_commit=gate["git_commit"], slurm_job_id=os.environ["SLURM_JOB_ID"],
                  matrix_sha256=gate["matrix_sha256"], counts=gate["counts"],
                  formal_training_runs_completed=0, generation_quality_complete=False,
                  independent_postevaluation_verified=False, wall_budget_seconds=budget)

    def record(**values):
        status.update(values, updated_at=time.time())
        write_json(root / "formal-status.json", status)

    def event(name, **values):
        with (root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(event=name, time=time.time(), **values), allow_nan=False) + "\n")
        if name == "epoch":
            if values["structures"] != gate["counts"]["train"] or values["minibatches"] != math.ceil(gate["counts"]["train"] / gate["config"]["batch_size"]):
                raise RuntimeError("Generation epoch omitted training records")
            record(last_completed_epoch=values["epoch"])
            print(json.dumps(dict(epoch=values["epoch"], loss=values["loss"])), flush=True)
            if shutil.disk_usage(root).free < 20 * 1024**3:
                raise RuntimeError("Disk reserve below20GiB; retain checkpoints")

    try:
        record()
        torch.cuda.reset_peak_memory_stats()
        trained = run_training(gate["config"], root, event_callback=event)
        events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        accepted = verify_generation_training(trained, gate, events)
        record(status="training_passed_quality_pending", stage="awaiting_independent_quality",
               formal_training_runs_completed=1, **accepted,
               last_checkpoint_sha256=file_sha(trained["checkpoint"]), denoising_metrics=trained["heldout"]["metrics"],
               training_wall_seconds=time.perf_counter() - started,
               peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),
               peak_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
               peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        return status
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error))
        raise


def run_generation_case_quality(matrix, identifier, *, budget_seconds):
    return _run_generation_case_quality(matrix, identifier, budget_seconds=budget_seconds)


def _run_generation_case_quality(matrix, identifier, *, budget_seconds, staged=False):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Formal generation quality must run through Slurm")
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or budget_seconds <= 0:
        raise ValueError("Declare a finite positive quality wall-time budget")
    spec = generation_case(matrix, identifier)
    root = Path(spec["case"]["run_directory"])
    gate, trained, status = read_json(root / "generation-gate.json"), read_json(root / "report.json"), read_json(root / "formal-status.json")
    if (status.get("status") not in {"training_passed_quality_pending", "quality_failed"} or
            gate["matrix_sha256"] != spec["matrix_sha256"] or gate["quality_protocol"] != spec["quality_protocol"] or
            gate["case"] != spec["case"] or gate["counts"] != spec["counts"] or
            gate["source_structures"] != spec["source_structures"] or
            status.get("formal_training_runs_completed") != 1):
        raise ValueError("Quality requires an accepted new full generation training case")
    from .evidence import checked_generation_config

    checked_generation_config(gate["config"], spec["configs"][spec["case"]["initialization"]],
                              gate["common_batch_size"], gate["counts"], gate["training_prior"])
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    verify_generation_training(trained, gate, events)
    if file_sha(trained["checkpoint"]) != status["last_checkpoint_sha256"]:
        raise ValueError("Preserve the last checkpoint with validation selection history")
    if installed_versions() != gate["versions"]:
        raise ValueError("Quality environment differs from accepted generation training")
    commit = compatible_sources([gate["git_commit"], trained["execution"]["git_commit"]])
    policy = None
    if staged:
        from .staging import revalidate_gate, declared_quality_budget
        from .sampling_failures import invalid_geometry_attempts, sampling_policy

        revalidate_gate(matrix, identifier, gate)
        policy = sampling_policy()
    if gate.get("training_readiness_only"):
        if not staged:
            raise ValueError("A training-only gate requires the explicit staged quality entry")
        estimate = None
        budget = declared_quality_budget(budget_seconds)
    else:
        estimate = gate["probed_sample_batch_seconds"] * gate["quality_protocol"]["samples"]
        budget = allocation_budget(budget_seconds, estimate)
    import resource
    import torch
    from universal_gnn.engine.generative.quality import run_generation_quality

    context = nullcontext()
    if staged:
        from universal_gnn.tasks.generation import PeriodicDenoiser

        context = invalid_geometry_attempts(PeriodicDenoiser)

    if not torch.cuda.is_available() or shutil.disk_usage(root).free < 20 * 1024**3:
        raise RuntimeError("Quality requires CUDA and20GiB disk reserve")
    claim = root / "quality-active"
    claim.mkdir(exist_ok=False)
    owner = claim / "owner.json"
    write_json(owner, dict(slurm_job_id=os.environ["SLURM_JOB_ID"], git_commit=commit))
    try:
        status = read_json(root / "formal-status.json")
        if status.get("status") not in {"training_passed_quality_pending", "quality_failed"} or status.get("generation_quality_complete"):
            raise ValueError("Quality was already completed or claimed; do not overwrite its result")
    except Exception:
        owner.unlink()
        claim.rmdir()
        raise
    output = root / ("quality-" + os.environ["SLURM_JOB_ID"])
    attempts = status.setdefault("quality_attempts", [])
    attempts.append(dict(job=os.environ["SLURM_JOB_ID"], output=str(output), status="running"))
    started = time.perf_counter()

    def record(**values):
        status.update(values, updated_at=time.time())
        write_json(root / "formal-status.json", status)

    try:
        record(status="quality_running", stage="full_conditional_sampling", quality_wall_budget_seconds=budget,
               quality_budget_estimate_seconds=estimate,
               quality_budget_estimate_scope=("conservative full preflight batch time per single sample; not a measured trained1000-sample runtime"
                   if estimate is not None else "Declared finite initial allocation; no measured sampling throughput exists. Timeout remains failure and all attempts are retained."))
        if staged:
            record(sampling_failure_policy=policy)
        torch.cuda.reset_peak_memory_stats()
        protocol = gate["quality_protocol"]
        with context:
            result = run_generation_quality(trained["checkpoint"], output, count=protocol["samples"],
                draws_per_condition=protocol["draws_per_condition"], seed=protocol["seed"], device=gate["config"]["device"])
        if staged:
            result["sampling_failure_policy"] = policy
            write_json(output / "metrics.json", result)
        accepted = verify_quality(result, trained, gate)
        attempts[-1]["status"] = "passed"
        record(status="passed", stage="complete", generation_quality_complete=True, quality=str(output / "metrics.json"),
               quality_integrity=accepted, quality_execution_commit=commit,
               quality_wall_seconds=time.perf_counter() - started,
               quality_peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),
               quality_peak_gpu_reserved_bytes=torch.cuda.max_memory_reserved(),
               quality_peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        return status
    except Exception as error:
        attempts[-1]["status"] = "failed"
        record(status="quality_failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        owner.unlink()
        claim.rmdir()
