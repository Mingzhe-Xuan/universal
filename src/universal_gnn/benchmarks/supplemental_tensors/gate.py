"""Independent full rank3/4 preparation evidence; no models or job submission."""

import copy
import getpass
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

from ..execution.gates import _check_prepared_spec, file_sha, read_json
from ..prediction_assessment.contracts import compare, finite_shape
from ..preparation.specification import physical_indices
from .experiments import build_tensor_definitions, inspect_tensor_inputs

DEFINITION_PATH = "runs/tensor-definition-control-1231/definitions/definitions.json"
DEFINITION_SHA = "c7492a3991444e3454544da08cae01787920d289a2f506aab8dcb1059c081624"
PRIMARY_PATH = "runs/arxiv-v1/definition-947/matrix.json"
CLAIM_ROOT = "runs/full-rank34-preparations-90a5836-claim"


def tensor_case_spec(primary, definitions, identifier):
    expected = build_tensor_definitions(primary)
    declared = copy.deepcopy(definitions)
    audit = declared.pop("full_input_audit", None)
    if declared != expected or not isinstance(audit, dict):
        raise ValueError("Require all sixteen original supplemental tensor definitions")
    cases = [c for c in expected["cases"] if c["id"] == identifier]
    if len(cases) != 1:
        raise ValueError("Select exactly one registered seed123 supplemental tensor case")
    case = cases[0]
    configs = {c["initialization"]: c["config"] for c in expected["cases"] if c["pair_id"] == case["pair_id"]}
    return dict(case=case, configs=configs, counts=case["counts"], source_structures=case["source_structures"],
                matrix_sha256=DEFINITION_SHA, definition_kind=expected["kind"])


def checked_tensor_physics(value, case, identifiers, *, device="cuda"):
    rank = len(case["tensor_shape"])
    guarantee = "O3_cartesian" if case["model"] in {"mace", "nequip"} else "fixed_frame_components"
    response = value.get("response", {})
    if (value.get("passed") is not True or value.get("dtype") != "torch.float32" or
            not ((device == "cuda" and str(value.get("device", "")).startswith("cuda")) or
                 (device == "cpu" and value.get("device") == "cpu")) or value.get("structure_ids") != identifiers or
            response.get("guarantee") != guarantee or response.get("rank") != rank or
            response.get("shape") != case["tensor_shape"] or response.get("inversion_parity") != (-1)**rank or
            response.get("no_symmetry_projection") is not True):
        raise ValueError("Higher-tensor device/output/geometry declaration differs")
    for key in ("analytic", "numeric"):
        finite_shape(response.get(key), (1, *case["tensor_shape"]))
    compare(response["analytic"], response["numeric"], "auxiliary_derivative", rtol=2e-4, atol=2e-5)
    expected = dict(response_auxiliary_finite_difference=(2e-4, 2e-5, True),
                    translation_response=(.001, .0002, True), eval_batch_response=(2e-4, 2e-5, True),
                    rotation_response_covariance=(.001, .0002, guarantee == "O3_cartesian"))
    if guarantee == "O3_cartesian":
        expected["inversion_rank" + str(rank) + "_response"] = (.001, .0002, True)
    else:
        expected["rotation_fixed_frame_invariance"] = (.001, .0002, True)
    if (set(value.get("checks", {})) != set(expected) or
            value.get("geometry_tolerance") != dict(rtol=.001, atol=.0002)):
        raise ValueError("Higher-tensor geometry check coverage changed")
    for key, (rtol, atol, required) in expected.items():
        row = value["checks"][key]
        if (row.get("rtol") != rtol or row.get("atol") != atol or row.get("required") is not required or
                (required and row.get("passed") is not True) or type(row.get("passed")) is not bool or
                type(row.get("max_abs_error")) not in (int, float) or
                not math.isfinite(row["max_abs_error"]) or row["max_abs_error"] < 0):
            raise ValueError("Higher-tensor physical tolerance/result changed")
    gradients = value.get("mixed_parameter_gradient_norms", {})
    if (set(gradients) != {"backbone", "readout"} or
            any(type(v) not in (int, float) or not math.isfinite(v) or v <= 1e-10 for v in gradients.values())):
        raise ValueError("Both trained components require finite nonzero mixed gradients")


