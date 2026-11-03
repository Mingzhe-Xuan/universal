"""Verify a chunked wheel archive completely before exposing wheels to pip."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def basename(name):
    if not isinstance(name, str) or not name or "/" in name or "\\" in name or Path(name).name != name:
        raise ValueError("Resource names must be basenames")
    return name


def restore(manifest_path, parts, archive_path, wheelhouse, *, min_free_bytes=20 * 1024**3):
    manifest_path, parts, archive_path, wheelhouse = map(Path, (manifest_path, parts, archive_path, wheelhouse))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or not manifest.get("chunks") or not manifest.get("wheels"):
        raise ValueError("Unsupported/empty archive manifest")
    chunks, wheels = manifest["chunks"], manifest["wheels"]
    for rows in (chunks, wheels):
        names = [basename(row["filename"]) for row in rows]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate manifest resource name")
        if any(not isinstance(row["size"], int) or isinstance(row["size"], bool) or row["size"] < 1 for row in rows):
            raise ValueError("Resource sizes must be positive integers")
    if any(not row["filename"].endswith(".whl") for row in wheels):
        raise ValueError("Archive may contain wheel resources only")
    for row in chunks:
        source = parts / row["filename"]
        if not source.is_file() or source.stat().st_size != row["size"] or digest(source) != row["sha256"]:
            raise ValueError(f"Missing/incomplete/corrupt chunk {source.name}")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    wheelhouse.mkdir(parents=True, exist_ok=True)
    required = sum(row["size"] for row in wheels) + (0 if archive_path.exists() else manifest["archive"]["size"])
    if shutil.disk_usage(wheelhouse).free - required < min_free_bytes:
        raise OSError("Archive restoration would violate free-space reserve")
    if not archive_path.exists():
        descriptor, temporary_name = tempfile.mkstemp(prefix=archive_path.name + ".", suffix=".tmp", dir=archive_path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            with temporary.open("wb") as output:
                for row in chunks:
                    with (parts / row["filename"]).open("rb") as stream:
                        shutil.copyfileobj(stream, output, length=1024 * 1024)
            if temporary.stat().st_size != manifest["archive"]["size"] or digest(temporary) != manifest["archive"]["sha256"]:
                raise ValueError("Combined archive digest/size mismatch")
            os.replace(temporary, archive_path)
        finally:
            temporary.unlink(missing_ok=True)
    elif digest(archive_path) != manifest["archive"]["sha256"]:
        raise ValueError("Existing archive conflicts with manifest")
    with tarfile.open(archive_path, "r:") as archive:
        members = archive.getmembers()
        if (len(members) != len(wheels) or {m.name for m in members} != {row["filename"] for row in wheels} or
                any(not m.isfile() or basename(m.name) != m.name for m in members)):
            raise ValueError("Archive members differ from the wheel manifest")
        # Validate all member metadata and existing outputs before extracting anything.
        for row in wheels:
            if archive.getmember(row["filename"]).size != row["size"]:
                raise ValueError("Wheel archive member size mismatch")
            destination = wheelhouse / row["filename"]
            if destination.exists() and digest(destination) != row["sha256"]:
                raise ValueError("Existing wheel conflicts with manifest")
        for row in wheels:
            destination = wheelhouse / row["filename"]
            if destination.exists():
                continue
            descriptor, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=wheelhouse)
            os.close(descriptor)
            temporary = Path(temporary_name)
            try:
                with archive.extractfile(row["filename"]) as source, temporary.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if digest(temporary) != row["sha256"]:
                    raise ValueError("Extracted wheel digest mismatch")
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
    return {"version": 1, "verified_wheels": len(wheels), "archive_sha256": manifest["archive"]["sha256"],
            "wheelhouse": str(wheelhouse), "scope": "resource bytes verified; no model/environment readiness claim"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--parts", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Large archive verification/restoration must run through Slurm")
    result = restore(args.manifest, args.parts, args.archive, args.wheelhouse)
    result["slurm_job_id"] = os.environ["SLURM_JOB_ID"]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
