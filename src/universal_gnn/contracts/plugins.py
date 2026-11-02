"""Directory plugins are packages, so relative imports and dataclasses work normally."""

import hashlib
import importlib.util
from pathlib import Path
import sys


def load_plugin(directory):
    directory = Path(directory).resolve()
    path = directory / "plugin.py"
    name = "universal_plugin_" + hashlib.sha256(str(directory).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=[str(directory)])
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load plugin {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module
