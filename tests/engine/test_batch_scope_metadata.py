"""Structured project/area scope metadata survives every batch write path."""
from __future__ import annotations

import json
import sqlite3
import time

from lume.core.engine import Engine


def test_record_batch_persists_scope_and_attribution_across_event_types(
    tmp_pmb_home, tmp_workspace_dir,
):
    eng = Engine(
        cwd=tmp_workspace_dir,
        pmb_home=tmp_pmb_home,
        config_overrides={"recall.cache_size": 0, "dedup.enable": False},
    )
    items = [
        {"type": "fact", "content": "Scoped fact alpha"},
        {"type": "lesson", "content": "Scoped lesson beta", "project": "PMB"},
        {"type": "goal", "title": "Scoped goal gamma"},
        {"type": "activity", "content": "Scoped activity delta"},
        {"type": "milestone", "chain_name": "scoped-chain", "title": "Scoped milestone epsilon"},
        {"type": "preference", "content": "Scoped preference zeta"},
        {"type": "summary", "content": "Scoped summary eta"},
        {"type": "fact_tree", "main": "Scoped tree theta", "subfacts": ["Scoped child iota"]},
        {
            "type": "keyed_fact", "subject": "user", "attribute": "scope-test",
            "value": "Scoped keyed fact kappa",
        },
    ]
    common = {
        "project_id": "pmb",
        "area_id": "design",
        "author": "opencode",
        "provenance": "user_asserted",
        "confidence": 0.95,
        "metadata": {"custom_tag": "keep-me"},
    }
    for item in items:
        item.update(common)

    result = eng.record_batch(items)
    assert result["n_ok"] == len(items), result["errors"]
    assert result["n_failed"] == 0

    with sqlite3.connect(eng.workspace.db_path) as conn:
        rows = conn.execute(
            "SELECT content, metadata_json FROM events WHERE workspace_id = ?",
            (eng.workspace.id,),
        ).fetchall()
    by_content = {content: json.loads(metadata or "{}") for content, metadata in rows}

    expected_contents = [
        "Scoped fact alpha", "Scoped lesson beta", "Scoped goal gamma",
        "Scoped activity delta", "Scoped milestone epsilon",
        "Scoped preference zeta", "Scoped summary eta", "Scoped tree theta",
        "Scoped child iota",
    ]
    for content in expected_contents:
        metadata = by_content[content]
        assert metadata["scope_type"] == "area", content
        assert metadata["scope_id"] == "design", content
        assert metadata["project_id"] == "pmb", content
        assert metadata["area_id"] == "design", content
        assert metadata["author"] == "opencode", content
        assert metadata["provenance"] == "user_asserted", content
        assert metadata["source"] == "user_asserted", content
        assert metadata["confidence"] == 0.95, content
        assert metadata["custom_tag"] == "keep-me", content

    # Keep old project-name metadata readable alongside the stable project ID.
    assert by_content["Scoped lesson beta"]["project_name"] == "PMB"
    assert any(
        metadata.get("scope_id") == "design"
        and metadata.get("custom_tag") == "keep-me"
        for content, metadata in by_content.items()
        if "scope-test" in content or "Scoped keyed fact kappa" in content
    )
    eng.close()


def test_record_batch_rejects_out_of_range_confidence_per_item(
    tmp_pmb_home, tmp_workspace_dir,
):
    eng = Engine(
        cwd=tmp_workspace_dir,
        pmb_home=tmp_pmb_home,
        config_overrides={"recall.cache_size": 0, "dedup.enable": False},
    )
    result = eng.record_batch([{
        "type": "fact",
        "content": "Invalid confidence is rejected",
        "confidence": 1.5,
        "project_id": "pmb",
    }])
    assert result["n_ok"] == 0
    assert result["n_failed"] == 1
    assert "confidence must be between 0 and 1" in result["errors"][0]["error"]
    eng.close()


def test_link_memories_connects_different_project_scopes(tmp_pmb_home, tmp_workspace_dir):
    eng = Engine(
        cwd=tmp_workspace_dir,
        pmb_home=tmp_pmb_home,
        config_overrides={"recall.cache_size": 0, "dedup.enable": False},
    )
    source = eng.record_fact("Project alpha migration decision", metadata={"project_id": "alpha"})
    target = eng.record_fact("Project beta migration consequence", metadata={"project_id": "beta"})

    linked = eng.link_memories(source, target, edge_type="references", rationale="shared migration")
    assert linked["cross_scope"] is True
    with sqlite3.connect(eng.workspace.db_path) as conn:
        edge = conn.execute(
            "SELECT edge_type, rationale FROM event_edges WHERE source_ulid=? AND target_ulid=?",
            (source, target),
        ).fetchone()
    assert edge == ("references", "shared migration")
    eng.close()


def test_archive_cold_can_be_limited_to_project_and_area(tmp_pmb_home, tmp_workspace_dir):
    eng = Engine(
        cwd=tmp_workspace_dir,
        pmb_home=tmp_pmb_home,
        config_overrides={"recall.cache_size": 0, "dedup.enable": False},
    )
    batch = eng.record_batch([
        {"type": "fact", "content": "Cold alpha design note", "project_id": "alpha", "area_id": "design", "importance": 0.2},
        {"type": "fact", "content": "Cold alpha coding note", "project_id": "alpha", "area_id": "development", "importance": 0.2},
        {"type": "fact", "content": "Cold beta design note", "project_id": "beta", "area_id": "design", "importance": 0.2},
    ])
    ulids = [item["ulid"] for item in batch["results"]]
    with sqlite3.connect(eng.workspace.db_path) as conn:
        conn.executemany(
            "UPDATE events SET timestamp=?, access_count=0 WHERE ulid=?",
            [(time.time() - 100 * 86400, ulid) for ulid in ulids],
        )

    result = eng.archive_cold(
        days=30, max_importance=0.3, dry_run=True,
        project_id="alpha", area_id="design",
    )
    assert result["n"] == 1
    assert result["candidates"][0]["ulid"] == ulids[0]
    eng.close()
