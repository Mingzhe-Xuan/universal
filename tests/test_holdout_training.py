"""Numerical integration: run on Guqq2 through Slurm, never on its login node."""

import copy
import hashlib
import json

import pytest
import torch

from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.training import dataset, run_training


def fixture_config(tmp_path, *, property_name="bandgap"):
    records = [{"schema_version": 1, "id": f"s{i}", "numbers": [1, 1],
                "positions": [[0., 0., 0.], [.7 + .01 * i, .2, .1]],
                "cell": [[8., 0., 0.], [0., 8., 0.], [0., 0., 8.]], "pbc": [False] * 3,
                "targets": {"bandgap": 1. + .05 * i, "classification": i % 2,
                            "dielectric": [[1., 0., 0.], [0., 2., 0.], [0., 0., 3.]],
                            "forces": [[.1, .2, .3], [-.1, -.2, -.3]]}} for i in range(20)]
    path = tmp_path / "structures.jsonl"
    groups = [{"id": r["id"], "group": r["id"]} for r in records]
    manifest = create_manifest(groups, source_sha256="0" * 64, seed=7)
    for i in manifest["partitions"]["test"]:
        records[i]["targets"]["bandgap"] = 1e6
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    manifest["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    split = tmp_path / "split.json"
    split.write_text(json.dumps(manifest), encoding="utf-8")
    config = {"seed": 123, "epochs": 3, "batch_size": 3, "dtype": "float32", "checkpoint_every": 1,
              "backbone": {"name": "gcn", "width": 8, "layers": 1}, "graph": {"name": "knn", "k": 1},
              "dataset": {"path": str(path), "split_manifest": str(split), "partition": "train"},
              "task": {"kind": "supervised", "property": property_name}, "evaluation": {"patience": None}}
    return config, manifest


def test_training_partition_train_scales_best_selection_and_test_tail(tmp_path):
    config, manifest = fixture_config(tmp_path)
    selected = dataset(config)
    assert [s.identifier for s in selected] == [f"s{i}" for i in manifest["partitions"]["train"]]
    limited = {**config, "structures": 4, "dataset": {**config["dataset"], "selection": "random"}}
    assert [s.identifier for s in dataset(limited)] == [s.identifier for s in dataset(limited)]
    assert set(s.identifier for s in dataset(limited)) <= set(s.identifier for s in selected)
    report = run_training(config, tmp_path / "trained")
    last = torch.load(report["checkpoint"], weights_only=True)
    best = torch.load(report["best_checkpoint"], weights_only=True)
    assert "training_state" not in best
    target = torch.tensor([s.targets["bandgap"] for s in selected], dtype=torch.float64)
    assert last["scales"]["bandgap"] == pytest.approx(float(target.std(unbiased=False)))
    tracker = report["heldout"]["selection"]["tracker"]
    assert tracker["best_loss"] == min(item["loss"] for item in tracker["history"])
    assert report["heldout"]["test_structures"] == 2
    predictions = [json.loads(line) for line in open(report["heldout"]["predictions"], encoding="utf-8")]
    assert {r["id"] for r in predictions} == {f"s{i}" for i in manifest["partitions"]["test"]}
    assert report["heldout"]["metrics"]["bandgap"]["mae"] > 1e5
    from universal_gnn.engine.inference import run_inference
    inference = run_inference(report["best_checkpoint"], config["dataset"]["path"], tmp_path / "test-inference.jsonl",
                              config_override={**best["config"], "dataset": {**config["dataset"], "partition": "test"}})
    assert inference["structure_count"] == 2
    external = tmp_path / "external.jsonl"
    external.write_bytes((tmp_path / "structures.jsonl").read_bytes())
    external_result = run_inference(report["best_checkpoint"], external, tmp_path / "external-predictions.jsonl")
    assert external_result["structure_count"] == 20
    assert "split_manifest" not in external_result["config"]["dataset"]


def test_resume_preserves_validation_selection_and_exact_weights(tmp_path):
    config, _ = fixture_config(tmp_path)
    continuous = run_training(config, tmp_path / "continuous")
    first = run_training({**config, "epochs": 1}, tmp_path / "first")
    resumed = run_training(config, tmp_path / "resumed", resume=first["checkpoint"])
    for role in ("checkpoint", "best_checkpoint"):
        a = torch.load(continuous[role], weights_only=True)
        b = torch.load(resumed[role], weights_only=True)
        for name, value in a["state_dict"].items():
            torch.testing.assert_close(value, b["state_dict"][name], rtol=0, atol=0)
    assert continuous["heldout"]["selection"]["tracker"] == resumed["heldout"]["selection"]["tracker"]
    with pytest.raises(ValueError, match="protocol"):
        run_training({**config, "evaluation": {"patience": 2}}, tmp_path / "bad-protocol", resume=first["checkpoint"])


def test_early_stopping_and_missing_previous_best_fail_closed(tmp_path):
    config, _ = fixture_config(tmp_path)
    config.update(epochs=8, evaluation={"patience": 1, "min_delta": 1e9})
    report = run_training(config, tmp_path / "stopped")
    assert report["early_stopped"] and report["completed_epochs"] == 2 and report["requested_epochs"] == 8
    from pathlib import Path
    Path(report["best_checkpoint"]).unlink()
    with pytest.raises(ValueError, match="previous validation-best"):
        run_training(config, tmp_path / "missing-best", resume=report["checkpoint"])


@pytest.mark.parametrize("task", ["classification", "dielectric", "forces"])
def test_heldout_classification_tensor_and_force_derivatives(tmp_path, task):
    config, _ = fixture_config(tmp_path, property_name=task if task != "forces" else "bandgap")
    config["epochs"] = 1
    if task == "forces":
        config["task"] = {"kind": "forcefield", "supervised_outputs": ["forces"]}
        config["prediction"] = {"version": 1, "readout": {"name": "node_mlp", "pooling": "sum", "hidden_features": [8]}}
    elif task == "dielectric":
        config["prediction"] = {"version": 1, "readout": {"name": "response", "pooling": "mean"}}
    report = run_training(config, tmp_path / task)
    metrics = report["heldout"]["metrics"][task]
    assert metrics["structures"] == 2
    if task == "classification":
        assert sum(sum(row) for row in metrics["confusion_matrix_true_by_predicted"]) == 2
    else:
        assert metrics["finite_elements"] == (12 if task == "forces" else 18)
