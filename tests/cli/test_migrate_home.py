"""Legacy user data is copied safely into Lume's new storage home."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner


def test_migrate_home_copies_and_preserves_legacy_directory(tmp_path, monkeypatch):
    from lume.cli.main import app

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("LUME_HOME", raising=False)
    monkeypatch.delenv("PMB_HOME", raising=False)
    old = tmp_path / ".pmb"
    old.mkdir()
    (old / "config.yaml").write_text("recall:\n  top_k: 7\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["migrate-home", "--yes"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".lume" / "config.yaml").read_text(encoding="utf-8") == \
        "recall:\n  top_k: 7\n"
    assert (old / "config.yaml").exists()


def test_migrate_home_refuses_to_merge_existing_target(tmp_path, monkeypatch):
    from lume.cli.main import app

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("LUME_HOME", raising=False)
    monkeypatch.delenv("PMB_HOME", raising=False)
    (tmp_path / ".pmb").mkdir()
    (tmp_path / ".lume").mkdir()

    result = CliRunner().invoke(app, ["migrate-home", "--yes"])

    assert result.exit_code == 2
    assert "already exists" in result.output
