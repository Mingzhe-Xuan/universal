import json

import pytest
import torch

from universal_gnn.data.structures import bind_targets, expand_voigt, load_structures
from universal_gnn.properties import property_spec


def test_json_binding_preserves_provenance(tmp_path):
    path = tmp_path / "atoms.json"
    path.write_text(json.dumps([{"id": "example", "atoms": {"numbers": [14],
        "cell": [[3, 0, 0], [0, 3, 0], [0, 0, 3]], "coords": [[.5, 0, 0]],
        "cartesian": False}, "energy": -2.5}]), encoding="utf-8")
    structures = load_structures(path)
    torch.testing.assert_close(structures[0].positions, torch.tensor([[1.5, 0, 0]], dtype=torch.float64))
    bound = bind_targets(structures, {"total_energy": {"key": "energy", "unit": "eV"}})
    assert bound[0].metadata["sha256"]
    assert bound[0].targets["total_energy"].item() == -2.5
    with pytest.raises(ValueError, match="missing target"):
        bind_targets(structures, {"forces": "absent"})


def test_response_catalog_and_voigt():
    assert property_spec("elastic").construction == "derivative"
    assert property_spec("piezoelectric").shape == (3, 3, 3)
    c = torch.arange(36.).reshape(6, 6)
    full = expand_voigt(c, "elastic")
    assert full.shape == (3, 3, 3, 3)
    assert full[1, 2, 0, 1] == c[3, 5]
    assert full[2, 1, 1, 0] == c[3, 5]
    with pytest.raises(ValueError, match="Unknown property"):
        property_spec("unregistered_response")
