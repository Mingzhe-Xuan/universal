"""Actual legacy NequIP checkpoint restoration; numerical work requires Slurm."""
import copy
from dataclasses import replace
import hashlib
import os
from pathlib import Path
from types import MethodType
import json

import pytest
import torch

from universal_gnn.backbones.official.checkpoint_graph import LEGACY_NEQUIP_SOURCE, PERIODIC_NEQUIP_SOURCE
from universal_gnn.contracts import StructureBatch
from universal_gnn.engine.training import build_model, dataset, load_checkpoint, predict

pytestmark=pytest.mark.skipif(not os.environ.get('SLURM_JOB_ID') or not os.environ.get('UGNN_LEGACY_NEQUIP_REPORT'),
    reason='Actual legacy NequIP checkpoint and Slurm allocation required')


@pytest.fixture(scope='module')
def actual_legacy():
    trained=json.loads(Path(os.environ['UGNN_LEGACY_NEQUIP_REPORT']).read_bytes())
    path=Path(trained['best_checkpoint']);before=hashlib.sha256(path.read_bytes()).hexdigest()
    saved=torch.load(path,map_location='cpu',weights_only=True)
    assert saved['config']['backbone']['neighbor_statistics']['native_graph']['adapter_source_sha256']==LEGACY_NEQUIP_SOURCE
    torch.manual_seed(123)
    model=load_checkpoint(path,device='cpu')
    structures=dataset(saved['config']);assert len(structures)==3998 and len(structures.source)==4999
    yield saved,model,[structures[i] for i in [0,1999,3997]]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_actual_state_and_original_neighbor_normalization_unchanged(actual_legacy):
    saved,model,_=actual_legacy;actual=model.state_dict()
    assert set(actual)==set(saved['state_dict'])
    for key,value in actual.items():
        assert value.dtype==saved['state_dict'][key].dtype
        torch.testing.assert_close(value,saved['state_dict'][key],rtol=0,atol=0)
    metadata=model.backbone._checkpoint_graph_compatibility
    assert metadata['allowed_pbc']=='fully_periodic_only' and not metadata['statistics_recalibrated']
    assert metadata['original_native_graph']['adapter_source_sha256']==LEGACY_NEQUIP_SOURCE
    assert metadata['runtime_native_graph']['adapter_source_sha256']==PERIODIC_NEQUIP_SOURCE
    assert model.backbone.load_report['neighbor_statistics']==saved['config']['backbone']['neighbor_statistics']


def test_actual_fresh_constructor_still_refuses_old_graph_statistics(actual_legacy):
    saved,_,_=actual_legacy
    with pytest.raises(ValueError,match='Fresh native neighbor statistics'):
        build_model(copy.deepcopy(saved['config']),official_artifact=saved['official_backbone'])


@pytest.mark.parametrize('flags',[(False,False,False),(True,False,True)])
def test_actual_guard_rejects_other_pbc_before_native_builder(actual_legacy,flags,monkeypatch):
    _,model,structures=actual_legacy
    batch=StructureBatch.from_structures([structures[0]])
    batch=replace(batch,pbc=torch.tensor([flags],dtype=torch.bool))
    def forbidden(*args,**kwargs):raise AssertionError('Native graph builder was reached')
    monkeypatch.setattr(type(model.backbone),'native_input',forbidden)
    with pytest.raises(ValueError,match='fully periodic'):model.backbone.native_input(batch)


def test_actual_periodic_native_fields_remain_exact(actual_legacy):
    _,model,structures=actual_legacy
    for structure in structures:
        batch=StructureBatch.from_structures([structure]);assert bool(batch.pbc.all())
        guarded=model.backbone.native_input(batch)
        original=type(model.backbone).native_input(model.backbone,batch)
        assert set(guarded)==set(original)
        for key in original:torch.testing.assert_close(guarded[key],original[key],rtol=0,atol=0)


def test_actual_predictions_unchanged_by_periodic_guard(actual_legacy,monkeypatch):
    saved,model,structures=actual_legacy
    batch=StructureBatch.from_structures(structures)
    guarded=predict(model,batch,saved['config'])
    with monkeypatch.context() as context:
        context.setattr(model.backbone,'native_input',MethodType(type(model.backbone).native_input,model.backbone))
        original=predict(model,batch,saved['config'])
    assert set(guarded)==set(original)
    for name,value in original.items():torch.testing.assert_close(guarded[name],value,rtol=0,atol=0)