def checked_preparation_receipt(case, preparation, prepared, receipt_path):
    receipt_path = Path(receipt_path)
    receipt = read_json(receipt_path)
    request = receipt_path.parent / "request.sh"
    terminal = read_json(receipt_path.parent / "terminal.json")
    output = "runs/arxiv-v1/full-rank34-preparation-" + str(receipt.get("job")) + "-" + case["task"] + "-" + case["model"]
    if (receipt.get("state") != "submitted" or receipt.get("formal_training_runs") != 0 or
            not re.fullmatch(r"[1-9][0-9]*", str(receipt.get("job", ""))) or
            receipt.get("pair") != case["pair_id"] or receipt.get("model") != case["model"] or
            receipt.get("task") != case["task"] or receipt.get("seed") != 123 or
            receipt.get("definition_control_job") != "1231" or receipt.get("definition_sha256") != DEFINITION_SHA or
            receipt.get("output") != output or Path(output).resolve() != Path(preparation).resolve() or
            Path(receipt.get("request_path", "")).resolve() != request.resolve() or
            file_sha(request) != receipt.get("request_sha256") or
            prepared.get("request_sha256") != receipt["request_sha256"] or
            prepared.get("slurm_job_id") != receipt.get("job") or
            prepared.get("git_commit") != receipt.get("git_commit")):
        raise ValueError("Supplemental preparation request/case/source binding differs")
    argv = receipt.get("sbatch_argv", [])
    flags = {part.split("=", 1)[0]: part.split("=", 1)[1] for part in argv if "=" in part}
    required = {"--partition": "compute", "--nodelist": "node42", "--gres": "gpu:1", "--cpus-per-task": "2",
                "--mem": "64G", "--time": "16:00:00", "--nice": "1000",
                "--chdir": receipt.get("source_checkout"),
                "--job-name": "ugnn-rank34-prep-" + case["task"] + "--" + case["model"]}
    if not argv or argv[0] != "sbatch" or "--no-requeue" not in argv or any(flags.get(k) != v for k, v in required.items()):
        raise ValueError("Supplemental preparation resource/request profile differs")
    if (terminal.get("entry") != receipt or terminal.get("exit") != 0 or
            terminal.get("request_sha256") != receipt["request_sha256"] or
            terminal.get("report_sha256") != file_sha(Path(preparation) / "report.json")):
        raise ValueError("Missing exact retained preparation terminal/report/request proof")
    fields = dict(t.split("=", 1) for t in shlex.split(terminal.get("raw", "")) if "=" in t)
    if (fields != terminal.get("fields") or fields.get("JobId") != receipt["job"] or
            fields.get("UserId", "").split("(")[0] != getpass.getuser() or
            fields.get("JobName") != required["--job-name"] or fields.get("WorkDir") != receipt["source_checkout"] or
            fields.get("JobState") != "COMPLETED" or fields.get("ExitCode") != "0:0" or
            fields.get("Requeue") != "0" or fields.get("NumCPUs") != "2" or
            fields.get("MinMemoryNode") != "64G" or fields.get("TimeLimit") != "16:00:00" or fields.get("Nice") != "1000"):
        raise ValueError("Retained preparation Slurm owner/state/source/resources differ")
    cache = receipt["source_checkout"]
    if (subprocess.check_output(["git", "-C", cache, "rev-parse", "HEAD"], text=True).strip() != receipt["git_commit"] or
            subprocess.check_output(["git", "-C", cache, "status", "--porcelain", "--untracked-files=no"], text=True).strip()):
        raise ValueError("Original preparation source cache is not clean and pinned")
    return dict(receipt=str(receipt_path), receipt_sha256=file_sha(receipt_path),
                terminal_sha256=file_sha(receipt_path.parent / "terminal.json"),
                request_sha256=receipt["request_sha256"], slurm_job_id=receipt["job"])


