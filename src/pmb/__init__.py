"""Compatibility namespace for the historic ``pmb`` Python package.

New integrations should import :mod:`lume`. Submodules requested through
``pmb`` are resolved to the same canonical ``lume`` module objects.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys

_lume = importlib.import_module("lume")
__version__ = _lume.__version__
__all__ = _lume.__all__


class _LegacyNamespaceLoader(importlib.abc.Loader):
    def __init__(self, target: str):
        self.target = target

    def create_module(self, spec):
        return importlib.import_module(self.target)

    def exec_module(self, module):
        # create_module returns the already initialized canonical module.
        return None

    def get_code(self, fullname):
        spec = importlib.util.find_spec(self.target)
        if spec is None or spec.loader is None:
            return None
        get_code = getattr(spec.loader, "get_code", None)
        return get_code(self.target) if get_code is not None else None

    def get_source(self, fullname):
        spec = importlib.util.find_spec(self.target)
        if spec is None or spec.loader is None:
            return None
        get_source = getattr(spec.loader, "get_source", None)
        return get_source(self.target) if get_source is not None else None


class _LegacyNamespaceFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith("pmb."):
            return None
        canonical = "lume." + fullname[4:]
        try:
            target_spec = importlib.util.find_spec(canonical)
        except (ImportError, ModuleNotFoundError, ValueError):
            return None
        if target_spec is None:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            _LegacyNamespaceLoader(canonical),
            origin=target_spec.origin,
            is_package=target_spec.submodule_search_locations is not None,
        )


if not any(isinstance(finder, _LegacyNamespaceFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _LegacyNamespaceFinder())

# Force the legacy alias to use the finder rather than searching an independent
# package tree and loading duplicate ``pmb.*`` modules.
__path__ = []


def __getattr__(name: str):
    return getattr(_lume, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_lume)))
