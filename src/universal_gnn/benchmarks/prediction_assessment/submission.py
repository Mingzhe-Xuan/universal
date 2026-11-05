"""Attach CPU assessment to existing managed primary training receipts only."""

import copy
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

from ..execution.gates import case_spec, check_preparation, compatible_sources, file_sha, read_json
from ..execution.runner import duration_seconds
from ..experiments.registry import canonical_digest
from ..preflight import write_json
from ..submission.dispatch import MANAGED, ReceiptNotRetained, pair_lock, submit_stage, validate_submitted_job
from ..submission.planning import partition_maximum, request_script, slurm_duration


def campaign_scope():
    return read_json(Path(__file__).resolve().parents[4] / "configs/arxiv_v1_scope.json")


def source_identity(source, commit):
    if (subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != commit or
            subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()):
        raise ValueError("Original pinned training source changed")


def training_dependency(receipt, case):
    """Retained identities or complete original artifacts; never replace training."""
    try:
        fields = validate_submitted_job(receipt)
    except ReceiptNotRetained as error:
        from .runtime import formal_context
        matrix = read_json(receipt["assessment_matrix"])
        context = formal_context(matrix, case["id"])
        if (context["formal"]["slurm_job_id"] != receipt["job"] or
                context["formal"]["git_commit"] != receipt["git_commit"] or
                context["trained"]["execution"]["slurm"]["SLURM_JOB_ID"] != receipt["job"]):
            raise ValueError("Purged training receipt is not bound to the complete original artifacts")
        return dict(dependency=None, terminal_unavailable=str(error),
                    verified_training=context["verified_training"], input_sha256=context["input_sha256"])
    resources = receipt["resources"]
    if (fields.get("WorkDir") != receipt["source_checkout"] or fields.get("Partition") != resources["partition"] or
            fields.get("NumCPUs") != str(resources["cpus_per_task"]) or
            fields.get("MinMemoryNode") != str(resources["memory_gib"]) + "G" or
            duration_seconds(fields["TimeLimit"]) != resources["budget_seconds"] or
            fields.get("TresPerNode") != "gres:gpu:1"):
        raise ValueError("Actual training allocation differs from the retained request")
    if fields["JobState"] == "COMPLETED" and fields.get("ExitCode") != "0:0":
        raise ValueError("Original training did not finish successfully")
    return dict(dependency="afterok:" + receipt["job"], retained_slurm=fields)


