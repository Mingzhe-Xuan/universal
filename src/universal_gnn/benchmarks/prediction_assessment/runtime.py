"""Formal CPU post-processing and a separate no-model acceptance stage."""

import json
import math
import os
from pathlib import Path
import sys
import time

from ..execution.gates import case_spec, check_preparation, compatible_sources, file_sha, read_json
from ..execution.runner import verify_training_report
from ..preflight import write_json
from ..submission.planning import finite_budget, measured_train_estimate
from .contracts import compare
from . import numerics
from .rescoring import rescore_saved
from .streaming import verify_inference_stream


def formal_context(matrix, identifier):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Predictive assessment must run through Slurm")
    spec = case_spec(matrix, identifier)
    case = spec["case"]
    scope = read_json(Path(__file__).resolve().parents[4] / "configs/arxiv_v1_scope.json")
    if (scope["base_matrix_sha256"] != spec["matrix_sha256"] or identifier not in scope["active_case_ids"] or
            case["seed"] not in scope["training_seeds"]):
        raise ValueError("Case is outside the current single-seed campaign scope")
    if Path(sys.prefix).name != case["python_environment"]:
        raise ValueError("Use the original provider's Python environment")
    root = Path(case["run_directory"])
    formal_path, report_path = root / "formal-status.json", root / "report.json"
    formal, trained = read_json(formal_path), read_json(report_path)
    if (formal.get("status") != "passed" or formal.get("stage") != "complete" or
            formal.get("formal_training_runs_completed") != 1 or formal.get("case_id") != identifier or
            formal.get("matrix_sha256") != spec["matrix_sha256"] or formal.get("counts") != spec["counts"] or
            any(formal.get(k) != case[k] for k in ("model", "task", "seed", "initialization"))):
        raise ValueError("Formal case identity or complete execution receipt differs")
    commit = compatible_sources([formal["git_commit"], trained["execution"]["git_commit"]])
    if (root / "execution-gate.json").is_file():
        original = read_json(root / "execution-gate.json")
        if original.get("case") != case or original.get("matrix_sha256") != spec["matrix_sha256"]:
            raise ValueError("Original training gate belongs to another frozen case")
        preparation, budget = original["preparation"], original["budget_seconds"]
    else:
        preparation = formal["preparation"]
        # Legacy full forcefield jobs predate execution-gate.json. Rebuild the same
        # scientific gate from its retained capacity measurements, without a new job.
        budget = finite_budget(measured_train_estimate(preparation, spec))
        if file_sha(Path(preparation) / "report.json") != formal["preparation_sha256"]:
            raise ValueError("Original preparation receipt changed")
    gate = check_preparation(matrix, identifier, preparation, budget_seconds=budget)
    if (gate["config"] != read_json(root / "config.requested.json") or
            (root / "execution-gate.json").is_file() and gate["config"] != original["config"]):
        raise ValueError("Prepared config differs from the actual requested training recipe")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf8").splitlines()]
    verified = verify_training_report(trained, gate, events)
    paths = [formal_path, report_path, root / "config.requested.json", root / "events.jsonl",
             Path(trained["best_checkpoint"]), Path(trained["checkpoint"]),
             Path(trained["heldout"]["predictions"]), Path(trained["config"]["dataset"]["path"]),
             Path(trained["config"]["dataset"]["split_manifest"]), Path(preparation) / "report.json"]
    if (root / "execution-gate.json").is_file():
        paths.append(root / "execution-gate.json")
    if file_sha(trained["best_checkpoint"]) != trained["heldout"]["selection"]["best_sha256"]:
        raise ValueError("Actual validation-best checkpoint changed")
    return dict(spec=spec, gate=gate, trained=trained, report_path=report_path, formal=formal,
                git_commit=commit, verified_training=verified,
                input_sha256={str(path): file_sha(path) for path in paths})


def unchanged(bindings):
    if any(file_sha(path) != digest for path, digest in bindings.items()):
        raise ValueError("Original training/source/checkpoint inputs changed during assessment")


def validation_sources():
    repository = Path(__file__).resolve().parents[4]
    return {str(path.relative_to(repository)).replace(os.sep, "/"): file_sha(path)
            for path in ((Path(__file__).resolve().parents[1] / "validation" / name)
                         for name in ("derivatives.py", "finite_difference.py", "precision.py", "cartesian.py"))}


