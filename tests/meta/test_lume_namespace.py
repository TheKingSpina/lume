"""The Lume namespace is canonical while PMB imports remain aliases."""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path


def test_legacy_imports_resolve_to_canonical_module_objects():
    for name in ("core.engine", "mcp.server", "cli.main", "security.redact"):
        assert importlib.import_module(f"pmb.{name}") is importlib.import_module(f"lume.{name}")


def test_lume_home_environment_is_primary_and_pmb_is_aliased(tmp_path):
    source = Path(__file__).resolve().parents[2] / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source)
    env["LUME_HOME"] = str(tmp_path / "new-home")
    env.pop("PMB_HOME", None)
    check = subprocess.run(
        [sys.executable, "-c", "import os,lume; assert os.environ['PMB_HOME']==os.environ['LUME_HOME']; assert lume.env.lume_home().name=='new-home'"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert check.returncode == 0, check.stderr


def test_legacy_environment_aliases_are_read_and_canonical_values_win(tmp_path):
    source = Path(__file__).resolve().parents[2] / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source)
    env["PMB_HOME"] = str(tmp_path / "legacy-home")
    env["PMB_WORKSPACE"] = "legacy-workspace"
    env.pop("LUME_HOME", None)
    env.pop("LUME_WORKSPACE", None)
    env["HOME"] = str(tmp_path)
    check = subprocess.run(
        [sys.executable, "-c", "import os,lume; assert os.environ['LUME_HOME']==os.environ['PMB_HOME']; assert os.environ['LUME_WORKSPACE']=='legacy-workspace'"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert check.returncode == 0, check.stderr

    env["LUME_HOME"] = str(tmp_path / "canonical-home")
    check = subprocess.run(
        [sys.executable, "-c", "import os,lume; assert os.environ['PMB_HOME']==os.environ['LUME_HOME']; assert lume.env.lume_home().name=='canonical-home'"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert check.returncode == 0, check.stderr


def test_legacy_home_is_reused_until_explicit_migration(tmp_path):
    source = Path(__file__).resolve().parents[2] / "src"
    legacy_home = tmp_path / ".pmb"
    legacy_home.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source)
    env.pop("LUME_HOME", None)
    env.pop("PMB_HOME", None)
    env["HOME"] = str(tmp_path)
    check = subprocess.run(
        [sys.executable, "-c", "import lume; assert lume.env.lume_home().name=='.pmb'"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert check.returncode == 0, check.stderr


def test_lume_home_api_names_are_available(tmp_path):
    from lume.config import Config
    from lume.core.workspace import detect_workspace

    config = Config(lume_home=tmp_path)
    workspace = detect_workspace(cwd=tmp_path, lume_home=tmp_path / "data")

    assert config.global_path == tmp_path / "config.yaml"
    assert config.pmb_home == config.lume_home == tmp_path
    assert workspace.lume_home == workspace.pmb_home == tmp_path / "data"
