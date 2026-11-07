"""Read regular Git blobs and export an auditable, disjoint source inventory."""

import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from .manifest import GROUPS, POLICY

FIELDS = ("files", "bytes", "physical_lines", "nonblank_lines", "python_statement_nodes")


def git(repository, *arguments, input=None):
    return subprocess.run(["git", "-C", str(repository), *arguments], input=input,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def safe_path(name):
    if (not isinstance(name, str) or not name or "\\" in name or re.match(r"[A-Za-z]:", name) or any(c in name for c in "\x00\r\n\t")
            or PurePosixPath(name).is_absolute() or PurePosixPath(name).as_posix() != name
            or any(part in {".", "..", ".git"} for part in name.split("/"))):
        raise ValueError("Require canonical relative Git paths without traversal or control characters")
    return name


def parse_tree(raw):
    entries = {}
    for record in raw.split(b"\x00"):
        if not record:
            continue
        header, encoded = record.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        name = safe_path(encoded.decode("utf8"))
        if name in entries or not re.fullmatch(r"[0-9a-f]{40}", oid):
            raise ValueError("Duplicate path or invalid Git object identity")
        entries[name] = dict(mode=mode, kind=kind, git_blob=oid)
    return entries


def select(entries, groups):
    selected = {}
    if not groups:
        raise ValueError("Declare at least one source group")
    for group, selectors in groups.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", group) or not selectors or isinstance(selectors, str):
            raise ValueError("Groups require a stable name and nonempty selector sequence")
        for selector in selectors:
            directory = selector.endswith("/")
            base = safe_path(selector[:-1] if directory else selector)
            matches = []
            for name, entry in entries.items():
                inside = name == base or (directory and name.startswith(base + "/"))
                if not inside:
                    continue
                if entry["mode"] not in {"100644", "100755"} or entry["kind"] != "blob":
                    raise ValueError("Selected boundaries cannot hide symlinks or submodules")
                if directory and not name.endswith(".py"):
                    continue
                if Path(name).suffix not in {".py", ".json", ".yaml", ".yml"}:
                    raise ValueError("Only Python and explicitly named configuration files are counted")
                if name in selected:
                    raise ValueError("Overlapping selectors/groups would double count a path")
                matches.append(name)
                selected[name] = dict(group=group, **entry)
            if not matches:
                raise ValueError("Every declared selector must match tracked source: " + selector)
    return dict(sorted(selected.items()))


def parse_blobs(raw, objects):
    cursor, result = 0, {}
    for expected in objects:
        stop = raw.index(b"\n", cursor)
        oid, kind, encoded_size = raw[cursor:stop].decode("ascii").split()
        size = int(encoded_size)
        if oid != expected or kind != "blob" or size < 0:
            raise ValueError("Git batch object identity/type mismatch")
        start = stop + 1
        body = raw[start:start + size]
        cursor = start + size + 1
        digest = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\x00" + body).hexdigest()
        if len(body) != size or raw[cursor - 1:cursor] != b"\n" or digest != expected:
            raise ValueError("Incomplete or changed Git blob bytes")
        result[expected] = body
    if cursor != len(raw):
        raise ValueError("Unexpected trailing Git batch bytes")
    return result


def count_source(name, raw):
    text = raw.decode("utf8")
    lines = text.splitlines()
    statements = 0
    if name.endswith(".py"):
        statements = sum(isinstance(node, ast.stmt) for node in ast.walk(ast.parse(text, filename=name)))
    return dict(files=1, bytes=len(raw), physical_lines=len(lines),
        nonblank_lines=sum(bool(line.strip()) for line in lines), python_statement_nodes=statements)


def inventory(repository, commit="HEAD", groups=None):
    repository = Path(repository).resolve()
    if commit != "HEAD" and not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Use HEAD or a full immutable Git commit")
    resolved = git(repository, "rev-parse", "--verify", commit + "^{commit}").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise ValueError("Require a SHA1-format repository commit")
    entries = parse_tree(git(repository, "ls-tree", "-r", "-z", "--full-tree", resolved))
    groups = GROUPS if groups is None else groups
    selected = select(entries, groups)
    objects = list(dict.fromkeys(row["git_blob"] for row in selected.values()))
    blobs = parse_blobs(git(repository, "cat-file", "--batch", input=("\n".join(objects) + "\n").encode("ascii")), objects)
    rows = []
    totals = dict.fromkeys(FIELDS, 0)
    grouped = {name: dict.fromkeys(FIELDS, 0) for name in sorted(groups)}
    for name, entry in selected.items():
        body = blobs[entry["git_blob"]]
        counts = count_source(name, body)
        rows.append(dict(path=name, **entry, sha256=hashlib.sha256(body).hexdigest(), **counts))
        for key in FIELDS:
            totals[key] += counts[key]
            grouped[entry["group"]][key] += counts[key]
    return dict(version=1, kind="declared_committed_source_footprint", measured_commit=resolved,
        policy=POLICY, selectors={name: list(groups[name]) for name in sorted(groups)},
        groups=grouped, totals=totals, files=rows,
        excluded_tracked_paths=sorted(set(entries) - set(selected)))


def provenance():
    repository = Path(__file__).resolve().parents[4]
    commit = git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    sources = {}
    for path in [*sorted(Path(__file__).parent.glob("*.py")), repository / "scripts/measure_code_footprint.py"]:
        name = path.relative_to(repository).as_posix()
        raw = path.read_bytes()
        blob = git(repository, "show", commit + ":" + name)
        if raw.replace(b"\r\n", b"\n") != blob:
            raise ValueError("Inventory producer must match its committed source")
        sources[name] = dict(actual_sha256=hashlib.sha256(raw).hexdigest(), git_blob_sha256=hashlib.sha256(blob).hexdigest())
    return dict(git_commit=commit, source_sha256=sources)


def markdown(report):
    lines = ["# Committed adapter source inventory", "", "Measured commit: `" + report["measured_commit"] + "`.", "",
        "| Boundary | Files | Git bytes | Physical lines | Nonblank lines | Python statement nodes |",
        "|---|---:|---:|---:|---:|---:|"]
    for name, counts in [*report["groups"].items(), ("DISTINCT TOTAL", report["totals"])]:
        lines.append("| " + name + " | " + " | ".join(str(counts[key]) for key in FIELDS) + " |")
    lines += ["", *[key + ": " + value for key, value in report["policy"].items() if key != "version"], "",
        "Exact selectors, every selected file's Git identity/SHA256 and all unselected tracked paths are in report.json.",
        "This software-cost supplement does not add an accepted scientific case or imply that pending experiments finished.", ""]
    return "\n".join(lines)


def write_inventory(repository, commit, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite a source inventory")
    report = inventory(repository, commit)
    report["producer"] = provenance()
    report["execution"] = dict(slurm_job_id=os.environ.get("SLURM_JOB_ID"))
    output.mkdir(parents=True, exist_ok=False)
    payloads = {"report.json": json.dumps(report, indent=2, allow_nan=False) + "\n", "summary.md": markdown(report)}
    columns = ("path", "group", "git_blob", "sha256", *FIELDS)
    payloads["files.tsv"] = "\t".join(columns) + "\n" + "".join("\t".join(str(row[key]) for key in columns) + "\n" for row in report["files"])
    hashes = {}
    for name, text in payloads.items():
        raw = text.encode("utf8")
        (output / name).write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    (output / "output-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf8")
    return report
