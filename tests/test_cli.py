import json

import pytest
import torch

from universal_gnn.cli import main
from universal_gnn.engine.configuration import load_config, resolve_config
from universal_gnn.engine.training import run_training


@pytest.fixture
def inputs(tmp_path):
    data = tmp_path / "structures.json"
    data.write_text(json.dumps([{"id": "analytic", "numbers": [14, 8],
                                 "positions": [[.1, .2, .3], [1.2, .7, .5]],
                                 "cell": [[4., 0., 0.], [0., 4., 0.], [0., 0., 4.]],
                                 "pbc": [True] * 3, "targets": {"bandgap": 1.2}}]))
    config = {"seed": 123, "structures": 1, "epochs": 4, "checkpoint_every": 1,
              "backbone": {"name": "cgcnn", "width": 8, "layers": 1, "cutoff": 2.},
              "dataset": {"path": str(data)}, "task": {"kind": "supervised", "property": "bandgap"}}
    return data, config


def test_configuration_safe_yaml_and_cli_precedence(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text('backbone: {name: mace, width: 8}\ndataset: {path: old, sha256: stale}\n'
                    'task: {kind: supervised, property: formation_energy, unit: eV/atom}\nepochs: 2\n')
    resolved = resolve_config(load_config(path), model="alignn", dataset="new", task="bandgap", training=True)
    assert resolved["backbone"] == {"name": "alignn", "width": 8}
    assert resolved["dataset"] == {"path": "new"}
    assert resolved["task"] == {"kind": "supervised", "property": "bandgap"}
    assert resolved["checkpoint_every"] == 1
    path.write_text('!!python/object/apply:os.system ["echo unsafe"]')
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(path)
    path.write_text("- not_a_mapping")
    with pytest.raises(ValueError, match="mapping"):
        load_config(path)


def test_interruption_resume_matches_uninterrupted_adam(tmp_path, inputs):
    _, config = inputs
    run_training(config, tmp_path / "continuous")

    def interrupt(event, **values):
        if event == "epoch" and values["epoch"] == 2:
            raise InterruptedError("unit-test interruption")

    with pytest.raises(InterruptedError):
        run_training(config, tmp_path / "interrupted", event_callback=interrupt)
    report = run_training(config, tmp_path / "resumed", resume=tmp_path / "interrupted/checkpoint.pt")
    assert report["resume"]["kind"] == "full" and report["resume"]["completed_epochs_before"] == 2
    assert len(report["history"]) == 4
    expected = torch.load(tmp_path / "continuous/checkpoint.pt", weights_only=True)
    actual = torch.load(tmp_path / "resumed/checkpoint.pt", weights_only=True)
    for name in expected["state_dict"]:
        torch.testing.assert_close(actual["state_dict"][name], expected["state_dict"][name], rtol=0, atol=0)
    torch.testing.assert_close(actual["training_state"]["torch_rng_state"],
                               expected["training_state"]["torch_rng_state"], rtol=0, atol=0)
    changed = {**config, "dataset": {"path": config["dataset"]["path"],
                                   "bindings": {"bandgap": {"key": "bandgap", "factor": 2.}}}}
    with pytest.raises(ValueError, match="same selected structures"):
        run_training(changed, tmp_path / "bad-data", resume=tmp_path / "interrupted/checkpoint.pt")


def test_documented_flags_train_resume_infer_and_legacy(tmp_path, inputs, capsys):
    import yaml

    data, config = inputs
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    checkpoint = tmp_path / "weights/custom.pt"
    logging = tmp_path / "training-logs"
    common = ["--model", "alignn", "--task", "bandgap", "--dataset", str(data), "--config", str(path)]
    main(["--mode", "train", *common, "--epochs", "2", "--logging", str(logging), "--save", str(checkpoint)])
    assert checkpoint.is_file() and (logging / "report.json").is_file()
    main(["--mode", "train", *common, "--resume", str(checkpoint), "--epochs", "4",
          "--logging", str(logging), "--save", str(checkpoint)])
    events = [json.loads(line) for line in (logging / "events.jsonl").read_text().splitlines()]
    assert [event["epoch"] for event in events if event["event"] == "epoch"] == [1, 2, 3, 4]
    assert len({event["run_id"] for event in events}) == 2
    result = tmp_path / "predictions/prediction.json"
    main(["--mode", "infer", *common, "--resume", str(checkpoint), "--results", str(result),
          "--logging", str(tmp_path / "inference-logs")])
    prediction = json.loads(result.read_text())["predictions"]
    assert len(prediction["bandgap"]) == 1
    old_result = tmp_path / "old.json"
    main(["infer", str(checkpoint), str(data), "--output", str(old_result)])
    assert json.loads(old_result.read_text())["predictions"] == prediction
    with pytest.raises(SystemExit) as error:
        main(["--mode", "infer", "--model", "mace", "--resume", str(checkpoint), "--results", str(result)])
    assert error.value.code == 2 and "checkpoint backbone" in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        main(["--mode", "infer", "--task", "formation_energy", "--resume", str(checkpoint),
              "--results", str(result)])
    assert error.value.code == 2 and "Task setting" in capsys.readouterr().err


def test_generation_continuation_and_old_weights_warm_start(tmp_path, inputs):
    from universal_gnn.engine.training import build_model

    _, original = inputs
    config = {**original, "epochs": 3, "task": {"kind": "generation",
              "sampling": {"steps": 2, "inner_steps": 1, "seed": 456}}}
    run_training(config, tmp_path / "continuous-gen")
    run_training({**config, "epochs": 1}, tmp_path / "first-gen")
    report = run_training(config, tmp_path / "resumed-gen", resume=tmp_path / "first-gen/checkpoint.pt")
    expected = torch.load(tmp_path / "continuous-gen/checkpoint.pt", weights_only=True)
    actual = torch.load(tmp_path / "resumed-gen/checkpoint.pt", weights_only=True)
    assert report["resume"]["completed_epochs_before"] == 1
    for name in expected["state_dict"]:
        torch.testing.assert_close(actual["state_dict"][name], expected["state_dict"][name], rtol=0, atol=0)
    old = tmp_path / "weights-only.pt"
    torch.manual_seed(123)
    model = build_model(original).double()
    torch.save({"format_version": 2, "config": original, "state_dict": model.state_dict()}, old)
    report = run_training(original, tmp_path / "warm-start", resume=old)
    assert report["resume"]["kind"] == "weights_only" and report["resume"]["completed_epochs_before"] == 0


def test_cpu_snapshot_does_not_initialize_cuda(tmp_path, monkeypatch):
    from universal_gnn.engine.runtime import save_training_checkpoint

    def unexpected(*args):
        raise AssertionError("CPU checkpoint must not initialize a CUDA device")

    monkeypatch.setattr(torch.cuda, "get_rng_state", unexpected)
    monkeypatch.setattr(torch.cuda, "get_rng_state_all", unexpected)
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.Adam(model.parameters())
    path = tmp_path / "cpu.pt"
    save_training_checkpoint(path, model, optimizer, {}, {}, {})
    assert torch.load(path, weights_only=True)["training_state"]["cuda_rng_states"] is None
