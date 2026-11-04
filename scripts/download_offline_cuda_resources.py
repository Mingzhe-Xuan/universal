"""Slurm-only resume of pinned offline wheels using bounded, reused curl connections."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote, urlsplit

CATALOG_SHA256 = "c191a5448ae0c5710236fcfa1d4109d7f557988098c6f679247181e3c81be009"
PROXY = "socks5h://127.0.0.1:1080"
MIN_FREE_BYTES = 20 * 1024**3


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def ranges_for(before, size, chunk_bytes, chunks):
    if (any(type(value) is not int for value in (before, size, chunk_bytes, chunks)) or
            before < 0 or size < before or size < 1 or chunk_bytes < 1 or not 1 <= chunks <= 32):
        raise ValueError("Invalid bounded resume range settings")
    return [(start, min(start + chunk_bytes - 1, size - 1))
            for start in range(before, min(size, before + chunks * chunk_bytes), chunk_bytes)]


def validate_append(result, planned, header_paths, before, after, expected):
    if not isinstance(result.stdout, str):
        raise ValueError("Curl metrics must be UTF-8 JSON text")
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if not rows or len(rows) > len(planned) or (result.returncode == 0 and len(rows) != len(planned)):
        raise ValueError("Curl did not report the expected range operations")
    received = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("Curl metrics must be JSON objects")
        size = row.get("size_download")
        if type(size) not in (int, float) or not math.isfinite(size) or size < 0 or int(size) != size:
            raise ValueError("Curl reported invalid received bytes")
        start, end = planned[index]
        if size > end - start + 1:
            raise ValueError("A response exceeded its bounded range")
        if size or row.get("http_code") == 206:
            if row.get("http_code") != 206:
                raise ValueError("A resumed payload lacks HTTP206")
            text = header_paths[index].read_text(encoding="iso-8859-1")
            matches = re.findall(r"(?im)^content-range:\s*bytes (\d+)-(\d+)/(\d+)\s*$", text)
            if not matches or tuple(map(int, matches[-1])) != (start, end, expected):
                raise ValueError("Response Content-Range differs from the pinned resume position")
        if index < len(rows) - 1 and size != end - start + 1:
            raise ValueError("Curl continued after an incomplete range")
        received += int(size)
    if after != before + received or after > expected:
        raise ValueError("Append position differs from received contiguous range bytes")
    return rows


def download_resource(resource, destination, *, base_url, proxy=PROXY, chunk_bytes=1024**2, chunks=8,
                      connect_timeout=20, operation_timeout=30, progress_timeout=600,
                      minimum_free_bytes=MIN_FREE_BYTES, runner=subprocess.run, clock=time.monotonic,
                      sleep=time.sleep, emit=lambda update: None):
    name, expected = resource["filename"], resource.get("size")
    if (not isinstance(name, str) or Path(name).name != name or "/" in name or "\\" in name or not name.endswith(".whl") or
            not isinstance(resource.get("sha256"), str) or not re.fullmatch("[0-9a-f]{64}", resource["sha256"])):
        raise ValueError("Resource must have a pinned wheel basename and SHA256")
    destination = Path(destination)
    final, partial = destination / name, destination / (name + ".partial")
    if final.is_symlink() or partial.is_symlink():
        raise ValueError("Do not replace symlinked resource paths")
    if final.exists():
        if digest(final) != resource["sha256"] or (expected is not None and final.stat().st_size != expected):
            raise ValueError("Conflicting existing final wheel")
        return final
    if type(expected) is not int or expected < 1:
        raise ValueError("Only an already verified wheel can omit its expected size")
    ranges_for(0, expected, chunk_bytes, chunks)
    if (any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
            for value in (connect_timeout, operation_timeout, progress_timeout)) or
            type(minimum_free_bytes) is not int or minimum_free_bytes < 0):
        raise ValueError("Invalid transfer budgets")
    destination.mkdir(parents=True, exist_ok=True)
    last_progress = clock()
    while True:
        before = partial.stat().st_size if partial.exists() else 0
        if before > expected:
            raise ValueError("Existing partial wheel exceeds its pinned size")
        if before == expected:
            break
        if shutil.disk_usage(destination).free - (expected - before) < minimum_free_bytes:
            raise OSError("Download would violate the configured disk reserve")
        emit(dict(status="running", current=dict(filename=name, bytes=before, expected=expected)))
        planned = ranges_for(before, expected, chunk_bytes, chunks)
        with tempfile.TemporaryDirectory(prefix=".ugnn-curl-", dir=destination) as folder:
            headers = [Path(folder) / f"range-{index}.headers" for index in range(len(planned))]
            command = ["curl", "--fail-early"]
            for index, (start, end) in enumerate(planned):
                if index:
                    command.append("--next")
                command += ["--fail", "--silent", "--show-error"]
                if proxy is not None:
                    command += ["--proxy", proxy]
                command += ["--connect-timeout", str(connect_timeout), "--max-time", str(operation_timeout),
                            "--continue-at", "-", "--header", f"Range: bytes={start}-{end}",
                            "--output", str(partial), "--dump-header", str(headers[index]),
                            "--write-out", "%{json}\n", base_url.rstrip("/") + "/" + quote(name, safe="")]
            result = runner(command, capture_output=True, text=True, encoding="utf-8", timeout=len(planned) * operation_timeout + 10)
            after = partial.stat().st_size if partial.exists() else 0
            try:
                metrics = validate_append(result, planned, headers, before, after, expected)
            except (ValueError, OSError, TypeError, KeyError):
                if after >= before and partial.exists():
                    with partial.open("r+b") as stream:
                        stream.truncate(before)
                raise
        greeting_closed = result.returncode == 97 and result.stderr.strip() == "curl: (97) Unable to receive initial SOCKS5 response."
        if result.returncode not in (0, 6, 7, 18, 28, 52, 55, 56) and not greeting_closed:
            raise RuntimeError(f"Unexpected curl failure {result.returncode}: {result.stderr.strip()}")
        emit(dict(status="running" if after > before else "waiting_for_proxy",
                  current=dict(filename=name, bytes=after, expected=expected), curl_exit=result.returncode,
                  curl_metrics=metrics, curl_error=result.stderr[-2000:]))
        if after > before:
            last_progress = clock()
        elif clock() - last_progress >= progress_timeout:
            raise RuntimeError("No download progress for recovery window; preserve partial and diagnose proxy")
        if after < expected:
            sleep(1 if after > before else 5)
    if digest(partial) != resource["sha256"]:
        raise ValueError("Incorrect complete resource SHA; preserve partial for diagnosis")
    partial.replace(final)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("models/official-install/arxiv-base-bootstrap/torch-cuda-catalog.json"))
    parser.add_argument("--destination", type=Path, default=Path("models/official-install/arxiv-linux-base"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:54339/cuda/")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Resource transfer and full hashing must run through Slurm")
    parts = urlsplit(args.base_url)
    if parts.scheme != "http" or parts.hostname != "127.0.0.1" or parts.username or parts.password or parts.query or parts.fragment:
        parser.error("Use the approved loopback resource endpoint through the fixed SOCKS proxy")
    if args.report.exists():
        parser.error("Use a new job-specific report")
    if digest(args.catalog) != CATALOG_SHA256:
        parser.error("Pinned CUDA resource catalog SHA differs")
    resources = json.loads(args.catalog.read_text())["resources"]
    args.destination.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    transfer_options = dict(chunk_bytes=1024**2, chunks=8, connect_timeout=20, operation_timeout=30, progress_timeout=600)
    state = dict(version=2, protocol="curl_range_connection_reuse_v1", status="running", verified=[], current=None,
                 catalog_sha256=CATALOG_SHA256, transfer_options=transfer_options, minimum_free_bytes=MIN_FREE_BYTES,
                 base_url=args.base_url, proxy=PROXY, started_at=time.time(),
                 environment_installed=False, numerical_acceptance=False,
                 source_sha256=digest(__file__), git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                 slurm_job_id=os.environ["SLURM_JOB_ID"], node=os.environ.get("SLURMD_NODENAME"),
                 curl_version=subprocess.check_output(["curl", "--version"], text=True, encoding="utf-8").splitlines()[0])

    def record(update=None):
        state.update(update or {})
        state["updated_at"] = time.time()
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temporary.replace(args.report)

    try:
        import fcntl

        with (args.destination / ".ugnn-cuda-transfer.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            record()
            health = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--proxy", PROXY,
                                     "--head", "--connect-timeout", "20", "--max-time", "30",
                                     f"http://{parts.netloc}/health"], capture_output=True, text=True, encoding="utf-8", timeout=35)
            record(dict(compute_node_proxy_health_exit=health.returncode))
            if health.returncode:
                raise RuntimeError("Compute-node resource proxy health failed: " + health.stderr[-1000:])
            for resource in resources:
                path = download_resource(resource, args.destination, base_url=args.base_url, emit=record, **transfer_options)
                state["verified"].append(path.name);record()
                print("CUDA_RESOURCE_VERIFIED " + path.name, flush=True)
            record(dict(status="complete", current=None))
    except Exception as error:
        record(dict(status="failed", error=str(error), error_type=type(error).__name__))
        raise


if __name__ == "__main__":
    main()
