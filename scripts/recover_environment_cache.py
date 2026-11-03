"""Recover only catalogued public wheels from pip caches; run large checks on Slurm."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit, urlunsplit


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def cache_key(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username is not None or parts.password is not None:
        raise ValueError("Cache recovery requires public HTTPS URLs")
    if parts.hostname not in {"files.pythonhosted.org", "pypi.nvidia.com", "download.pytorch.org", "download-r2.pytorch.org"}:
        raise ValueError("Unexpected wheel source host")
    normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))
    return hashlib.sha224(normalized.encode()).hexdigest()


def validate_resource(resource):
    name = resource["filename"]
    if not isinstance(name, str) or Path(name).name != name or "/" in name or "\\" in name or not name.endswith(".whl"):
        raise ValueError("Resource filename must be a wheel basename")
    if not re.fullmatch("[0-9a-f]{64}", resource["sha256"]):
        raise ValueError("Resource requires an official SHA256")
    size = resource.get("size")
    if size is not None and (not isinstance(size, int) or isinstance(size, bool) or size < 1):
        raise ValueError("Resource size must be positive or null")
    if not resource.get("cache_urls"):
        raise ValueError("Resource requires explicit cache URLs")
    for url in resource["cache_urls"]:
        cache_key(url)


def _reserve(directory, bytes_to_write, minimum):
    if shutil.disk_usage(directory).free - bytes_to_write < minimum:
        raise OSError("Wheel recovery would violate the configured free-space reserve")


def recover_resource(resource, cache_root, wheelhouse, *, min_free_bytes=20 * 1024**3):
    validate_resource(resource)
    cache_root, wheelhouse = Path(cache_root), Path(wheelhouse)
    wheelhouse.mkdir(parents=True, exist_ok=True)
    destination = wheelhouse / resource["filename"]
    expected = resource["sha256"]
    result = {"filename": resource["filename"], "sha256": expected, "status": "missing", "checks": []}
    if destination.exists():
        if digest(destination) != expected:
            raise ValueError(f"Existing destination has a different digest: {destination}")
        return {**result, "status": "verified_existing", "bytes": destination.stat().st_size}
    checked = set()
    for url in resource["cache_urls"]:
        key = cache_key(url)
        for version in ("http-v2", "http"):
            base = cache_root / version / Path(*key[:5]) / key
            for source, kind in ((base.with_name(base.name + ".body"), "body"), (base, "legacy")):
                if source in checked:
                    continue
                checked.add(source)
                if not source.is_file():
                    continue
                body = None
                if kind == "legacy":
                    with source.open("rb") as stream:
                        prefix = stream.read(5)
                    if prefix != b"cc=4,":
                        continue
                    if source.stat().st_size > 3 * 1024**3:
                        result["checks"].append({"path": str(source), "status": "legacy_too_large"})
                        continue
                    from pip._vendor import msgpack

                    value = msgpack.unpackb(source.read_bytes()[5:], raw=False)
                    body = value.get("response", {}).get("body")
                    if not isinstance(body, bytes):
                        continue
                    actual = hashlib.sha256(body).hexdigest()
                    size = len(body)
                else:
                    actual, size = digest(source), source.stat().st_size
                if actual != expected or (resource.get("size") is not None and size != resource["size"]):
                    result["checks"].append({"path": str(source), "status": "digest_or_size_mismatch"})
                    continue
                mode = "legacy_copy" if body is not None else "hardlink"
                additional = size if body is not None or source.stat().st_dev != wheelhouse.stat().st_dev else 0
                _reserve(wheelhouse, additional, min_free_bytes)
                descriptor, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=wheelhouse)
                os.close(descriptor)
                temporary = Path(temporary_name)
                try:
                    if body is not None:
                        temporary.write_bytes(body)
                    else:
                        temporary.unlink()
                        try:
                            os.link(source, temporary)
                        except OSError:
                            _reserve(wheelhouse, size, min_free_bytes)
                            shutil.copyfile(source, temporary)
                            mode = "copy"
                    if digest(temporary) != expected:
                        raise ValueError("Cache bytes changed during recovery")
                    os.replace(temporary, destination)
                finally:
                    temporary.unlink(missing_ok=True)
                return {**result, "status": "recovered", "bytes": size, "source": str(source), "mode": mode}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, default=Path.home() / ".cache/pip")
    parser.add_argument("--min-free-gib", type=float, default=20.)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Large cache verification/extraction must run through Slurm")
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if catalog.get("version") != 1 or not catalog.get("resources"):
        parser.error("Unsupported/empty wheel catalog")
    if not 0 <= args.min_free_gib < float("inf"):
        parser.error("min-free-gib must be finite and nonnegative")
    records = [recover_resource(resource, args.cache_root, args.wheelhouse,
                                min_free_bytes=int(args.min_free_gib * 1024**3)) for resource in catalog["resources"]]
    report = {"version": 1, "catalog_sha256": digest(args.catalog), "slurm_job_id": os.environ["SLURM_JOB_ID"],
              "resources": records, "complete": all(r["status"] != "missing" for r in records),
              "missing": [r["filename"] for r in records if r["status"] == "missing"]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"complete": report["complete"], "verified": len(records) - len(report["missing"]),
                      "missing": report["missing"]}))


if __name__ == "__main__":
    main()
