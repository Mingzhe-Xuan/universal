"""Author Figshare file identities; downloading is separate from CPU preparation."""

import hashlib
from pathlib import Path

SOURCE_URL = "https://doi.org/10.6084/m9.figshare.c.978904.v5"
FILES = {
    "dsgdb9nsd.xyz.tar.bz2": dict(id=3195389, bytes=86144227, md5="ad1ebd51ee7f5b3a6e32e974e5d54012"),
    "uncharacterized.txt": dict(id=3195404, bytes=486752, md5="a361887bacb427b8a0ce7903d92a53b4"),
    "readme.txt": dict(id=3195392, bytes=5198, md5="c6581a03f673746528c57acfc6b79679"),
}
RAW_COUNT, EXCLUDED_COUNT, CLEAN_COUNT = 133885, 3054, 130831
HARTREE_TO_EV = 27.211386245988
UNITS = dict(homo="eV", lumo="eV", dipole_magnitude="Debye", isotropic_polarizability="Bohr^3")


def digest(path, algorithm="sha256"):
    result = hashlib.new(algorithm)
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def verify_sources(directory):
    result = {}
    for name, expected in FILES.items():
        path = Path(directory) / name
        if path.stat().st_size != expected["bytes"] or digest(path, "md5") != expected["md5"]:
            raise ValueError("QM9 original source checksum/size differs: " + name)
        result[name] = dict(expected, sha256=digest(path), url=f"https://ndownloader.figshare.com/files/{expected['id']}")
    return result


def excluded_ids(text, *, expected_count=EXCLUDED_COUNT):
    ids = []
    for line in text.splitlines():
        first = line.split()[:1]
        if first and first[0].isdecimal():
            value = int(first[0])
            if not 1 <= value <= RAW_COUNT or value in ids:
                raise ValueError("Invalid or duplicate original QM9 exclusion ID")
            ids.append(value)
    if len(ids) != expected_count:
        raise ValueError("Original QM9 exclusion count differs")
    return set(ids)