def checked_training_receipts(matrix, pair_id, *, matrix_path, dispatch_job):
    """Rebuild original scripts and both full gates while preserving their source."""
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Predictive assessment dispatch requires Slurm")
    spec = case_spec(matrix, pair_id + "--pretrained")
    cases = [c for c in matrix["cases"] if c["pair_id"] == pair_id]
    cases.sort(key=lambda case: case["initialization"] != "pretrained")
    scope = campaign_scope()
    if (len(cases) != 2 or spec["case"]["task"] not in {"bandgap", "classification", "dielectric", "spectrum"} or
            scope["base_matrix_sha256"] != spec["matrix_sha256"] or scope["training_seeds"] != [123] or
            any(c["seed"] != 123 or c["id"] not in scope["active_case_ids"] for c in cases)):
        raise ValueError("Select one of the16 active nonforce predictive pairs")
    if Path(sys.prefix).name != cases[0]["python_environment"]:
        raise ValueError("Use the original provider Python environment")
    matrix_path = Path(matrix_path).resolve()
    if canonical_digest(read_json(matrix_path)) != spec["matrix_sha256"]:
        raise ValueError("On-disk original matrix changed")
    if not isinstance(dispatch_job, str) or not re.fullmatch(r"[1-9][0-9]*", dispatch_job):
        raise ValueError("Bind the successful original pair-gate Slurm ID")
    root = Path("runs/arxiv-v1/dispatch") / pair_id
    latest, identity = read_json(root / "latest.json"), read_json(root / "provenance.json")
    attempt = root / "attempts" / dispatch_job
    if (latest.get("status") != "submitted" or latest.get("parent_slurm_job") != dispatch_job or
            Path(latest["attempt"]).resolve() != attempt.resolve() or
            {k: v for k, v in latest.items() if k != "attempt"} != read_json(attempt / "report.json")):
        raise ValueError("Original dispatch did not finish for this exact pair gate")
    original = read_json(attempt / "plan.json")
    if (original.get("status") != "checked" or original.get("kind") != "formal_pair_submission_plan" or
            original.get("pair_id") != pair_id or original.get("cases") != cases or
            original.get("fingerprint") != canonical_digest(original["provenance"]) or
            identity != dict(fingerprint=original["fingerprint"], provenance=original["provenance"]) or
            latest["fingerprint"] != original["fingerprint"] or
            original["provenance"]["matrix_sha256"] != spec["matrix_sha256"] or
            original["provenance"]["stages"] != [{k: v for k, v in s.items() if k != "script"} for s in original["stages"]]):
        raise ValueError("Original source/recipe/stage provenance differs")
    old_commit = original["provenance"]["git_commit"]
    commit = compatible_sources([old_commit])
    source_identity((Path("runs/source-checkouts") / old_commit).resolve(), old_commit)
    if original["provenance"]["python"] != str(Path(sys.executable).absolute()):
        raise ValueError("Original training used another provider interpreter")
    keys = {case["id"] + ":train" for case in cases}
    if set(latest["jobs"]) != keys or len(original["stages"]) != 2:
        raise ValueError("Require exactly the two original predictive train receipts")
    receipts, dependencies = {}, {}
    for case, item in zip(cases, original["stages"]):
        mode, identifier = case["initialization"], case["id"]
        gate = original["gates"][mode]
        if (item.get("key") != identifier + ":train" or item.get("case_id") != identifier or
                item.get("phase") != "train" or item.get("depends_on") is not None or
                gate["git_commit"] != old_commit or item["resources"]["gpus"] != 1 or
                item["resources"]["budget_seconds"] != gate["budget_seconds"] or
                original["provenance"]["configs"][mode] != canonical_digest(gate["config"])):
            raise ValueError("Original training stage/config/source differs")
        current = check_preparation(matrix, identifier, gate["preparation"], budget_seconds=gate["budget_seconds"])
        if (current["git_commit"] != commit or
                {k: v for k, v in current.items() if k != "git_commit"} != {k: v for k, v in gate.items() if k != "git_commit"}):
            raise ValueError("Full preparation evidence changed since original submission")
        directory = Path("runs/arxiv-v1/launches") / identifier
        intent, receipt = read_json(directory / "submission-intent.json"), read_json(directory / "launch.json")
        source = Path(receipt["source_checkout"]).resolve()
        if source != (Path("runs/source-checkouts") / old_commit).resolve():
            raise ValueError("Original training source is outside the pinned task cache")
        args = [original["provenance"]["python"], "scripts/run_formal_case.py", str(matrix_path),
                "--matrix-sha256", spec["matrix_sha256"], "--case", identifier,
                "--preparation", gate["preparation"], "--budget-seconds", str(gate["budget_seconds"])]
        expected_script = request_script(args, repository=source)
        if (expected_script != item["script"] or file_sha(directory / "request.sh") != item["request_sha256"] or
                hashlib.sha256(expected_script.encode()).hexdigest() != item["request_sha256"]):
            raise ValueError("Retained training script differs from its frozen arguments")
        expected = dict(managed_by=MANAGED, fingerprint=original["fingerprint"], key=item["key"],
                        case_id=identifier, phase="train", dependency=None, request_sha256=item["request_sha256"],
                        resources=item["resources"], git_commit=old_commit, source_checkout=str(source))
        reported = copy.deepcopy(latest["jobs"][item["key"]])
        if type(reported.pop("reused", None)) is not bool:
            raise ValueError("Original dispatch lacks its receipt-reuse record")
        if (reported != receipt or any(intent.get(k) != v or receipt.get(k) != v for k, v in expected.items()) or
                intent.get("state") != "submitted" or receipt.get("state") != "submitted" or
                intent.get("parent_slurm_job") != dispatch_job or receipt.get("parent_slurm_job") != dispatch_job or
                intent.get("submission_token") != receipt.get("submission_token") or
                not re.fullmatch(r"ugnn-[0-9a-f]{32}", receipt.get("submission_token", "")) or
                not re.fullmatch(r"[1-9][0-9]*", receipt.get("job", "")) or
                Path(receipt["request_path"]).resolve() != (directory / "request.sh").resolve()):
            raise ValueError("Original managed training intent/receipt/token differs")
        decorated = dict(receipt, assessment_matrix=str(matrix_path))
        dependencies[identifier] = training_dependency(decorated, case)
        receipts[item["key"]] = receipt
    return dict(cases=cases, receipts=receipts, dependencies=dependencies, git_commit=commit,
                matrix_path=str(matrix_path), matrix_sha256=spec["matrix_sha256"],
                original_dispatch_job=dispatch_job, original_fingerprint=original["fingerprint"])


