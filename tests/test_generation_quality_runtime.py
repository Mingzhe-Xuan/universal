"""Actual Pymatgen/ASE and Torch quality tests; Slurm only."""

from dataclasses import replace
import json

import pytest
import torch

from universal_gnn.contracts import Structure
from universal_gnn.engine.generative.quality import StructuralQuality, run_generation_quality
from universal_gnn.engine.training import run_training
from test_generation_heldout_runtime import generation_config


def reference_structure():
    return Structure(torch.tensor([14, 8]), torch.tensor([[0., 0., 0.], [1.2, 1., .5]], dtype=torch.float64),
                     torch.eye(3, dtype=torch.float64) * 4., torch.ones(3, dtype=torch.bool), "reference")


def record(structure):
    return {"id": structure.identifier, "numbers": structure.numbers.tolist(), "positions": structure.positions.tolist(),
            "cell": structure.cell.tolist(), "pbc": structure.pbc.tolist()}


def test_match_uniqueness_novelty_periodic_collision_and_distributions():
    reference = reference_structure()
    scorer = StructuralQuality([reference], record=record)
    first = scorer.update(record(reference), record(reference))
    second = scorer.update(record(reference), record(reference))
    assert first["geometrically_valid"] and first["unique"] and not first["novel_to_train"]
    assert first["matches_assigned_reference"] and first["normalized_rms"] == pytest.approx(0., abs=1e-10)
    assert not second["unique"]
    collision = replace(reference, positions=torch.zeros_like(reference.positions))
    invalid = scorer.update(record(collision), record(reference))
    assert not invalid["geometrically_valid"] and invalid["reason"] == "periodic_distance_below_threshold"
    result = scorer.result()
    assert result["attempted"] == 3 and result["geometric_validity"] == pytest.approx(2/3)
    assert result["uniqueness_among_valid"] == .5 and result["novelty_among_valid"] == 0.
    assert result["paired_match_rate"] == pytest.approx(2/3)
    assert result["valid_samples_with_training_seen_composition"] == 2
    assert result["novelty_among_valid_with_training_seen_composition"] == 0.
    assert result["distribution_wasserstein_1"] == {"volume_per_atom_angstrom3": 0., "density_g_cm3": 0.}


def test_unseen_composition_novelty_and_numerical_failures_disclosed():
    training = reference_structure()
    carbon = replace(training, numbers=torch.tensor([6, 6]))
    scorer = StructuralQuality([training], record=record)
    result = scorer.update(record(carbon), record(carbon))
    assert result["novel_to_train"]
    summary = scorer.result()
    assert summary["novelty_among_valid"] == 1.
    assert summary["novelty_among_valid_with_training_seen_composition"] is None
    assert summary["valid_samples_with_training_seen_composition"] == 0
    failed = StructuralQuality([training], record=record)
    assert not failed.update(None, record(training), failure="nonfinite sampler")["geometrically_valid"]
    summary = failed.result()
    assert summary["attempted"] == 1 and summary["geometric_validity"] == 0.
    assert summary["uniqueness_among_valid"] is None
    assert all(value is None for value in summary["distribution_wasserstein_1"].values())
    with pytest.raises(ValueError, match="composition"):
        StructuralQuality([training], record=record).update(record(carbon), record(training))


def test_quality_uses_verified_best_heldout_conditions_and_erased_reference_geometry(tmp_path, monkeypatch):
    from universal_gnn.tasks.generation import PeriodicDenoiser

    config = generation_config(tmp_path)
    run_training(config, tmp_path / "train")
    seeds = []
    def sample(model, batch, *, seed, **options):
        seeds.append(seed)
        assert batch.num_graphs == 1
        assert torch.count_nonzero(batch.positions) == 0
        torch.testing.assert_close(batch.cell[0], torch.eye(3, dtype=batch.cell.dtype) * 4.)
        assert all(not targets for targets in batch.targets)
        positions = batch.positions.new_tensor([[0., 0., 0.], [1.2, 1., .5]])
        return batch.with_geometry(positions, batch.cell)
    monkeypatch.setattr(PeriodicDenoiser, "sample", sample)
    result = run_generation_quality(tmp_path / "train/checkpoint.pt", tmp_path / "quality", count=2,
                                    draws_per_condition=2, seed=7, device="cpu")
    assert result["execution_complete"] and result["attempted"] == 2
    assert result["selected_test_conditions"] == 1 and result["draws_per_condition"] == 2
    assert result["available_test_conditions"] == 2
    assert result["full_training_partition"] and not result["meets_v1_sample_count"]
    assert result["checkpoint_role"] == "validation_best" and result["partition"] == "test"
    assert len(set(seeds)) == 2
    records = [json.loads(line) for line in (tmp_path / "quality/samples.jsonl").read_text().splitlines()]
    assert all(row["condition_id"] in {"generation-7", "generation-8"} for row in records)
    assert {row["draw"] for row in records} == {0, 1}
    assert result["geometric_validity"] == 1. and result["uniqueness_among_valid"] == .5
    with pytest.raises(ValueError, match="validation selection history"):
        run_generation_quality(tmp_path / "train/checkpoint.best.pt", tmp_path / "no-history", count=2,
                               draws_per_condition=1, device="cpu")