def physical_selection(context):
    preparation = Path(context["gate"]["preparation"])
    prepared = read_json(preparation / "report.json")
    graph = Path(prepared.get("graph_scan_path", str(preparation / "graph-scan")))
    probe_path = graph / "probe.json"
    probe = read_json(probe_path)
    indices = probe["worst_indices"][:2]
    if len(indices) != 2 or len(set(indices)) != 2 or any(type(i) is not int or
            not 0 <= i < context["gate"]["counts"]["train"] for i in indices):
        raise ValueError("Require the original two distinct worst training inputs")
    manifest = read_json(context["trained"]["config"]["dataset"]["split_manifest"])
    ids = [manifest["records"][manifest["partitions"]["train"][i]]["id"] for i in indices]
    return dict(probe=str(probe_path), probe_sha256=file_sha(probe_path), indices=indices, ids=ids)


def verify_physics(physics, task, selection):
    required = ("forces_finite_difference", "stress_finite_difference") if task == "forcefield" else (
        "response_auxiliary_finite_difference",)
    if (physics.get("passed") is not True or physics.get("device") != "cpu" or
            physics.get("dtype") != "torch.float32" or physics.get("structure_ids") != selection["ids"] or
            not physics.get("checks") or any(not physics["checks"].get(k, {}).get("required") for k in required) or
            any(not row["passed"] for row in physics["checks"].values() if row["required"])):
        raise ValueError("Trained-best physical checks did not satisfy the original required protocol")
    expected = {}
    if task == "forcefield":
        expected.update({key: (.02, .002, True) for key in required})
        expected["net_force"] = (0, 2e-5, True)
        expected.update({"translation_" + key: (.001, .0002, True)
                         for key in ("total_energy", "forces", "stress")})
        expected.update({"rotation_" + key: (.001, .0002, True)
                         for key in ("energy", "forces", "stress")})
        expected.update({mode + "_batch_" + key: (2e-4, 2e-5, True)
                         for mode in ("train", "eval") for key in ("total_energy", "forces", "stress")})
    else:
        response = physics.get("response", {})
        guarantee = response.get("guarantee")
        if guarantee not in {"O3_cartesian", "SO3_cartesian", "fixed_frame_components"} or response.get("no_symmetry_projection") is not True:
            raise ValueError("Missing original response transformation declaration")
        expected = dict(response_auxiliary_finite_difference=(2e-4, 2e-5, True),
                        translation_response=(.001, .0002, True), eval_batch_response=(2e-4, 2e-5, True),
                        rotation_response_covariance=(.001, .0002, guarantee != "fixed_frame_components"))
        if guarantee == "fixed_frame_components":
            expected["rotation_fixed_frame_invariance"] = (.001, .0002, True)
        if guarantee == "O3_cartesian":
            expected["inversion_rank2_response"] = (.001, .0002, True)
    if set(physics["checks"]) != set(expected) or physics.get("geometry_tolerance") != dict(rtol=.001, atol=.0002):
        raise ValueError("Trained-best geometry check coverage/tolerances changed")
    for key, (rtol, atol, required_check) in expected.items():
        row = physics["checks"][key]
        if (row.get("rtol") != rtol or row.get("atol") != atol or row.get("required") is not required_check or
                type(row.get("max_abs_error")) not in (int, float) or not math.isfinite(row["max_abs_error"])):
            raise ValueError("Trained-best physical tolerances/observations changed")
    gradients = physics.get("mixed_parameter_gradient_norms", {})
    if not gradients or any(type(value) not in (int, float) or not math.isfinite(value) or value <= 1e-10
                            for value in gradients.values()):
        raise ValueError("Missing finite positive mixed parameter gradients")


def _new_report(output, kind, identifier):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status="running", stage="formal_training_validation", kind=kind, case_id=identifier,
                  slurm_job_id=os.environ["SLURM_JOB_ID"], device="cpu", formal_training_runs=0)
    def record(**values):
        report.update(values, updated_at=time.time())
        write_json(output / "report.json", report)
    record()
    return output, report, record


