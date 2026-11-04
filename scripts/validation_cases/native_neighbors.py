"""Real original graph scanning; run separately in each provider environment under Slurm."""

from contextlib import ExitStack
import copy
import hashlib
import json
import os
import random
from unittest.mock import patch

import pytest
import torch
import numpy as np

from universal_gnn.backbones.factory import make_backbone
from universal_gnn.data.splits.manifest import create_manifest
from universal_gnn.engine.initialization.neighbors import prepare_native_neighbors
from universal_gnn.engine.training import build_model


@pytest.fixture
def config(tmp_path):
    provider = os.environ["UGNN_NEIGHBOR_PROVIDER"]
    assert provider in {"mace", "nequip"}
    records = []
    for index, spacing in enumerate((1.4, 1.8, .7, 2.)):
        records.append(dict(schema_version=1, id=f"scan-{index}", numbers=[6, 6],
                            positions=[[0., 0., 0.], [spacing, 0., 0.]],
                            cell=[[20., 0., 0.], [0., 20., 0.], [0., 0., 20.]],
                            pbc=[False, False, False], targets={}))
    source = tmp_path / "data.jsonl"
    source.write_text("".join(json.dumps(record) + "\n" for record in records))
    manifest = create_manifest([dict(id=item["id"], group=item["id"]) for item in records],
                               source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                               official={item["id"]: "train" if index < 2 else "validation" if index == 2 else "test"
                                         for index, item in enumerate(records)})
    split = tmp_path / "split.json";split.write_text(json.dumps(manifest))
    return dict(backbone=dict(name=provider, implementation="official", initialization="scratch"),
                dataset=dict(path=str(source), split_manifest=str(split), partition="train"),
                task=dict(kind="supervised", property="bandgap"), dtype="float32", structures="all")


def test_actual_graphs_scan_train_once_preserve_rng_and_never_forward(config):
    calls = []
    original = copy.deepcopy(config)
    with ExitStack() as stack:
        def factory(name, **options):
            model = make_backbone(name, **options)
            native_input = model.native_input
            def record(batch):
                calls.extend(batch.identifiers)
                return native_input(batch)
            model.native_input = record
            stack.enter_context(patch.object(model.model, "forward", side_effect=AssertionError("GNN forward forbidden")))
            return model
        stack.enter_context(patch("universal_gnn.backbones.factory.make_backbone", side_effect=factory))
        torch.manual_seed(195)
        rng = torch.get_rng_state().clone()
        resolved = prepare_native_neighbors(config)
        assert torch.equal(torch.get_rng_state(), rng)
    assert config == original
    assert calls == ["scan-0", "scan-1"]
    statistics = resolved["backbone"]["neighbor_statistics"]
    assert statistics["structures"] == statistics["declared_training_structures"] == 2
    assert statistics["atomic_nodes"] == statistics["active_receivers"] == 4
    assert statistics["directed_edges"] == 4
    assert statistics["native_graph"]["artifact_sha256"]


def test_bound_receipt_reused_without_rescanning_and_tampering_rejected(config):
    resolved = prepare_native_neighbors(config)
    with ExitStack() as stack:
        def factory(name, **options):
            model = make_backbone(name, **options)
            stack.enter_context(patch.object(model, "native_input", side_effect=AssertionError("Unexpected graph rescan")))
            return model
        stack.enter_context(patch("universal_gnn.backbones.factory.make_backbone", side_effect=factory))
        assert prepare_native_neighbors(resolved) == resolved
        changed = copy.deepcopy(resolved)
        changed["backbone"]["neighbor_statistics"]["native_graph"]["provider_version"] = "changed"
        with pytest.raises(ValueError, match="implementation/artifact"):
            prepare_native_neighbors(changed)
        changed = copy.deepcopy(resolved);changed["dtype"] = "float64"
        with pytest.raises(ValueError, match="precision"):
            prepare_native_neighbors(changed)


def test_partial_training_and_holdout_selection_rejected(config):
    for changed in ({**config, "structures": 1},
                    {**config, "dataset": {**config["dataset"], "partition": "validation"}}):
        with patch("universal_gnn.backbones.factory.make_backbone", side_effect=AssertionError("Must reject before construction")):
            with pytest.raises(ValueError):
                prepare_native_neighbors(changed)


def test_calibration_keeps_saved_fresh_provenance_intact(config):
    from universal_gnn.backbones.official.profiles import official_options

    provider = config["backbone"]["name"]
    options = official_options(provider, {"initialization": "scratch"})
    options["initialization"] = "pretrained"
    reference = make_backbone(provider, **options)
    artifact = copy.deepcopy(reference.official_artifact)
    artifact["implementation"] = {"native_class": "saved.fresh.constructor", "backend_version": "fixture"}
    original = copy.deepcopy(artifact)
    resolved = prepare_native_neighbors(config, official_artifact=artifact)
    assert resolved["backbone"]["neighbor_statistics"]["native_graph"]["artifact_sha256"] == artifact["sha256"]
    assert artifact == original


def test_fresh_constructor_consumes_receipt_and_inference_rejects_changed_graph(config):
    resolved = prepare_native_neighbors(config)
    def audited_factory(*args, **kwargs):
        torch_rng, python_rng, numpy_rng = torch.get_rng_state().clone(), random.getstate(), np.random.get_state()
        dtype = torch.get_default_dtype()
        backbone = make_backbone(*args, **kwargs)
        assert torch.equal(torch_rng, torch.get_rng_state())
        assert python_rng == random.getstate()
        current_numpy_rng = np.random.get_state()
        assert numpy_rng[0] == current_numpy_rng[0] and np.array_equal(numpy_rng[1], current_numpy_rng[1])
        assert numpy_rng[2:] == current_numpy_rng[2:]
        assert torch.get_default_dtype() == dtype
        return backbone
    with patch("universal_gnn.engine.training.make_backbone", side_effect=audited_factory):
        model = build_model(resolved)
    assert model.backbone.load_report["neighbor_statistics"] == resolved["backbone"]["neighbor_statistics"]
    assert model.backbone.load_report["parameter_coverage"] == model.backbone.load_report["buffer_coverage"] == 0.
    assert model.backbone.load_report["state_layout_verified"]
    if config["backbone"]["name"] == "mace":
        assert len(model.backbone.load_report["structural_state_migrations"]) == 6
        assert model.backbone.model.atomic_energies_fn.atomic_energies.eq(0).all()
        assert model.backbone.model.scale_shift.scale.eq(1).all()
        assert model.backbone.model.scale_shift.shift.eq(0).all()
    if config["backbone"]["name"] == "nequip":
        assert model.backbone.load_report["constructor"] == "nequip.model.FullNequIPGNNModel"
        assert model.backbone.load_report["original_layout"] == dict(
            irreps_edge_sh="1x0e+1x1e", type_embed_num_features=32,
            feature_irreps_hidden=["128x0e+64x1e", "128x0e"])
    changed = copy.deepcopy(resolved)
    changed["backbone"]["neighbor_statistics"]["native_graph"]["adapter_source_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="graph implementation/artifact"):
        build_model(changed)