def test_sampling_oom_is_not_counted_as_an_invalid_scientific_sample(tmp_path, monkeypatch):
    from universal_gnn.tasks.generation import PeriodicDenoiser

    config = generation_config(tmp_path)
    run_training({**config, "epochs": 1}, tmp_path / "train")
    def oom(*args, **kwargs):
        raise torch.cuda.OutOfMemoryError("fixture OOM; no allocation")
    monkeypatch.setattr(PeriodicDenoiser, "sample", oom)
    with pytest.raises(torch.cuda.OutOfMemoryError):
        run_generation_quality(tmp_path / "train/checkpoint.pt", tmp_path / "oom", count=2,
                               draws_per_condition=1, device="cpu")
    assert not (tmp_path / "oom/metrics.json").exists()


@pytest.mark.parametrize('location', ['nodes', 'graph_features'])
def test_actual_nonfinite_feature_validation_is_recorded_for_every_condition(tmp_path, monkeypatch, location):
    from universal_gnn.contracts import NativeFeatures
    from universal_gnn.tasks.generation import PeriodicDenoiser
    config = generation_config(tmp_path)
    run_training({**config, 'epochs': 1}, tmp_path / 'train')
    def sample(model, batch, **options):
        nodes = batch.positions.new_ones((len(batch.numbers), 1))
        graphs = batch.positions.new_ones((batch.num_graphs, 1))
        (nodes if location == 'nodes' else graphs).fill_(float('nan'))
        NativeFeatures(nodes, '1x0e', 'invariant', batch.batch, batch.ptr, batch,
                       graph_features=graphs).validate()
        pytest.fail('Nonfinite features passed validation')
    monkeypatch.setattr(PeriodicDenoiser, 'sample', sample)
    result = run_generation_quality(tmp_path / 'train/checkpoint.pt', tmp_path / 'invalid', count=2,
                                    draws_per_condition=1, device='cpu')
    assert result['execution_complete'] and result['attempted'] == 2
    assert result['geometric_validity'] == 0 and result['geometrically_valid'] == 0
    rows = [json.loads(line) for line in (tmp_path / 'invalid/samples.jsonl').read_text().splitlines()]
    assert len(rows) == 2 and len({row['condition_id'] for row in rows}) == 2
    assert all(row['structure'] is None and not row['quality']['geometrically_valid'] for row in rows)
    assert all('Nonfinite' in row['quality']['reason'] for row in rows)


def test_shape_contract_errors_still_stop_quality_instead_of_becoming_invalid_samples(tmp_path, monkeypatch):
    from universal_gnn.contracts import NativeFeatures
    from universal_gnn.tasks.generation import PeriodicDenoiser
    config = generation_config(tmp_path)
    run_training({**config, 'epochs': 1}, tmp_path / 'train')
    def sample(model, batch, **options):
        NativeFeatures(batch.positions.new_zeros((len(batch.numbers), 2)), '1x0e', 'invariant',
                       batch.batch, batch.ptr, batch).validate()
    monkeypatch.setattr(PeriodicDenoiser, 'sample', sample)
    with pytest.raises(ValueError, match='Node dimensions'):
        run_generation_quality(tmp_path / 'train/checkpoint.pt', tmp_path / 'bad-shape', count=2,
                               draws_per_condition=1, device='cpu')
    assert not (tmp_path / 'bad-shape/metrics.json').exists()