def postprocess_case(matrix, identifier, output):
    """Run unchanged trained-best physics and complete inference in a CPU Slurm job."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Predictive post-processing must run through Slurm")
    started = time.perf_counter()
    output, report, record = _new_report(output, "formal_predictive_postprocessing", identifier)
    try:
        context = formal_context(matrix, identifier)
        trained, gate = context["trained"], context["gate"]
        record(stage="saved_raw_label_rescore", git_commit=context["git_commit"],
               matrix_sha256=context["spec"]["matrix_sha256"], input_sha256=context["input_sha256"],
               physical_validator_sha256=validation_sources(),
               verified_training=context["verified_training"])
        rescore = rescore_saved(context["report_path"], output / "heldout")
        record(stage="trained_best_physics", raw_label_assessment_sha256=file_sha(output / "heldout/report.json"))
        if gate["case"]["task"] in {"forcefield", "dielectric"}:
            selection = physical_selection(context)
            physics = numerics.trained_physics(trained["best_checkpoint"], trained["config"], selection["indices"])
            write_json(output / "trained-best-physics.json", physics)
            verify_physics(physics, gate["case"]["task"], selection)
            record(physical_selection=selection, physical_report_sha256=file_sha(output / "trained-best-physics.json"))
        record(stage="complete_source_inference")
        predictions = output / "all-source-predictions.jsonl"
        if predictions.exists() or predictions.is_symlink():
            raise FileExistsError("Refusing to overwrite an existing inference output")
        inferred = numerics.complete_inference(trained["best_checkpoint"], trained["config"], predictions)
        if not inferred.get("streamed") or inferred.get("structure_count") != gate["source_structures"]:
            raise ValueError("Inference did not stream the complete original source")
        unchanged(context["input_sha256"])
        record(status="passed", stage="awaiting_independent_validation", metrics=rescore["metrics"],
               inference_path=str(predictions), inference_structures=gate["source_structures"],
               inference_prediction_sha256=file_sha(predictions), inference_prediction_bytes=predictions.stat().st_size,
               wall_seconds=time.perf_counter() - started,
               peak_process_rss_bytes=numerics.peak_rss_bytes(),
               independent_output_verified=False,
               scope="CPU trained-best post-processing; separate independent validation required. No training count or supervised stress accuracy")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error), wall_seconds=time.perf_counter() - started)
        raise


def verify_case(matrix, identifier, postprocessing, output):
    """Independent saved-output acceptance; tensor CPU softmax only, no GNN execution."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Independent prediction validation must run through Slurm")
    started = time.perf_counter()
    output, report, record = _new_report(output, "independent_formal_predictive_acceptance", identifier)
    try:
        with numerics.forbid_models():
            context = formal_context(matrix, identifier)
            parent_path = Path(postprocessing) / "report.json"
            parent_sha = file_sha(parent_path)
            parent = read_json(parent_path)
            if (parent.get("status") != "passed" or parent.get("stage") != "awaiting_independent_validation" or
                    parent.get("kind") != "formal_predictive_postprocessing" or parent.get("case_id") != identifier or
                    parent.get("matrix_sha256") != context["spec"]["matrix_sha256"] or
                    parent.get("input_sha256") != context["input_sha256"] or parent.get("device") != "cpu"):
                raise ValueError("Independent post-processing binding/status differs")
            compatible_sources([parent["git_commit"]])
            compare(validation_sources(), parent["physical_validator_sha256"], "physical_validator_source")
            compare(parent["verified_training"], context["verified_training"], "verified_training")
            rescored = rescore_saved(context["report_path"], output / "heldout")
            saved_rescore_path = Path(postprocessing) / "heldout/report.json"
            if file_sha(saved_rescore_path) != parent["raw_label_assessment_sha256"]:
                raise ValueError("Parent raw-label assessment bytes changed")
            compare(rescored, read_json(saved_rescore_path), "independent_rescore")
            compare(rescored["metrics"], parent["metrics"], "post_metrics")
            task = context["gate"]["case"]["task"]
            if task in {"forcefield", "dielectric"}:
                selection = physical_selection(context)
                compare(selection, parent["physical_selection"], "physical_selection")
                physics_path = Path(postprocessing) / "trained-best-physics.json"
                if file_sha(physics_path) != parent["physical_report_sha256"]:
                    raise ValueError("Trained-best physical evidence bytes changed")
                verify_physics(read_json(physics_path), task, selection)
            predictions = Path(postprocessing) / "all-source-predictions.jsonl"
            if Path(parent["inference_path"]).resolve() != predictions.resolve():
                raise ValueError("Inference path differs from the retained post-processing output")
            verified = verify_inference_stream(context["report_path"], predictions,
                expected_sha256=parent["inference_prediction_sha256"], expected_bytes=parent["inference_prediction_bytes"])
            if verified["structures"] != parent["inference_structures"]:
                raise ValueError("Parent complete inference population differs")
            unchanged(context["input_sha256"])
            if file_sha(parent_path) != parent_sha:
                raise ValueError("Post-processing report changed during independent validation")
        record(status="passed", stage="complete", git_commit=context["git_commit"],
               matrix_sha256=context["spec"]["matrix_sha256"], input_sha256=context["input_sha256"],
               parent_report_sha256=parent_sha, verified_training=context["verified_training"],
               metrics=rescored["metrics"], inference_verification=verified, model_execution_forbidden=True,
               wall_seconds=time.perf_counter() - started,
               scope="Independent full raw-label, trained-best physics binding and all-source output acceptance; no new training or supervised stress accuracy")
        return report
    except Exception as error:
        record(status="failed", error_type=type(error).__name__, error=str(error), wall_seconds=time.perf_counter() - started)
        raise
