import copy
import json

import pytest
import torch

from universal_gnn.contracts import StructureBatch
from universal_gnn.contracts.schema import validate_config
from universal_gnn.engine.metrics import dataset_scales, loss_parts, weighted_loss
from universal_gnn.engine.runtime import check_model_config
from universal_gnn.engine.training import dataset, loss_for
from universal_gnn.tasks.supervision import supervised_outputs


def config_for(tmp_path):
    path = tmp_path / "force-labels.jsonl"
    path.write_text(json.dumps({"schema_version": 1, "id": "analytic-force-test", "numbers": [1, 1],
        "positions": [[.1, .2, .3], [.8, .5, .7]], "pbc": [False] * 3,
        "targets": {"F": [[-.2, -.4, -.6], [-1.6, -1., -1.4]]}}) + "\n")
    return {"backbone": {"name": "gcn"}, "dataset": {"path": str(path), "bindings": {
        "total_energy": {"key": "absent-energy"}, "forces": {"key": "F"},
        "stress": {"key": "absent-stress"}}},
        "task": {"kind": "forcefield", "supervised_outputs": ["forces"]}}


@pytest.mark.parametrize("selection", [[], "forces", None, ["energy"], ["forces", "forces"], [3]])
def test_invalid_supervision_fails_configuration_preflight(selection):
    config = {"task": {"kind": "forcefield", "supervised_outputs": selection}}
    with pytest.raises(ValueError, match="supervised_outputs"):
        validate_config(config)
    with pytest.raises(ValueError, match="only supported for forcefield"):
        validate_config({"task": {"kind": "supervised", "property": "bandgap",
                                  "supervised_outputs": ["forces"]}})


def test_checkpoint_supervision_normalizes_order_and_preserves_old_default():
    config = {"backbone": {"name": "gcn"}, "task": {"kind": "forcefield"}}
    assert supervised_outputs(config) == ("total_energy", "forces", "stress")
    explicit = copy.deepcopy(config)
    explicit["task"]["supervised_outputs"] = ["stress", "forces", "total_energy"]
    check_model_config(config, explicit)
    explicit["task"]["supervised_outputs"] = ["forces"]
    with pytest.raises(ValueError, match="Supervised outputs"):
        check_model_config(config, explicit)


def test_force_only_labels_mixed_gradient_and_unidentified_energy_offset(tmp_path):
    config = config_for(tmp_path)
    structures = dataset(config)
    assert set(structures[0].targets) == {"forces"}
    scales = dataset_scales(structures, config)
    assert set(scales) == {"forces"}
    batch = StructureBatch.from_structures(list(structures))
    position = batch.positions.detach().requires_grad_(True)
    stiffness = position.new_tensor(1., requires_grad=True)
    energy_offset = position.new_tensor(7., requires_grad=True)
    energy = stiffness * position.square().sum() / 2 + energy_offset
    forces = -torch.autograd.grad(energy, position, create_graph=True)[0]
    predictions = {"total_energy": energy.reshape(1, 1), "forces": forces,
                   "stress": position.new_full((1, 3, 3), float("nan"))}
    parts = loss_parts(predictions, batch, config, scales)
    assert set(parts) == {"forces"}
    objective = weighted_loss(parts, config)
    old_api, used = loss_for(predictions, batch, config, scales)
    torch.testing.assert_close(old_api, objective)
    assert set(used) == {"forces"}
    gradient, offset_gradient = torch.autograd.grad(objective, [stiffness, energy_offset], allow_unused=True)
    expected = -2 * position.square().mean() / scales["forces"] ** 2
    torch.testing.assert_close(gradient, expected)
    assert offset_gradient is None
    with pytest.raises(ValueError, match="Missing predictions"):
        loss_parts({"total_energy": energy}, batch, config, scales)
    missing = copy.deepcopy(config)
    missing["dataset"]["bindings"]["forces"]["key"] = "absent-forces"
    with pytest.raises(ValueError, match="missing target absent-forces"):
        dataset(missing)[0]
    default = copy.deepcopy(config)
    del default["task"]["supervised_outputs"]
    with pytest.raises(ValueError, match="missing target absent-energy"):
        dataset(default)[0]
