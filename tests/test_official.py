import copy
import hashlib

import pytest
import torch

from universal_gnn.backbones.official.base import ReferenceValue, artifact_files


def test_original_preprocessing_value_and_higher_order_gradient():
    position = torch.tensor([.2, .8], dtype=torch.float64, requires_grad=True)
    live = torch.exp(-position.square())
    reference = live.detach().clone()
    value = ReferenceValue.apply(reference, live)
    torch.testing.assert_close(value, reference, rtol=0, atol=0)
    first = torch.autograd.grad(value.sum(), position, create_graph=True)[0]
    second = torch.autograd.grad(first.sum(), position)[0]
    torch.testing.assert_close(first, -2 * position * live)
    torch.testing.assert_close(second, (4 * position.square() - 2) * live)


def test_official_source_artifacts_survive_source_deletion_and_detect_corruption(tmp_path):
    path = tmp_path / "model.bin"
    path.write_bytes(b"source-artifact")
    artifact = artifact_files("unit-provider", {"model": path}, source="unit-test")
    assert artifact["sha256"]["model"] == hashlib.sha256(b"source-artifact").hexdigest()
    path.unlink()
    assert artifact_files("unit-provider", {}, artifact=artifact) == artifact
    bad = copy.deepcopy(artifact)
    bad["files"]["model"] = b"corrupted"
    with pytest.raises(ValueError, match="checksum"):
        artifact_files("unit-provider", {}, artifact=bad)
    with pytest.raises(ValueError, match="wrong provider"):
        artifact_files("other", {}, artifact=artifact)
    with pytest.raises(ValueError, match="requires source artifact"):
        artifact_files("unit-provider", {"model": None})
