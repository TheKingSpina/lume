"""Server-configured agent mode is delivered on MCP initialization."""
from __future__ import annotations

import pytest


@pytest.fixture
def mcp_server_env(tmp_path, monkeypatch):
    home = tmp_path / "lume-home"
    monkeypatch.setenv("PMB_HOME", str(home))
    monkeypatch.setenv("PMB_WORKSPACE", "active-mode-test")
    monkeypatch.setenv("PMB_TOOL_PROFILE", "default")
    return home


@pytest.mark.asyncio
async def test_initialize_reads_active_mode_and_category_toggles(mcp_server_env):
    from fastmcp import Client

    from lume.config import Config
    from lume.mcp.server import build_server

    config = Config(
        workspace_dir=mcp_server_env / "workspaces" / "active-mode-test",
        pmb_home=mcp_server_env,
    )
    config.set_workspace("agent.active_mode", True)
    config.set_workspace("agent.log_decisions", False)
    config.set_workspace("agent.log_lessons", True)

    async with Client(
        build_server(cwd=None, workspace_id="active-mode-test", prewarm=False),
        mode="legacy",
    ) as client:
        instructions = client.initialize_result.instructions

    assert "AI-AGENT ACTIVE MODE" in instructions
    assert '"type":"lesson"' in instructions
    assert '"kind":"decision"' not in instructions


@pytest.mark.asyncio
async def test_reconnect_observes_dashboard_config_changes(mcp_server_env):
    from fastmcp import Client

    from lume.config import Config
    from lume.mcp.server import build_server

    config = Config(
        workspace_dir=mcp_server_env / "workspaces" / "active-mode-test",
        pmb_home=mcp_server_env,
    )
    config.set_workspace("agent.active_mode", True)
    server = build_server(cwd=None, workspace_id="active-mode-test", prewarm=False)

    async with Client(server, mode="legacy") as first_client:
        assert "AI-AGENT ACTIVE MODE" in first_client.initialize_result.instructions

    # Simulate the dashboard writing the workspace setting while the server
    # process remains alive; the next MCP handshake must see the new value.
    config.set_workspace("agent.active_mode", False)
    async with Client(server, mode="legacy") as reconnecting_client:
        assert "AI-AGENT ACTIVE MODE" not in reconnecting_client.initialize_result.instructions
