"""Numerical generation training checks; run through Slurm after Torch restoration."""

import copy
import hashlib
import json

import pytest
import torch

from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.generation import generation_batches
from universal_gnn.engine.training import dataset, run_training


def generation_config(tmp_path):
    path = tmp_path / "generation.jsonl"
    records = []
    for index in range(9):
        length = 4. if index < 5 else 10. if index < 7 else 12.
        records.append({"schema_version": 1, "id": f"generation-{index}", "numbers": [14, 8],
                        "positions": [[.1, .2, .3], [1.2 + .02 * index, .7, .5]],
                        "cell": [[length, 0., 0.], [0., length, 0.], [0., 0., length]],
                        "pbc": [True, True, True], "targets": {}})
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    roles = {record["id"]: "train" if index < 5 else "validation" if index < 7 else "test"
             for index, record in enumerate(records)}
    manifest = create_manifest([{"id": record["id"], "group": record["id"]} for record in records],
                               source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), official=roles)
    split = tmp_path / "split.json"
    split.write_text(json.dumps(manifest))
    return {"seed": 123, "dtype": "float64", "epochs": 2, "batch_size": 2, "checkpoint_every": 1,
            "report_predictions": False, "report_structure_limit": 2,
            "backbone": {"name": "cgcnn", "implementation": "legacy", "width": 8, "layers": 1, "cutoff": 2.},
            "dataset": {"path": str(path), "split_manifest": str(split), "partition": "train"},
            "task": {"kind": "generation", "sampling": {"steps": 2, "inner_steps": 1}}}


def corruptions(structures, config, **options):
    result = {}
    for clean, noisy, times, targets in generation_batches(structures, config, **options):
        for i, identifier in enumerate(clean.identifiers):
            start, end = int(clean.ptr[i]), int(clean.ptr[i + 1])
            result[identifier] = (noisy.positions[start:end].clone(), noisy.cell[i].clone(), times[i].clone(),
                                  targets["fractional_score"][start:end].clone(), targets["cell_score"][i].clone())
    return result


def test_actual_noise_changes_each_epoch_and_is_minibatch_order_independent(tmp_path):
    config = generation_config(tmp_path)
    structures = dataset(config)
    first = corruptions(structures, config, epoch=0)
    other = corruptions(structures, {**config, "batch_size": 4, "shuffle": False}, epoch=0)
    later = corruptions(structures, config, epoch=1)
    validation = corruptions(structures, config, phase="validation")
    for identifier in first:
        for a, b in zip(first[identifier], other[identifier]):
            torch.testing.assert_close(a, b, rtol=0, atol=0)
        assert not torch.equal(first[identifier][0], later[identifier][0])
        assert not torch.equal(first[identifier][0], validation[identifier][0])


def test_validation_selection_complete_test_and_no_training_sampling(tmp_path, monkeypatch):
    from universal_gnn.tasks.generation import PeriodicDenoiser

    config = generation_config(tmp_path)
    monkeypatch.setattr(PeriodicDenoiser, "sample", lambda *args, **kwargs: pytest.fail("Formal training must not sample all training structures"))
    events = []
    report = run_training(config, tmp_path / "run", event_callback=lambda event, **values: events.append((event, values)))
    assert report["passed"] and report["selected_structures"] == 5
    assert report["available_structures"] == 9
    assert report["config"]["generation_corruption"] == "per_epoch_structure_v2"
    prior = report["config"]["generation_prior"]
    assert prior["statistics"]["structures"] == 5
    assert prior["statistics"]["volume_per_atom"] == pytest.approx(32.)
    assert prior["sampling_volume_source"] == "train_fit"
    heldout = report["heldout"]
    assert heldout["structures"] == heldout["validation_structures"] == 2
    records = [json.loads(line) for line in open(heldout["predictions"], encoding="utf-8")]
    assert {row["id"] for row in records} == {"generation-7", "generation-8"}
    assert all(row["noise_phase"] == "test" for row in records)
    assert heldout["metrics"]["fractional_score"]["finite_elements"] == 12
    tracker = heldout["selection"]["tracker"]
    best = min(tracker["history"], key=lambda row: row["loss"])
    assert tracker["best_epoch"] == best["epoch"]
    assert tracker["best_loss"] == best["loss"]
    assert len([event for event, _ in events if event == "validation"]) == 2
    assert report["generation"] == {}
    assert "quality" in report["interpretation"]


def test_full_resume_matches_fresh_noise_continuous_training(tmp_path):
    config = generation_config(tmp_path)
    run_training(config, tmp_path / "continuous")
    run_training({**config, "epochs": 1}, tmp_path / "first")
    report = run_training(config, tmp_path / "resumed", resume=tmp_path / "first/checkpoint.pt")
    expected = torch.load(tmp_path / "continuous/checkpoint.pt", weights_only=True)
    actual = torch.load(tmp_path / "resumed/checkpoint.pt", weights_only=True)
    for name in expected["state_dict"]:
        torch.testing.assert_close(actual["state_dict"][name], expected["state_dict"][name], rtol=0, atol=0)
    assert expected["training_state"]["history"] == actual["training_state"]["history"]
    assert report["resume"]["completed_epochs_before"] == 1
    assert report["heldout"]["selection"]["tracker"] == expected["training_state"]["evaluation"]["tracker"]
    changed = {**config, "generation_corruption": "per_structure_v1"}
    with pytest.raises(ValueError, match="same generation corruption"):
        run_training(changed, tmp_path / "wrong-objective", resume=tmp_path / "first/checkpoint.pt")
    changed = copy.deepcopy(config)
    changed["task"]["sampling"]["steps"] = 3
    with pytest.raises(ValueError, match="same declared generation sampling"):
        run_training(changed, tmp_path / "wrong-sampling", resume=tmp_path / "first/checkpoint.pt")


def test_training_prior_tamper_and_training_partition_sampling_rejected(tmp_path):
    config = generation_config(tmp_path)
    with pytest.raises(ValueError, match="separate quality evaluation"):
        run_training({**config, "validate_sampling": True}, tmp_path / "sampling")
    changed = copy.deepcopy(config)
    changed["generation_prior"] = {"statistics": {"structures": 100}}
    with pytest.raises(ValueError, match="prior differs"):
        run_training(changed, tmp_path / "prior")
    changed = copy.deepcopy(config)
    changed["dataset"]["partition"] = "test"
    with pytest.raises(ValueError, match="partition=train"):
        run_training(changed, tmp_path / "test-training")


def test_denoising_training_and_capacity_loss_respect_declared_weights():
    from universal_gnn.engine.generation import denoising_parts
    from universal_gnn.engine.metrics import weighted_loss

    targets = {"fractional_score": torch.zeros((2, 3)), "cell_score": torch.zeros((1, 6))}
    prediction = {"fractional_score": torch.ones((2, 3)), "cell_score": torch.full((1, 6), 2.)}
    config = {"task": {"kind": "generation", "loss_weights": {"fractional_score": .25, "cell_score": 2.}}}
    assert float(weighted_loss(denoising_parts(prediction, targets), config)) == pytest.approx(8.25)