def checked_preparation_origin(prepared, case):
    allocation = prepared.get("allocation", {})
    parity = prepared.get("native_parity", {})
    errors = {"max_feature_error", "max_energy_error"} if case["model"] == "mace" else (
        {"max_feature_error", "max_energy_error", "max_force_error"} if case["model"] == "nequip" else
        {"max_feature_error", "max_prediction_error"})
    if (prepared.get("cuda_acceptance") is not True or prepared.get("formal_training_runs") != 0 or
            prepared.get("formal_training_launched") is not False or
            type(allocation.get("gpus")) is not int or allocation["gpus"] != 1 or allocation.get("node_list") != "node42" or
            allocation.get("evidence") not in {"AllocTRES", "TRES", "running_nodes_and_TresPerNode"} or
            parity.get("structures") != 2 or not isinstance(parity.get("reference"), str) or not parity["reference"] or
            set(parity) != {"structures", "reference", *errors} or
            any(type(parity[key]) not in (int, float) or not math.isfinite(parity[key]) or parity[key] < 0 for key in errors)):
        raise ValueError("Missing actual GPU allocation and two original-package parity observations")


def check_tensor_preparation(definitions_path, identifier, preparation, *, budget_seconds,
                             primary_path=PRIMARY_PATH, receipt_path=None):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Independent full tensor preparation checks must run through Slurm")
    if file_sha(definitions_path) != DEFINITION_SHA:
        raise ValueError("Original accepted sixteen-case definition bytes changed")
    primary, definitions = read_json(primary_path), read_json(definitions_path)
    spec = tensor_case_spec(primary, definitions, identifier)
    case = spec["case"]
    if Path(sys.prefix).name != case["python_environment"]:
        raise ValueError("Use the original provider Python environment")
    prepared = read_json(Path(preparation) / "report.json")
    if (prepared.get("status") != "passed" or prepared.get("stage") != "complete" or
            prepared.get("independent_full_gate_pending") is not True):
        raise ValueError("Wait for complete original supplemental preparation; it never self-certifies this gate")
    checked_preparation_origin(prepared, case)
    receipt_path = Path(receipt_path) if receipt_path is not None else Path(CLAIM_ROOT) / case["pair_id"] / "job.json"
    receipt = checked_preparation_receipt(case, preparation, prepared, receipt_path)
    compare(definitions["full_input_audit"], inspect_tensor_inputs(), "complete_tensor_input_audit")
    result = _check_prepared_spec(primary, spec, preparation, budget_seconds=budget_seconds)
    probe = read_json(Path(preparation) / "graph-scan/probe.json")
    if (probe.get("warmup_batches") != case["preflight"]["warmup_batches"] or
            probe.get("measure_batches") != case["preflight"]["measure_batches"]):
        raise ValueError("Higher-tensor capacity schedule differs from its frozen two/100 batches")
    indices = physical_indices(probe, case["counts"]["train"])
    manifest = read_json(case["config"]["dataset"]["split_manifest"])
    identifiers = [manifest["records"][manifest["partitions"]["train"][i]]["id"] for i in indices]
    if prepared.get("physical_training_indices") != indices or prepared.get("physical_structure_ids") != identifiers:
        raise ValueError("Original CUDA physics did not use the complete scan's worst two structures")
    for mode in ("pretrained", "scratch"):
        path = Path(preparation) / ("derivatives-" + mode + ".json")
        checked_tensor_physics(read_json(path), case, identifiers)
        if prepared.get("physical_evidence_sha256", {}).get(mode) != file_sha(path):
            raise ValueError("Original preparation physical report hash differs")
    names = ("cartesian.py", "derivatives.py", "finite_difference.py", "precision.py")
    validators = {"src/universal_gnn/benchmarks/validation/" + name:
                  file_sha("src/universal_gnn/benchmarks/validation/" + name) for name in names}
    compare(prepared.get("source_sha256"), validators, "accepted_higher_tensor_validator_source")
    estimate = prepared.get("resource_estimate", {}).get("train_only_300_epoch_seconds")
    if type(estimate) not in (int, float) or not math.isclose(estimate, result["probed_train_only_seconds"], rel_tol=1e-14):
        raise ValueError("Preparation training estimate differs from independently checked workers")
    return dict(result, kind="independent_supplemental_tensor_execution_gate", definition_sha256=DEFINITION_SHA,
                definition_kind=definitions["kind"], preparation_receipt=receipt,
                physical_training_indices=indices, physical_structure_ids=identifiers,
                validator_sha256=validators, formal_training_runs=0,
                interpretation="Independent complete source/original graphs/paired CUDA capacity/calibration/official artifacts/versions/worst-two rank3/4 physical and retained terminal gate. No training launched.")
