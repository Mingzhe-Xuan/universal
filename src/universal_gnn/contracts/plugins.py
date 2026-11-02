"""Directory plugins are packages, so relative imports and dataclasses work normally."""

import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
from pathlib import Path
import sys


class _PluginSourceLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        # Source fingerprints must not be undermined by stale timestamp-based bytecode caches.
        return self.source_to_code(self.get_data(self.path), self.path)


class _PluginFinder(importlib.abc.MetaPathFinder):
    roots = {}

    def find_spec(self, fullname, path=None, target=None):
        root_name, _, relative = fullname.partition(".")
        if root_name not in self.roots or not relative:
            return None
        location = self.roots[root_name].joinpath(*relative.split("."))
        package = location / "__init__.py"
        source = package if package.is_file() else location.with_suffix(".py")
        if source.is_file():
            return importlib.util.spec_from_file_location(fullname, source,
                       loader=_PluginSourceLoader(fullname, str(source)),
                       submodule_search_locations=[str(location)] if source == package else None)
        if location.is_dir():
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(location)]
            return spec
        return None


_finder = _PluginFinder()


def load_plugin(directory):
    directory = Path(directory).resolve()
    path = directory / "plugin.py"
    if not path.is_file():
        raise ValueError(f"Plugin directory must contain {path}")
    files = sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.relative_to(directory).as_posix().encode() + b"\0" + file.read_bytes() + b"\0")
    checksum = digest.hexdigest()
    name = "universal_plugin_" + hashlib.sha256((str(directory) + checksum).encode()).hexdigest()[:16]
    if name in sys.modules:
        return sys.modules[name]
    _finder.roots[name] = directory
    if _finder not in sys.meta_path:
        sys.meta_path.insert(0, _finder)
    spec = importlib.util.spec_from_file_location(name, path, loader=_PluginSourceLoader(name, str(path)),
                                                submodule_search_locations=[str(directory)])
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load plugin {path}")
    module = importlib.util.module_from_spec(spec)
    module.__ugnn_provenance__ = {"path": str(directory), "source_sha256": checksum,
                                  "files": [file.relative_to(directory).as_posix() for file in files]}
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module
