"""Training route integration; execute under Slurm after automatic preparation is wired."""
import pytest
import torch

@pytest.mark.parametrize("generation", [False, True])
@pytest.mark.parametrize("resume", [False, True])
def test_training_prepares_bound_statistics_before_constructing_scratch(tmp_path, monkeypatch, generation, resume):
    from copy import deepcopy
    from universal_gnn.engine import training, runtime, generation as generation_engine
    from universal_gnn.engine.initialization import neighbors

    config = dict(backbone=dict(name="mace", implementation="official", initialization="scratch"),
                  dataset=dict(path="fixture.jsonl", split_manifest="fixture-split.json", partition="train"),
                  task=dict(kind="generation") if generation else dict(kind="supervised", property="bandgap"),
                  structures="all", dtype="float32", generation_corruption="per_epoch_structure_v2")
    statistics = {"fixture": "bound-training-statistics"}
    selected = [object(), object()]
    events = []
    artifact = {"fixture": "embedded-source"}
    if resume:
        saved_config = deepcopy(config)
        saved_config["backbone"]["neighbor_statistics"] = deepcopy(statistics)
        saved = dict(format_version=2, config=saved_config, official_backbone=artifact, training_state={})
        monkeypatch.setattr(torch, "load", lambda *args, **kwargs: saved)

    def prepare(value, structures, *, official_artifact=None):
        assert structures is selected
        if resume:
            assert value["backbone"]["neighbor_statistics"] == statistics
            assert official_artifact == artifact
        else:
            assert "neighbor_statistics" not in value["backbone"]
            assert official_artifact is None
        events.append("prepare")
        resolved = deepcopy(value)
        resolved["backbone"]["neighbor_statistics"] = deepcopy(statistics)
        return resolved

    def construct(value, **options):
        assert events == ["prepare"]
        assert value["backbone"]["neighbor_statistics"] == statistics
        raise RuntimeError("fixture-stop-after-resolution")

    monkeypatch.setattr(training, "dataset", lambda value: selected)
    monkeypatch.setattr(training, "build_model", construct)
    monkeypatch.setattr(runtime, "data_fingerprint", lambda structures: "a" * 64)
    monkeypatch.setattr(neighbors, "prepare_native_neighbors", prepare)
    monkeypatch.setattr(generation_engine, "resolve_sampling_prior", lambda *args: None)
    with pytest.raises(RuntimeError, match="fixture-stop-after-resolution"):
        training.run_training(config, tmp_path / "run", resume=tmp_path / "saved.pt" if resume else None)
    assert "neighbor_statistics" not in config["backbone"]


def test_backbone_warm_start_conflict_fails_before_native_data_scan(tmp_path, monkeypatch):
    from universal_gnn.engine import training

    config = dict(backbone=dict(name="mace", initialization="scratch"),
                  dataset=dict(path="never-read.jsonl"), task=dict(kind="supervised", property="bandgap"))
    monkeypatch.setattr(training, "dataset", lambda value: pytest.fail("Conflicting warm-start must fail before scanning data"))
    with pytest.raises(ValueError, match="scratch backbone"):
        training.run_training(config, tmp_path / "run", warm_start=tmp_path / "never-read.pt")
