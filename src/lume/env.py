"""Environment-name and storage-path compatibility for the Lume rename."""
from __future__ import annotations

import os
from pathlib import Path

_LEGACY_ENV = (
    "HOME",
    "WORKSPACE",
    "CWD",
    "TOOL_PROFILE",
    "MCP_BEARER_TOKEN",
    "MCP_TRANSPORT",
    "MCP_HOST",
    "MCP_PORT",
    "MCP_PATH",
    "MCP_CLIENT_TIMEOUT_MS",
    "OLLAMA_URL",
    "OLLAMA_MODEL",
    "OPENAI_MODEL",
    "SYSTEM_INSTRUCTIONS",
    "SYSTEM_INSTRUCTIONS_OLD",
    "CLAUDE_CMD",
    "CLAUDE_MODEL",
    "INTERNAL_LLM",
    "NO_ANIM",
    "DISABLE_DEFAULT_PACKS",
)


def initialize_environment() -> None:
    """Prefer LUME_* settings while continuing to honor historical PMB_* names."""
    for suffix in _LEGACY_ENV:
        current, legacy = f"LUME_{suffix}", f"PMB_{suffix}"
        if current in os.environ:
            os.environ[legacy] = os.environ[current]
        elif legacy in os.environ:
            os.environ[current] = os.environ[legacy]


def lume_home() -> Path:
    """Resolve the active data home without moving legacy user data."""
    explicit = os.environ.get("LUME_HOME") or os.environ.get("PMB_HOME")
    if explicit:
        return Path(explicit).expanduser()
    current, legacy = Path.home() / ".lume", Path.home() / ".pmb"
    if not current.exists() and legacy.exists():
        return legacy
    return current


def env_value(name: str, default: str | None = None) -> str | None:
    """Read a LUME_* variable first, falling back to its PMB_* alias."""
    if name.startswith("LUME_"):
        return os.environ.get(name, os.environ.get("PMB_" + name[5:], default))
    return os.environ.get(name, default)


initialize_environment()
