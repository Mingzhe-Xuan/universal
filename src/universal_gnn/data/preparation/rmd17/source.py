"""Author version-four bytes; NumPy is imported only for full Slurm inspection."""

import hashlib
import os
from pathlib import Path


SOURCE_URL = "https://figshare.com/articles/dataset/Revised_MD17_dataset_rMD17_/12672038/4"
SOURCE_FILES = {
    "rmd17_ethanol.npz": dict(file_id=62265733, bytes=67201791,
        sha256="0824d78c687b8ede25f7162c54c5c6434cfe37f9f859ee8f223c60379d7d5cf9",
        md5="eb837fb8deb27d4e0d52f71a03aff776"),
    "readme.txt": dict(file_id=24013628, bytes=2082,
        sha256="6e4f0e262a9065a59ad298773c5b12f88561f69c28f7a182a704b97afbf3957c",
        md5="29e6f250bb2d1c461363e24955b5be1e"),
    "index_train_01.csv": dict(file_id=62265793, bytes=5880,
        sha256="67f2c51e7c00bbc1f9fc5ba90863e5d526e6bca0d885bb68f9a1df4a5b7825cb",
        md5="22264dcf2e42d6133362411abbbe4ce8"),
    "index_test_01.csv": dict(file_id=62265781, bytes=5896,
        sha256="65bfd73039f32a73586b84d799b96cea4fb4809a642611a7e8e8d94b9a5982f8",
        md5="124c8a0849e84e244d6ce8424e1c05cf"),
}


def verify_sources(directory):
    checked = {}
    for name, expected in SOURCE_FILES.items():
        path = Path(directory) / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != expected["bytes"]:
            raise ValueError("rMD17 original source size/file/symlink mismatch: " + name)
        sha, md5 = hashlib.sha256(), hashlib.md5()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 ** 2), b""):
                sha.update(block)
                md5.update(block)
        if sha.hexdigest() != expected["sha256"] or md5.hexdigest() != expected["md5"]:
            raise ValueError("rMD17 original source checksum mismatch: " + name)
        checked[name] = dict(expected)
    return checked


def read_arrays(directory):
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Full rMD17 array inspection requires Slurm")
    import numpy as np

    expected = {"nuclear_charges": (9,), "coords": (100000, 9, 3), "energies": (100000,),
                "forces": (100000, 9, 3), "old_indices": (100000,),
                "old_energies": (100000,), "old_forces": (100000, 9, 3)}
    with np.load(Path(directory) / "rmd17_ethanol.npz", allow_pickle=False) as source:
        if set(source.files) != set(expected):
            raise ValueError("rMD17 requires all seven original arrays")
        arrays = {name: source[name] for name in expected}
    for name, value in arrays.items():
        if value.shape != expected[name] or value.dtype.kind not in "iuf" or not bool(np.isfinite(value).all()):
            raise ValueError("rMD17 array shape/type/finiteness differs: " + name)
    z, old = arrays["nuclear_charges"], arrays["old_indices"]
    if (z.dtype.kind not in "iu" or dict(zip(*np.unique(z, return_counts=True))) != {1: 6, 6: 2, 8: 1}
            or old.dtype.kind not in "iu" or int(old.min()) < 0 or len(np.unique(old)) != 100000):
        raise ValueError("rMD17 ethanol species or unique original frame indices differ")
    summary = {name: dict(shape=list(value.shape), dtype=str(value.dtype), finite_elements=int(value.size))
               for name, value in arrays.items()}
    return arrays, summary