def build_post_plan(matrix, pair_id, *, matrix_path, dispatch_job, post_seconds=259200, verify_seconds=14400):
    checked = checked_training_receipts(matrix, pair_id, matrix_path=matrix_path, dispatch_job=dispatch_job)
    maximum = partition_maximum()
    for value in (post_seconds, verify_seconds):
        if type(value) is not int or value <= 0 or maximum is not None and value > maximum:
            raise ValueError("Declare finite positive CPU budgets within the partition maximum")
    stages = []
    for case in checked["cases"]:
        identifier = case["id"]
        parent = "runs/arxiv-v1/prediction-postprocessing/" + identifier + "-" + checked["git_commit"][:7] + "-attempt-001"
        output = "runs/arxiv-v1/prediction-acceptance/" + identifier + "-" + checked["git_commit"][:7] + "-attempt-001"
        old_post = Path("runs/arxiv-v1/launches") / identifier / "post" / "launch.json"
        if checked["dependencies"][identifier]["dependency"] is None and old_post.is_file():
            dependency = read_json(old_post).get("dependency")
            if dependency not in (None, "afterok:" + checked["receipts"][identifier + ":train"]["job"]):
                raise ValueError("Existing post receipt depends on another training run")
            checked["dependencies"][identifier]["dependency"] = dependency
        common = [sys.executable, "scripts/assess_prediction.py"]
        options = ["--matrix", checked["matrix_path"], "--matrix-sha256", checked["matrix_sha256"], "--case", identifier]
        for phase, seconds, destination in (("post", post_seconds, parent), ("verify", verify_seconds, output)):
            args = common + [phase] + options + (["--postprocessing", parent] if phase == "verify" else []) + ["--output", destination]
            script = request_script(args, cpu_only=True)
            dependency = identifier + (":post" if phase == "verify" else ":train")
            if phase == "post" and checked["dependencies"][identifier]["dependency"] is None:
                dependency = None
            stages.append(dict(key=identifier + ":" + phase, case_id=identifier, phase=phase,
                depends_on=dependency, script=script, request_sha256=hashlib.sha256(script.encode()).hexdigest(),
                output=destination, resources=dict(partition="compute", node="node42", gpus=0,
                    cpus_per_task=2 if phase == "post" else 1, memory_gib=32 if phase == "post" else 8,
                    time=slurm_duration(seconds), budget_seconds=seconds)))
    provenance = dict(git_commit=checked["git_commit"], matrix_sha256=checked["matrix_sha256"], pair_id=pair_id,
        original_dispatch_job=dispatch_job, original_fingerprint=checked["original_fingerprint"],
        original_receipts=checked["receipts"], training_dependencies={identifier: row["dependency"]
            for identifier, row in checked["dependencies"].items()},
        stages=[{k: v for k, v in s.items() if k != "script"} for s in stages])
    return dict(status="checked", kind="predictive_post_submission_plan", cases=checked["cases"],
                pair_id=pair_id, provenance=provenance, fingerprint=canonical_digest(provenance), stages=stages,
                training_receipts=checked["receipts"], formal_training_runs_submitted=0,
                training_observations=checked["dependencies"],
                interpretation="CPU post/independent verification only; finite initial budgets are not measured runtime guarantees")


def dispatch_post_pair(matrix, pair_id, **options):
    plan = build_post_plan(matrix, pair_id, **options)
    root = Path("runs/arxiv-v1/prediction-dispatch") / pair_id
    root.mkdir(parents=True, exist_ok=True)
    with pair_lock(root):
        identity = root / "provenance.json"
        if identity.exists() and read_json(identity).get("fingerprint") != plan["fingerprint"]:
            raise ValueError("Existing post-dispatch provenance differs; preserve it")
        write_json(identity, dict(fingerprint=plan["fingerprint"], provenance=plan["provenance"]))
        attempt = root / "attempts" / os.environ["SLURM_JOB_ID"]
        attempt.mkdir(parents=True, exist_ok=False)
        write_json(attempt / "plan.json", plan)
        report = dict(status="dispatching", pair_id=pair_id, fingerprint=plan["fingerprint"], jobs={},
                      parent_slurm_job=os.environ["SLURM_JOB_ID"], formal_training_runs_submitted=0)
        all_jobs = dict(plan["training_receipts"])
        try:
            for item in plan["stages"]:
                claim = Path("runs/arxiv-v1/launches") / item["case_id"] / item["phase"]
                if not claim.exists() and (Path(item["output"]).exists() or Path(item["output"]).is_symlink()):
                    raise FileExistsError("Unclaimed post-processing output already exists")
                receipt = submit_stage(plan, item, all_jobs)
                all_jobs[item["key"]] = receipt
                report["jobs"][item["key"]] = receipt
                write_json(attempt / "report.json", report)
            report.update(status="submitted", postprocessing_jobs=4,
                          newly_submitted_cpu_jobs=sum(not r["reused"] for r in report["jobs"].values()))
            write_json(attempt / "report.json", report)
            write_json(root / "latest.json", dict(attempt=str(attempt), **report))
            return report
        except Exception as error:
            report.update(status="submission_failed", error_type=type(error).__name__, error=str(error))
            write_json(attempt / "report.json", report)
            raise
