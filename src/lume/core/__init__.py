"""Core engine package.

Like `pmb`, this package re-exports its big names lazily via PEP 562
`__getattr__`. Submodules that don't need the full engine (for example
`lume.core.events` for SQLite-only callers, or `lume.core.workspace` for
path detection in the CLI) can be imported directly without dragging
LanceDB / sentence-transformers in.
"""

from __future__ import annotations

__all__ = [
    "Engine",
    "Event",
    "EventStore",
    "HybridSearch",
    "Workspace",
    "detect_workspace",
]


_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "Engine":           ("lume.core.engine",     "Engine"),
    "Event":            ("lume.core.events",     "Event"),
    "EventStore":       ("lume.core.events",     "EventStore"),
    "HybridSearch":     ("lume.core.search",     "HybridSearch"),
    "Workspace":        ("lume.core.workspace",  "Workspace"),
    "detect_workspace": ("lume.core.workspace",  "detect_workspace"),
}


def __getattr__(name: str):
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'lume.core' has no attribute {name!r}")
    module_name, attr = target
    import importlib
    module = importlib.import_module(module_name)
    value = getattr(module, attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_ATTRS.keys()))
