import pytest
import torch

from universal_gnn.engine.training import build_model, load_checkpoint

from test_backbones import tiny_batch


@pytest.mark.parametrize("format_version", [1, 2])
def test_geometry_basis_version_survives_checkpoint_loading(tmp_path, format_version):
    config = {"backbone": {"name": "cgcnn", "width": 8, "layers": 1, "cutoff": 2.},
              "task": {"kind": "supervised", "property": "dielectric", "route": "common_equivariant"}}
    explicit = {**config, "task": {**config["task"], "adapter_version": format_version}}
    model = build_model(explicit).double().eval()
    batch = tiny_batch()
    before = model(batch)
    saved = {"config": config, "state_dict": model.state_dict()}
    if format_version == 2:
        saved["format_version"] = 2
    path = tmp_path / "model.pt"
    torch.save(saved, path)
    again = load_checkpoint(path)
    assert again.adapter.basis_version == format_version
    torch.testing.assert_close(again(batch), before, atol=1e-10, rtol=1e-10)
