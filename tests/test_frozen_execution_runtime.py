"""Actual full-training/checkpoint/post oracles, exclusively in CPU Slurm."""

import copy
import json
import os
from pathlib import Path

import pytest
import torch

from universal_gnn.benchmarks.execution.gates import canonical_digest, file_sha
from universal_gnn.benchmarks.frozen_backbones import execution as frozen
from universal_gnn.benchmarks.frozen_backbones.training_audit import audited_training, check_training_audit
from universal_gnn.benchmarks.frozen_backbones.worker import state_sha
from universal_gnn.benchmarks.prediction_assessment import runtime
from universal_gnn.benchmarks.prediction_assessment.numerics import forbid_models
from universal_gnn.benchmarks.prediction_assessment.contracts import UNITS
from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
from universal_gnn.data.splits import create_manifest
from universal_gnn.engine.optimization import components
from universal_gnn.engine.training import build_model, run_training, load_checkpoint
from test_physical_task_validation import configured


@pytest.mark.parametrize("kind", ["forcefield", "fixed_frame", "equivariant"])
@pytest.mark.parametrize("dtype", ["float32", "float64"])
def test_real_full_frozen_training_checkpoints_and_saved_output_acceptance(kind, dtype, tmp_path, monkeypatch):
    assert os.environ.get("SLURM_JOB_ID"), "Numerical training controls require Slurm"
    _, structures, config = configured(kind)
    config = copy.deepcopy(config)
    config.update(seed=123, device="cpu", dtype=dtype, epochs=3, batch_size=2, structures="all",
                  max_atoms=None, report_predictions=False, report_structure_limit=0, checkpoint_every=1,
                  evaluation=dict(patience=2, min_delta=0.))
    config["optimization"]["train_backbone"] = False
    task = "forcefield" if kind == "forcefield" else "dielectric"
    names = ["total_energy", "forces"] if task == "forcefield" else ["dielectric"]
    if task == "forcefield":config["task"]["supervised_outputs"] = names
    records = []
    for i in range(7):
        structure = structures[i % 2]
        labels = dict(total_energy=0. if i == 0 else .1 * i,
                      forces=[[0., 0., 0.]] * 3) if task == "forcefield" else dict(
                          dielectric=[[0. if i == 0 else .1 * i if a == b else .01 * i for b in range(3)] for a in range(3)])
        records.append(dict(id=str(i), numbers=structure.numbers.tolist(), positions=structure.positions.tolist(),
            cell=structure.cell.tolist(), pbc=structure.pbc.tolist(), targets=labels))
    source = tmp_path / "source.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in records))
    manifest = create_manifest([dict(id=str(i), group=str(i)) for i in range(7)], source_sha256=file_sha(source),
        official={str(i): "train" if i < 3 else "validation" if i < 5 else "test" for i in range(7)})
    split = tmp_path / "split.json";split.write_text(json.dumps(manifest))
    config["dataset"] = dict(path=str(source), sha256=file_sha(source), partition="train",
        split_manifest=str(split), split_manifest_sha256=canonical_digest(manifest),
        bindings={name: dict(key=name, unit=UNITS[name]) for name in names})
    torch.manual_seed(123)
    original = build_model(config).to(device="cpu", dtype=getattr(torch, dtype))
    original_body = state_sha(components(original)["backbone"])
    events = []
    trained = audited_training(config, tmp_path / "audited", event_callback=lambda event, **kw: events.append(dict(event=event, **kw)))
    audited_rng = torch.get_rng_state()
    # Control the observer's end-of-training CPU checkpoint reloads as well, so
    # comparison covers both actual optimization and final global RNG state.
    control = run_training(config, tmp_path / "control")
    for key in ("best_checkpoint", "checkpoint"):
        load_checkpoint(control[key], device="cpu")
    assert torch.equal(torch.get_rng_state(), audited_rng)
    assert trained["history"] == control["history"]
    for key in ("best_checkpoint", "checkpoint"):
        actual = torch.load(trained[key], map_location="cpu", weights_only=True)["state_dict"]
        expected = torch.load(control[key], map_location="cpu", weights_only=True)["state_dict"]
        assert actual.keys() == expected.keys()
        assert all(torch.equal(value, expected[name]) for name, value in actual.items())
    assert trained["selected_structures"] == 3 and trained["heldout"]["test_structures"] == 2
    assert trained["backbone_gradient_norms"] == [0.] * trained["completed_epochs"]
    assert all(value > 0 for value in trained["gradient_norms"])
    gate = dict(case=dict(task=task, run_directory=str(tmp_path / "audited")), config=trained["config"],
        counts=dict(train=3, validation=2, test=2), source_structures=7,
        frozen_audit=dict(backbone_state_before_sha256=original_body), kind="formal_frozen_backbone_execution_gate")
    accepted = check_training_audit(trained, gate)
    assert accepted["optimizer_steps"] == 2 * trained["completed_epochs"]
    best = load_checkpoint(trained["best_checkpoint"], device="cpu")
    assert state_sha(components(best)["backbone"]) == original_body
    data = runtime.numerics.trained_physics(trained["best_checkpoint"], trained["config"], [0, 1])
    assert data["passed"] and data["mixed_parameter_gradient_norms"]["backbone"] == 0.
    assert data["mixed_parameter_gradient_norms"]["readout"] > 1e-10
    result = None
    if dtype == "float32":
        # Domain selection/official CUDA evidence have separate protocol tests;
        # this small numerical oracle cannot qualify an official frozen case.
        reference = tmp_path / "reference";reference.mkdir()
        scan = reference / "graph-scan";scan.mkdir()
        (scan / "probe.json").write_text(json.dumps(dict(worst_indices=[0, 1])))
        (reference / "report.json").write_text("{}")
        prep = tmp_path / "prep";prep.mkdir()
        (prep / "report.json").write_text(json.dumps(dict(reference_preparation=str(reference))))
        gate.update(preparation=str(prep), reference_preparation=str(reference))
        report_path = tmp_path / "audited/report.json"
        paths = [report_path, Path(trained["best_checkpoint"]), Path(trained["checkpoint"]),
                 Path(trained["heldout"]["predictions"]), source, split, tmp_path / "audited/frozen-training-audit.json"]
        context = dict(spec=dict(matrix_sha256="small-numerical-control"), gate=gate, trained=trained,
            report_path=report_path, git_commit=trained["execution"]["git_commit"], verified_training=dict(frozen_training=accepted),
            input_sha256={str(path): file_sha(path) for path in paths})
        monkeypatch.setattr(frozen, "frozen_context", lambda settings, identifier: context)
        post = frozen.postprocess_frozen_case({}, "small-numerical-control", tmp_path / "post")
        with forbid_models():
            result = frozen.verify_frozen_case({}, "small-numerical-control", tmp_path / "post", tmp_path / "verify")
        assert post["status"] == result["status"] == "passed"
        assert result["model_execution_forbidden"] and result["inference_verification"]["structures"] == 7
        if task == "dielectric":
            raw = json.loads((tmp_path / "verify/heldout/report.json").read_text())
            assert raw["tensor_groups"]["overall"]["metrics"]["structures"] == 2
    if os.environ.get("UGNN_FROZEN_EXECUTION_REPORTS"):
        output = Path(os.environ["UGNN_FROZEN_EXECUTION_REPORTS"]);output.mkdir(parents=True, exist_ok=True)
        report = dict(status="passed", kind=kind, dtype=dtype, identical_training_state_and_rng=True,
            training=accepted, physics=data, independent_no_model=result,
            completed_epochs=trained["completed_epochs"], counts=gate["counts"], original_source_structures=7,
            zero_label_training_records_preserved=1, official_frozen_training_runs=0,
            interpretation="Small CPU training/checkpoint/post oracle; no official CUDA or full-data acceptance")
        (output / (kind + "-" + dtype + ".json")).write_text(json.dumps(report, indent=2, allow_nan=False))
