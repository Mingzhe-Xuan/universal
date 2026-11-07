"""Export exact frozen definitions and split metadata without model execution."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

from .recipes import validate_registry
from .registry import DATASETS, canonical_digest, inspect_registry

MATRIX_SHA = "b792524e098298500c75785eaf06051824f66d27cfcbae794bb55f5cfe1a2651"
SCOPE_SHA = "9b33ab3f987bd9476c24711b7e0adc39cb4abfee666840fe086c6aea31837ea7"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_name(name):
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name
            or any(c in name for c in "\x00\r\n\t") or PurePosixPath(name).is_absolute()
            or PurePosixPath(name).as_posix() != name or any(part in {".", "..", ".git"} for part in name.split("/"))):
        raise ValueError("Archive/input paths must be canonical relative paths")
    return name


def checked_definitions(matrix_raw, scope_raw):
    matrix, scope = json.loads(matrix_raw), json.loads(scope_raw)
    if canonical_digest(matrix) != MATRIX_SHA or sha(scope_raw) != SCOPE_SHA or scope.get("base_matrix_sha256") != MATRIX_SHA:
        raise ValueError("Require the unchanged frozen947 matrix and single-seed scope")
    if (matrix.get("definition_revision") != 2 or matrix.get("seeds") != [123, 456, 789]
            or matrix.get("expected_training_runs") != 144 or len(matrix.get("cases", [])) != 144):
        raise ValueError("Preserve the original144 definitions as provenance")
    validate_registry(matrix["registry"])
    if canonical_digest(matrix["registry"]) != matrix.get("registry_sha256"):
        raise ValueError("Frozen registry identity differs")
    cases = {row["id"]: row for row in matrix["cases"]}
    active, excluded = scope.get("active_case_ids", []), scope.get("excluded_case_ids", [])
    if (len(cases) != 144 or len(active) != len(set(active)) or len(active) != 48
            or len(excluded) != len(set(excluded)) or len(excluded) != 96
            or set(active) & set(excluded) or set(active) | set(excluded) != set(cases)
            or scope.get("training_seeds") != [123] or scope.get("expected_training_runs") != 48):
        raise ValueError("Require exactly48 active and96 excluded historical IDs")
    for row in matrix["cases"]:
        safe_name(row["config_path"])
        if canonical_digest(row["config"]) != row["config_sha256"]:
            raise ValueError("Definition configuration digest differs")
    for identifier in active:
        row = cases[identifier]
        config = row["config"]
        if (row["seed"] != 123 or config["seed"] != 123 or config["structures"] != "all"
                or config["max_atoms"] is not None or config["dtype"] != "float32"
                or config["epochs"] != 300 or config["evaluation"] != {"patience": 30, "min_delta": 0.0}):
            raise ValueError("Active definitions must retain the full single-seed baseline recipe")
    return matrix, scope, [cases[identifier] for identifier in active]


def write_payload_archive(path, payloads):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError("Refusing to overwrite a frozen input archive")
    if not payloads:
        raise ValueError("Refusing an empty archive")
    for name, body in payloads.items():
        safe_name(name)
        if not isinstance(body, bytes):
            raise TypeError("Archive payloads must preserve explicit bytes")
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(payloads):
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, payloads[name])


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [safe_name(info.filename) for info in infos]
        if len(names) != len(set(names)) or sum(info.file_size for info in infos) > 256 * 1024**2:
            raise ValueError("Duplicate members or an unexpectedly large metadata bundle")
        if any((info.external_attr >> 16) & 0o170000 != 0o100000 for info in infos):
            raise ValueError("Only regular archive members are supported")
        manifest = json.loads(archive.read("manifest.json"))
        if set(names) != {"manifest.json", *manifest["members"]}:
            raise ValueError("Manifest and complete archive membership differ")
        for name, expected in manifest["members"].items():
            body = archive.read(name)
            if len(body) != expected["bytes"] or sha(body) != expected["sha256"]:
                raise ValueError("Changed frozen input archive member: " + name)
        matrix, scope, active = checked_definitions(archive.read("matrix.json"), archive.read("scope.json"))
        if manifest["active_case_ids"] != scope["active_case_ids"] or len(active) != 48:
            raise ValueError("Archive active-case inventory differs")
        required = {"matrix.json", "scope.json", "registry.json", "README.md", "manifest.json",
            "models/official/cgcnn/atom_init.json", "models/official/nequip/NequIP-OAM-S_pretrain_config.yaml"}
        required.update(row["config_path"] for row in active)
        required.update("data/arxiv-v1/" + name + "/" + filename for name in DATASETS
            for filename in ["split.json", "audit.json", "exclusions.jsonl"])
        allowed = required | {"data/downloads/arxiv-matrix-raw/download-receipt.json"}
        if (not required.issubset(names) or not set(names).issubset(allowed)
                or json.loads(archive.read("registry.json")) != matrix["registry"]
                or manifest.get("kind") != "arxiv_v1_frozen_inputs_only" or manifest.get("definition_configs") != 48
                or manifest.get("dataset_count") != 5 or manifest.get("scientific_acceptance") is not False
                or manifest.get("preflight_still_required") is not True
                or manifest.get("structures_and_learned_weights_included") is not False):
            raise ValueError("Incomplete metadata bundle or an unsupported readiness claim")
        for case in active:
            if canonical_digest(json.loads(archive.read(case["config_path"]))) != case["config_sha256"]:
                raise ValueError("Archived configuration differs from its frozen definition")
    return manifest


def export_inputs(repository, matrix_path, scope_path, output):
    if not re.fullmatch(r"[1-9][0-9]*", os.environ.get("SLURM_JOB_ID", "")):
        raise RuntimeError("Full input scanning and export require CPU Slurm")
    repository, matrix_path, scope_path, output = map(Path, [repository, matrix_path, scope_path, output])
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite a frozen input export")
    matrix_raw, scope_raw = matrix_path.read_bytes(), scope_path.read_bytes()
    matrix, scope, active = checked_definitions(matrix_raw, scope_raw)
    actual = inspect_registry(repository)
    if actual != matrix["registry"]:
        raise ValueError("Current full source/split/artifacts differ from the frozen registry")
    source_repository = Path(__file__).resolve().parents[4]
    commit = subprocess.check_output(["git", "-C", str(source_repository), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(source_repository), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise ValueError("Export from a clean committed source checkout")
    payloads = {"matrix.json": matrix_raw, "scope.json": scope_raw,
        "registry.json": (json.dumps(actual, indent=2, allow_nan=False) + "\n").encode("utf8")}
    original_files = {matrix_path: sha(matrix_raw), scope_path: sha(scope_raw)}
    def copy(path, name):
        safe_name(name)
        if name in payloads or path.is_symlink():
            raise ValueError("Duplicate member or symlink input")
        body = path.read_bytes()
        payloads[name] = body
        original_files[path] = sha(body)
    for case in active:
        path = matrix_path.parent / case["config_path"]
        if not path.resolve().is_relative_to(matrix_path.parent.resolve()):
            raise ValueError("Configuration escapes the frozen definition directory")
        copy(path, case["config_path"])
        if canonical_digest(json.loads(payloads[case["config_path"]])) != case["config_sha256"]:
            raise ValueError("Original saved configuration differs from the matrix")
    for name in DATASETS:
        for filename in ["split.json", "audit.json", "exclusions.jsonl"]:
            relative = "data/arxiv-v1/" + name + "/" + filename
            copy(repository / relative, relative)
    for relative in ["cgcnn/atom_init.json", "nequip/NequIP-OAM-S_pretrain_config.yaml"]:
        copy(repository / "models/official" / relative, "models/official/" + relative)
    receipt = "data/downloads/arxiv-matrix-raw/download-receipt.json"
    if (repository / receipt).is_file():
        copy(repository / receipt, receipt)
    payloads["README.md"] = (
        "# Frozen arXiv v1 input definitions\n\n"
        "48 active seed123 definitions; the unchanged144-case matrix retains provenance. "
        "The96 excluded definitions are historical and must not be scheduled.\n\n"
        "These are baseline definition configs, not final capacity-resolved or trained configurations. "
        "Follow the repository's full original-model, graph/capacity and train-only-statistics preparation before training. "
        "Do not bypass gates or interpret this archive as completed experiments.\n\n"
        "The complete released split IDs, preparation audits and exclusions retain their exact bytes. "
        "Structure JSONL and learned weights are external inputs: obtain/prepare the exact sources "
        "and checksums in registry.json and the source audits; nonlearned CGCNN element descriptors "
        "and the NequIP author blueprint are included. No dataset/weight pickle is loaded by this exporter.\n\n"
        "Training uses seed123; generation's sampling RNG456 is evaluation-only. "
        "No performance, clean-pretraining-overlap or DFT-stability claim is implied.\n"
    ).encode("utf8")
    manifest = dict(version=1, kind="arxiv_v1_frozen_inputs_only", active_case_ids=scope["active_case_ids"],
        training_seeds=[123], definition_configs=48, historical_matrix_cases=144, excluded_case_count=96,
        matrix_canonical_sha256=MATRIX_SHA, scope_file_sha256=SCOPE_SHA,
        source_commit=commit, slurm_job_id=os.environ["SLURM_JOB_ID"],
        source_records=sum(entry["structures"] for entry in actual["datasets"].values()),
        dataset_count=5, artifact_sources=actual["artifacts"],
        structures_and_learned_weights_included=False, preflight_still_required=True, scientific_acceptance=False,
        members={name: dict(bytes=len(body), sha256=sha(body)) for name, body in sorted(payloads.items())})
    payloads["manifest.json"] = (json.dumps(manifest, indent=2, allow_nan=False) + "\n").encode("utf8")
    for path, expected in original_files.items():
        if sha(path.read_bytes()) != expected:
            raise ValueError("Input changed during read-only export")
    output.mkdir(parents=True, exist_ok=False)
    target = output / "frozen-inputs.zip"
    write_payload_archive(target, payloads)
    if verify_archive(target) != manifest:
        raise ValueError("Independent archive readback differs")
    if inspect_registry(repository) != actual:
        raise ValueError("Full source/split/artifact registry changed during export")
    receipt = dict(status="passed", kind="frozen_inputs_archive_export", archive=target.name,
        archive_bytes=target.stat().st_size, archive_sha256=sha(target.read_bytes()),
        archive_members=len(payloads), source_commit=commit, source_records=manifest["source_records"],
        definition_configs=48, scientific_acceptance=False, preflight_still_required=True,
        input_sha256={str(path): value for path, value in original_files.items()})
    (output / "report.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf8")
    return receipt
