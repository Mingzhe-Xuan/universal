"""Actual quality engine/error accounting controls; CPU Slurm only."""

import copy
import hashlib
import json
import os

import pytest
import torch

from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.training import run_training
from universal_gnn.engine.generative.quality import run_generation_quality
from universal_gnn.tasks.generation import PeriodicDenoiser
from universal_gnn.benchmarks.generation.sampling_failures import invalid_geometry_attempts
from test_generation_heldout_runtime import generation_config


def test_actual_engine_retains_all_thousand_known_guard_failures(tmp_path, monkeypatch):
    assert os.environ.get("SLURM_JOB_ID"), "Numerical acceptance runs through Slurm"
    config = generation_config(tmp_path)
    path = tmp_path / "generation.jsonl"
    original = [json.loads(line) for line in path.read_text().splitlines()]
    records = original[:7] + [{**copy.deepcopy(original[7]), "id": "condition-" + str(i)} for i in range(200)]
    path.write_text("".join(json.dumps(row) + "\n" for row in records))
    roles = {row["id"]: "train" if i < 5 else "validation" if i < 7 else "test" for i, row in enumerate(records)}
    manifest = create_manifest([dict(id=row["id"], group=row["id"]) for row in records],
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), official=roles)
    (tmp_path / "split.json").write_text(json.dumps(manifest))
    config.update(epochs=1, validate_sampling=False)
    config["task"]["sampling"] = dict(steps=100, inner_steps=2)
    trained = run_training(config, tmp_path / "train")
    seen = []
    def guard(model, batch, *, seed, **options):
        assert batch.num_graphs == 1 and not torch.count_nonzero(batch.positions)
        assert options["steps"] == 100 and options["inner_steps"] == 2
        assert all(not targets for targets in batch.targets)
        seen.append(seed)
        raise ValueError("Cell requires 51129 periodic images; check cell/cutoff")
    monkeypatch.setattr(PeriodicDenoiser, "sample", guard)
    with invalid_geometry_attempts(PeriodicDenoiser):
        result = run_generation_quality(trained["checkpoint"], tmp_path / "quality", count=1000,
                                        draws_per_condition=5, seed=456, device="cpu")
    assert PeriodicDenoiser.sample is guard
    assert result["attempted"] == result["requested_samples"] == len(set(seen)) == 1000
    assert result["selected_test_conditions"] == 200 and result["geometric_validity"] == 0.
    assert result["execution_complete"] and result["meets_v1_sample_count"]
    rows = [json.loads(line) for line in (tmp_path / "quality/samples.jsonl").read_text().splitlines()]
    assert len(rows) == 1000 and len({(r["condition_id"], r["draw"]) for r in rows}) == 1000
    assert all(r["structure"] is None and not r["quality"]["geometrically_valid"] for r in rows)
    assert all("periodic_image_budget_guard" in r["quality"]["reason"] for r in rows)
    report_dir = os.environ.get("UGNN_STAGED_GENERATION_RUNTIME_REPORTS")
    if report_dir:
        from pathlib import Path
        output = Path(report_dir);output.mkdir(parents=True, exist_ok=True)
        value = dict(status="passed", kind="controlled_failure_accounting_not_model_quality", attempted=1000,
                     conditions=200, draws=5, sampling=result["sampling"], seed=456, device="cpu",
                     unique_seeds=len(set(seen)), invalid_attempts=1000, samples_sha256=hashlib.sha256(
                         (tmp_path / "quality/samples.jsonl").read_bytes()).hexdigest())
        (output / "known-invalid-1000.json").write_text(json.dumps(value, indent=2))


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError, torch.cuda.OutOfMemoryError])
def test_actual_engine_propagates_unknown_and_oom_without_fake_completion(tmp_path, monkeypatch, error_type):
    assert os.environ.get("SLURM_JOB_ID"), "Numerical acceptance runs through Slurm"
    config = generation_config(tmp_path)
    trained = run_training({**config, "epochs": 1}, tmp_path / "train")
    error = error_type("Controlled unknown or OOM; no allocation")
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(PeriodicDenoiser, "sample", fail)
    with invalid_geometry_attempts(PeriodicDenoiser), pytest.raises(error_type) as caught:
        run_generation_quality(trained["checkpoint"], tmp_path / "quality", count=2,
                               draws_per_condition=1, seed=456, device="cpu")
    assert caught.value is error
    assert not (tmp_path / "quality/metrics.json").exists()
