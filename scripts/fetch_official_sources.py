"""Fetch pinned, unmodified official source packages and make a verifiable offline bundle."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen
import zipfile


SOURCES = {
    "cgcnn": ("txie-93/cgcnn", "f42ab233c4ee0c416879d6bc2d22a264418413ad", "cgcnn"),
    "equiformer": ("atomicarchitects/equiformer", "64cb7866f48b9aa156e74a9d6a2ef2663b367437", "nets"),
    "ocp": ("FAIR-Chem/fairchem", "b5a197fc3c79a9a5a787aabaa02979be53d296b7", "ocpmodels"),
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def prepare(cache, destination):
    cache, destination = Path(cache), Path(destination)
    cache.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    contents, manifest = {}, {"version": 1, "repositories": {}, "files": {}}
    for name, (repository, commit, package) in SOURCES.items():
        url = f"https://codeload.github.com/{repository}/zip/{commit}"
        archive_path = cache / f"{name}-{commit}.zip"
        if not archive_path.is_file():
            temporary = archive_path.with_suffix(".part")
            with urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
            temporary.replace(archive_path)
        archive_sha256 = sha256_file(archive_path)
        manifest["repositories"][name] = {"repository": repository, "commit": commit, "url": url,
                                          "archive_sha256": archive_sha256}
        with zipfile.ZipFile(archive_path) as archive:
            for item in archive.infolist():
                parts = Path(item.filename).parts
                if item.is_dir() or len(parts) < 2:
                    continue
                relative = Path(*parts[1:])
                if ".." in relative.parts or relative.is_absolute():
                    raise ValueError("Unsafe official archive member")
                if relative.parts[0] != package and relative.name.lower() not in {"license", "license.txt", "license.md"}:
                    continue
                if (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Symbolic links are not copied into the source bundle")
                if "__pycache__" in relative.parts or relative.suffix == ".pyc":
                    continue
                target = (Path(name) / relative).as_posix()
                content = archive.read(item)
                contents[target] = content
                manifest["files"][target] = hashlib.sha256(content).hexdigest()
        if f"{name}/{package}/__init__.py" not in contents:
            raise ValueError(f"Missing original {package} package in {url}")
        print(json.dumps({"repository": repository, "commit": commit, "archive_sha256": archive_sha256}), flush=True)
    contents["SOURCE.json"] = json.dumps(manifest, indent=2).encode()
    with destination.open("wb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as bundle:
            for name, content in sorted(contents.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.mtime = len(content), 0o644, 0
                bundle.addfile(member, io.BytesIO(content))
    with tarfile.open(destination) as bundle:
        for member in bundle.getmembers():
            if member.name == "SOURCE.json":
                continue
            if hashlib.sha256(bundle.extractfile(member).read()).hexdigest() != manifest["files"][member.name]:
                raise AssertionError("Source bundle changed an upstream file")
    digest = sha256_file(destination)
    print(json.dumps({"bundle": str(destination), "sha256": digest, "bytes": destination.stat().st_size,
                      "files": len(manifest["files"])}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("models/official/sources"))
    parser.add_argument("--output", type=Path, default=Path("tmp/official-sources.tar.gz"))
    args = parser.parse_args()
    prepare(args.cache, args.output)
