"""Optional immutable dataset identities, independent of numerical/model libraries."""

import hashlib
from pathlib import Path
import re


def check_expected_digest(expected, actual, field):
    if expected is None:
        return
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"{field} must be a lowercase SHA256 digest")
    if actual != expected:
        raise ValueError(f"{field} differs from the configured immutable input")


def validate_dataset_digest(settings, *, actual_sha256=None):
    expected = settings.get("sha256")
    if expected is None:
        return
    check_expected_digest(expected, expected, "dataset.sha256")
    path = settings.get("path")
    if not isinstance(path, (str, Path)) or str(path).startswith("plugin:"):
        raise ValueError("dataset.sha256 describes file bytes; plugin datasets require their own data provenance")
    if actual_sha256 is None:
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        actual_sha256 = digest.hexdigest()
    check_expected_digest(expected, actual_sha256, "dataset.sha256")
