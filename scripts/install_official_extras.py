"""Install pinned official-provider extras after the shared CUDA base is complete."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

RESOURCES = [
    ("official-extra-wheelhouse/opt_einsum-3.4.0-py3-none-any.whl", 71932, "69bb92469f86a1565195ece4ac0323943e83477171b91d24c35afe028a90d7cd"),
    ("official-extra-wheelhouse/opt_einsum_fx-0.1.4-py3-none-any.whl", 13213, "85f489f4c7c31fd88d5faf9669c09e61ec37a30098809fdcfe2a08a9e42f23c9"),
    ("official-extra-wheelhouse/torchmetrics-1.9.0-py3-none-any.whl", 983384, "bfdcbff3dd1d96b3374bb2496eb39f23c4b28b8a845b6a18c313688e0d2d9ca1"),
    ("official-extra-wheelhouse/lightning_utilities-0.15.3-py3-none-any.whl", 31906, "6c55f1bee70084a1cbeaa41ada96e4b3a0fea5909e844dd335bd80f5a73c5f91"),
    ("native-provider-wheelhouse/dgl-1.1.3+cu121-cp310-cp310-manylinux1_x86_64.whl", 79870014, "f32a1907431544ee1085b11deb373fa277534e41a46e5d5d0188c447fa9bae07"),
    ("provider-wheelhouse/torchvision-0.22.1+cu128-cp310-cp310-manylinux_2_28_x86_64.whl", 8730539, "538f4db667286d939b4eee0a66d31ed21b51186668006b0e0ffe20338ecc7e00"),
]
PROBE = '''import importlib.metadata as metadata,json
from pathlib import Path
torch=metadata.distribution('torch')
try:
 e3nn=metadata.distribution('e3nn');e3nn_version=e3nn.version;e3nn_root=str(Path(e3nn.locate_file('')).resolve())
except metadata.PackageNotFoundError:e3nn_version=None;e3nn_root=None
print(json.dumps(dict(torch=torch.version,torch_root=str(Path(torch.locate_file('')).resolve()),e3nn=e3nn_version,e3nn_root=e3nn_root)))
'''


def verified_resources(repository, resources=RESOURCES):
    root = Path(repository).resolve() / "models/official-install"
    paths = []
    for relative, size, expected in resources:
        path = root / relative
        if (path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file() or
                path.suffix != ".whl" or path.stat().st_size != size):
            raise ValueError(f"Missing/incomplete/unsafe official resource: {relative}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError(f"Official resource SHA mismatch: {relative}")
        paths.append(path)
    return paths


def install(repository, venv_root, *, runner=subprocess.run, resources=RESOURCES):
    wheels = verified_resources(repository, resources)
    venv_root = Path(venv_root)
    base = venv_root / "universal-base/lib/python3.10/site-packages"
    names = ("universal", "universal-mace", "universal-official")
    for name in names:
        link = venv_root / name / "lib/python3.10/site-packages/ugnn-common-base.pth"
        if link.is_symlink() or not link.is_file() or link.read_text().strip() != str(base):
            raise ValueError(f"Missing/conflicting shared base link: {name}; run the CUDA base installer first")

    def execute(name, *arguments):
        python = venv_root / name / "bin/python"
        return runner([str(python), *arguments], capture_output=True, text=True, check=True)

    def probe(name, expected_e3nn=None, e3nn_parent=None):
        value = json.loads(execute(name, "-c", PROBE).stdout)
        if value.get("torch") != "2.7.1+cu128" or Path(value["torch_root"]).resolve() != base.resolve():
            raise ValueError(f"{name} does not use the exact task shared Torch distribution")
        if expected_e3nn is not None and value.get("e3nn") != expected_e3nn:
            raise ValueError(f"{name} does not retain its pinned e3nn version")
        if expected_e3nn is not None and Path(value["e3nn_root"]).resolve() != (venv_root / (e3nn_parent or name) / "lib/python3.10/site-packages").resolve():
            raise ValueError(f"{name} does not use its pinned e3nn source")
        return value

    probe("universal-base")
    execute("universal-base", "-m", "pip", "check")
    for name, expected in (("universal", "0.5.8"), ("universal-mace", "0.4.4")):
        probe(name, expected)
        execute(name, "-m", "pip", "check")
    official = probe("universal-official")
    own_site = venv_root / "universal-official/lib/python3.10/site-packages"
    migrations = []
    if official.get("e3nn") == "0.5.8" and Path(official["e3nn_root"]).resolve() == own_site.resolve():
        execute("universal-official", "-m", "pip", "uninstall", "--yes", "e3nn")
        migrations.append("Removed own official e3nn0.5.8 overlay; retained documented MACE e3nn0.4.4 parent")
    probe("universal-official", "0.4.4", "universal-mace")
    execute("universal-official", "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--no-deps",
            "--no-cache-dir", "--only-binary=:all:", *map(str, wheels))
    verified = {}
    for name, expected in (("universal", "0.5.8"), ("universal-mace", "0.4.4"), ("universal-official", "0.4.4")):
        execute(name, "-m", "pip", "check")
        verified[name] = {"metadata": probe(name, expected, "universal-mace" if name == "universal-official" else None), "packages": json.loads(execute(name, "-m", "pip", "list", "--format=json").stdout)}
    return dict(status="complete", verified_wheels=len(wheels), environments=verified, numerical_acceptance=False,
                migrations=migrations,
                interpretation="offline dependencies and metadata verified; CUDA/GNN/derivative numerical acceptance still required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv-root", type=Path, default=Path("/home/xmz/.venvs"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        parser.error("Official environment restoration must run through Slurm")
    if args.report.exists() or args.report.is_symlink():
        parser.error("Report already exists; refusing to repeat installation into an existing report")
    repository = Path(__file__).resolve().parents[1]
    value = install(repository, args.venv_root)
    value["slurm_job_id"] = os.environ["SLURM_JOB_ID"]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
    print(json.dumps({"status": value["status"], "verified_wheels": value["verified_wheels"], "report": str(args.report)}))


if __name__ == "__main__":
    main()
