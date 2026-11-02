import copy
import hashlib

import pytest
import torch

from universal_gnn.backbones.official.base import (OfficialBackbone, ReferenceValue, artifact_files,
                                                  capture_features, select_packaged_model)


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


def test_feature_capture_skips_old_head_preserves_gradient_and_removes_hooks():
    class OldHead(torch.nn.Module):
        def forward(self, values):
            raise AssertionError("Old prediction/force head must not execute during feature extraction")

    original = torch.nn.Sequential(torch.nn.Linear(2, 3), torch.nn.Tanh(), OldHead()).double()
    positions = torch.tensor([[.2, .7]], dtype=torch.float64, requires_grad=True)
    expected = original[1](original[0](positions))
    for before, target in [(True, original[2]), (False, original[1])]:
        extract = (lambda inputs: inputs[0]) if before else (lambda value: value)
        features = capture_features(lambda: original(positions), target, extract, before=before)
        torch.testing.assert_close(features, expected, rtol=0, atol=0)
        gradient = torch.autograd.grad(features.sum(), positions, create_graph=True)[0]
        second = torch.autograd.grad(gradient.sum(), positions)[0]
        assert torch.isfinite(second).all() and second.norm() > 0
        assert not target._forward_hooks and not target._forward_pre_hooks
    with pytest.raises(AssertionError, match="Old prediction"):
        original(positions)


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
    bad = copy.deepcopy(artifact)
    bad["version"] = 99
    with pytest.raises(ValueError, match="artifact version"):
        artifact_files("unit-provider", {}, artifact=bad)


def test_official_checkpoint_rejects_different_original_source_version():
    artifact = {"version": 1, "provider": "unit", "files": {}, "sha256": {}}
    OfficialBackbone(torch.nn.Linear(2, 3), "3x0e", "invariant", 2., artifact, version="original-v1")
    with pytest.raises(ValueError, match="source/version"):
        OfficialBackbone(torch.nn.Linear(2, 3), "3x0e", "invariant", 2., artifact, version="different-v2")


def test_nequip_package_container_selects_original_model_without_reconstruction():
    first, second = torch.nn.Linear(2, 3), torch.nn.Linear(2, 3)
    assert select_packaged_model(first) == (first, None)
    assert select_packaged_model(torch.nn.ModuleDict({"sole_model": first})) == (first, "sole_model")
    models = torch.nn.ModuleDict({"first": first, "second": second})
    with pytest.raises(ValueError, match="multiple models"):
        select_packaged_model(models)
    assert select_packaged_model(models, "second") == (second, "second")
    with pytest.raises(ValueError, match="no model"):
        select_packaged_model(models, "absent")
