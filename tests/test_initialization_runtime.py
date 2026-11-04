"""Tiny Torch integration fixtures; execute through the Slurm regression entry."""
from types import SimpleNamespace
import pytest
import torch

from universal_gnn.backbones.official.base import OfficialBackbone
from universal_gnn.backbones.initialization import initialize_original


def test_lazy_backbone_exports_preserve_class_identity():
    from universal_gnn import backbones
    from universal_gnn.backbones import invariant

    for name in backbones.__all__:
        assert getattr(backbones,name) is getattr(invariant,name)


def test_fresh_state_has_constructor_bn_statistics_and_load_coverage():
    torch.manual_seed(3)
    reference = torch.nn.Sequential(torch.nn.Linear(3,4),torch.nn.BatchNorm1d(4))
    with torch.no_grad():
        reference[1].running_mean.fill_(17)
        reference[1].running_var.fill_(19)
        reference[1].num_batches_tracked.fill_(100)
    torch.manual_seed(4)
    fresh = torch.nn.Sequential(torch.nn.Linear(3,4),torch.nn.BatchNorm1d(4))
    initialize_original(fresh,reference.state_dict(),mode="scratch")
    assert not torch.equal(fresh[0].weight,reference[0].weight)
    assert fresh[1].running_mean.eq(0).all() and fresh[1].running_var.eq(1).all()
    assert fresh[1].num_batches_tracked.item()==0
    backbone = OfficialBackbone(fresh,"4x0e","invariant",4.,
             {"version":1,"provider":"unit","files":{},"sha256":{}},initialization="scratch")
    assert backbone.load_report["parameter_coverage"]==0 and backbone.load_report["buffer_coverage"]==0
    with pytest.raises(ValueError,match="original pretrained head"):
        backbone.native_task_contract()


def test_initialization_config_resume_default_and_conflict():
    from copy import deepcopy
    from universal_gnn.engine.runtime import check_model_config
    from universal_gnn.contracts.schema import validate_config

    config={"backbone":{"name":"cgcnn","implementation":"official"},
            "task":{"kind":"supervised","property":"bandgap"}}
    explicit=deepcopy(config)
    explicit["backbone"]["initialization"]="pretrained"
    check_model_config(config,explicit)
    explicit["backbone"]["initialization"]="scratch"
    with pytest.raises(ValueError,match="checkpoint backbone"):
        check_model_config(config,explicit)
    with pytest.raises(ValueError,match="head_mode=reset"):
        validate_config({**explicit,"prediction":{"head_mode":"native"}})


def test_scratch_backbone_cannot_be_overwritten_by_warm_start_or_mislabeled_checkpoint(tmp_path):
    from universal_gnn.engine.runtime import save_training_checkpoint
    from universal_gnn.engine.warm_start import initialize_components

    backbone=OfficialBackbone(torch.nn.Linear(3,4),"4x0e","invariant",4.,
             {"version":1,"provider":"unit","files":{},"sha256":{}},initialization="scratch")
    model=SimpleNamespace(backbone=backbone)
    with pytest.raises(ValueError,match="scratch backbone"):
        initialize_components(model,tmp_path/"never-read.pt")
    with pytest.raises(ValueError,match="does not match"):
        save_training_checkpoint(tmp_path/"never-written.pt",model,None,{"backbone":{"name":"cgcnn"}},None,None)
    assert not (tmp_path/"never-written.pt").exists()


