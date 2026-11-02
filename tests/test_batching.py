import json

import pytest
import torch

from universal_gnn.data.indexed import JSONLStructures
from universal_gnn.engine.batching import batch_indices, batches
from universal_gnn.engine.training import dataset, run_training


def config_for(tmp_path, count=13):
    path = tmp_path / "structures.jsonl"
    records = [{"schema_version": 1, "id": f"s-{i}", "numbers": [1, 1],
                "positions": [[0., 0., 0.], [.8 + i * .01, .2, .1]],
                "cell": [[8., 0., 0.], [0., 8., 0.], [0., 0., 8.]], "pbc": [False] * 3,
                "targets": {"bandgap": 1. + i * .05}} for i in range(count)]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    return {"seed": 123, "epochs": 3, "batch_size": 4, "checkpoint_every": 1,
            "backbone": {"name": "gcn", "width": 8, "layers": 1},
            "graph": {"name": "knn", "k": 1}, "dataset": {"path": str(path)},
            "task": {"kind": "supervised", "property": "bandgap"}}


def test_all_data_indexing_selection_precision_and_atom_budget(tmp_path, monkeypatch):
    config = config_for(tmp_path)
    structures = dataset(config)
    assert len(structures) == 13 and isinstance(structures.source, JSONLStructures)
    assert structures[-1].identifier == "s-12"
    assert [len(batch.identifiers) for batch in batches(structures, config)] == [4, 4, 4, 1]
    assert all(batch.positions.dtype == torch.float32 for batch in batches(structures, config))
    limited = {**config, "structures": 5, "dataset": {**config["dataset"], "selection": "random"}}
    assert [s.identifier for s in dataset(limited)] == [s.identifier for s in dataset(limited)]
    assert [s.identifier for s in dataset(limited)] != [f"s-{i}" for i in range(5)]
    indices = list(batch_indices(structures, {**config, "max_atoms": 5}, epoch=2))
    assert all(len(batch) <= 2 for batch in indices)
    assert sorted(i for batch in indices for i in batch) == list(range(13))
    assert indices == list(batch_indices(structures, {**config, "max_atoms": 5}, epoch=2))
    with pytest.raises(ValueError, match="max_atoms"):
        list(batch_indices(structures, {**config, "max_atoms": 1}))
    # Constructing the index reads records but must not instantiate Structure tensors.
    import universal_gnn.data.indexed as indexed
    monkeypatch.setattr(indexed, "structure_from_record", lambda *a, **k: (_ for _ in ()).throw(AssertionError("eager")))
    assert len(JSONLStructures(config["dataset"]["path"])) == 13


def test_jsonl_duplicate_ids_and_empty_input_rejected(tmp_path):
    config = config_for(tmp_path, 2)
    path = tmp_path / "structures.jsonl"
    record = path.read_text().splitlines()[0]
    path.write_text(record + "\n" + record)
    with pytest.raises(ValueError, match="unique"):
        dataset(config)
    path.write_text("\n")
    with pytest.raises(ValueError, match="empty"):
        dataset(config)


@pytest.mark.parametrize("dtype", ["float32", "float64"])
def test_minibatch_training_resume_and_streamed_inference(tmp_path, dtype):
    from universal_gnn.engine.inference import run_inference

    config = {**config_for(tmp_path), "dtype": dtype}
    report = run_training(config, tmp_path / "continuous")
    assert report["selected_structures"] == 13 and len(report["structures"]) == 13
    run_training({**config, "epochs": 1}, tmp_path / "first")
    run_training(config, tmp_path / "resumed", resume=tmp_path / "first/checkpoint.pt")
    expected = torch.load(tmp_path / "continuous/checkpoint.pt", weights_only=True)
    actual = torch.load(tmp_path / "resumed/checkpoint.pt", weights_only=True)
    for name in expected["state_dict"]:
        torch.testing.assert_close(actual["state_dict"][name], expected["state_dict"][name], rtol=0, atol=0)
    with pytest.raises(ValueError, match="same batching"):
        run_training({**config, "batch_size": 3}, tmp_path / "bad", resume=tmp_path / "first/checkpoint.pt")
    checkpoint = tmp_path / "continuous/checkpoint.pt"
    batched = run_inference(checkpoint, config["dataset"]["path"], tmp_path / "batched.json")
    full = run_inference(checkpoint, config["dataset"]["path"], tmp_path / "full.json",
                         config_override={**expected["config"], "batch_size": 100})
    torch.testing.assert_close(torch.tensor(batched["predictions"]["bandgap"]),
                               torch.tensor(full["predictions"]["bandgap"]), rtol=1e-5, atol=1e-6)
    summary = run_inference(checkpoint, config["dataset"]["path"], tmp_path / "streamed.jsonl")
    records = [json.loads(line) for line in (tmp_path / "streamed.jsonl").read_text().splitlines()]
    assert summary["structure_count"] == 13 and summary["structures"] == []
    assert records[0]["type"] == "metadata" and records[-1]["type"] == "completed"
    assert [record["id"] for record in records[1:-1]] == [f"s-{i}" for i in range(13)]
    assert [row for record in records[1:-1] for row in record["predictions"]["bandgap"]] == batched["predictions"]["bandgap"]


def test_global_scales_and_loss_ignore_batch_boundaries_and_missing_values(tmp_path):
    from universal_gnn.engine.metrics import dataset_scales, loss_parts, LossTotals

    config = config_for(tmp_path)
    path = tmp_path / "structures.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    # Standard-v1 requires finite targets; the legacy reader permits masked missing labels.
    for record in records:
        record.pop("schema_version")
    records[-1]["targets"]["bandgap"] = float("nan")
    path.write_text("\n".join(json.dumps(record) for record in records))
    structures = dataset(config)
    scales = dataset_scales(structures, config)
    targets = torch.tensor([s.targets["bandgap"] for s in structures], dtype=torch.float64)
    assert scales["bandgap"] == pytest.approx(float(targets[torch.isfinite(targets)].std(unbiased=False)))
    losses = []
    for size in (4, 100):
        totals = LossTotals()
        for batch in batches(structures, {**config, "batch_size": size}):
            values = {"bandgap": batch.positions.new_zeros(batch.num_graphs, 1)}
            totals.add(loss_parts(values, batch, config, scales))
        losses.append(totals.loss(config))
    assert losses[0] == pytest.approx(losses[1], rel=1e-6)
