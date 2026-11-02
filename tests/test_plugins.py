import torch

from universal_gnn.data.structures import load_structures
from universal_gnn.engine.training import build_model, loss_for


def test_relative_import_dataset_and_custom_output(tmp_path):
    (tmp_path / "source.py").write_text('''import torch
from universal_gnn.contracts import Structure
def records(label):
    yield Structure(torch.tensor([1]),torch.zeros(1,3),torch.eye(3)*8,
                    torch.tensor([False]*3),"custom",{"my_label":label})
''')
    (tmp_path / "plugin.py").write_text('''from dataclasses import dataclass
from .source import records
@dataclass
class Options:
    label: int = 1
def build_dataset(label=1):
    return records(Options(label).label)
''')
    structures = load_structures("plugin:" + str(tmp_path), options={"label": 2})
    assert structures[0].targets["my_label"] == 2
    assert structures[0].positions.dtype == torch.float64
    config = {"backbone": {"name": "cgcnn", "implementation": "legacy", "width": 8, "layers": 1},
              "task": {"kind": "supervised", "property": "my_label",
                       "spec": {"scope": "graph", "shape": [3], "unit": "class", "kind": "classification"}}}
    model = build_model(config).double()
    from universal_gnn.contracts import StructureBatch

    batch = StructureBatch.from_structures(structures)
    prediction = model(batch)
    loss, _ = loss_for({"my_label": prediction}, batch, config)
    torch.testing.assert_close(loss, torch.nn.functional.cross_entropy(prediction, torch.tensor([2])))
    loss.backward()
    assert any(p.grad is not None for p in model.backbone.parameters())
