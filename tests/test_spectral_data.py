import importlib.util
from pathlib import Path

import pytest


def test_raman_rejects_unmapped_mode_slots(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("prepare_raman_data", directory / "prepare_raman_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = {"numbers": {"__ndarray__": [[1], "int64", [1]]},
           "key_value_pairs": {"frequencies_thz": "[0.0 0.1 0.2]"},
           "data": {"raman_tensors": [None, [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]]}}
    with pytest.raises(ValueError, match="mode count mismatch"):
        module.convert(row)
