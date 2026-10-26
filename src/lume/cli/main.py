"""
Lume CLI (legacy command alias: ``pmb``).

Common commands:
- lume                                - show this workspace's status dashboard
- lume init [--name NAME]             - initialize a workspace in the current folder
- lume stats                          - workspace statistics
- lume list [--limit N] [--type T]    - list recent events
- lume remember "query" "response"   - add a Q/A pair
- lume recall "query" [-k 5]          - search memory
- lume pin ULID                       - pin an event (kept, never auto-archived)
- lume forget ULID                    - archive an event
- lume workspaces                     - list all workspaces
- lume workspace use NAME             - switch the default workspace
"""

from __future__ import annotations

import typer

import lume.cli.commands.capture  # noqa: F401  (registers capture root commands)

# The root Typer app, console, and shared helpers live in lume.cli._common so
# the per-area command modules can register onto the same app without an import
# cycle. (Re-exported here for the many in-file commands that still use them.)
from lume.cli._common import (  # noqa: E402
    app,
)
from lume.cli.commands.graph import graph_app

app.add_typer(graph_app, name="graph")
from lume.cli.commands.health import health_app

app.add_typer(health_app, name="health")
from lume.cli.commands.config import config_app

app.add_typer(config_app, name="config")
# Ollama subcommand - for fully-local LLM ops (no Anthropic / OpenAI key)
from lume.cli.ollama_cmd import app as ollama_app

app.add_typer(ollama_app, name="ollama")
import lume.cli.commands.maintenance  # noqa: F401  (registers maintenance root commands)
from lume.cli.commands.workspace import workspace_app

app.add_typer(workspace_app, name="workspace")
from lume.cli.commands.index import index_app

app.add_typer(index_app, name="index")
from lume.cli.commands.track import track_app

app.add_typer(track_app, name="track")
from lume.cli.commands.resume import resume_app

app.add_typer(resume_app, name="resume")
from lume.cli.commands.memo import memory_app

app.add_typer(memory_app, name="memory")
from lume.cli.commands.snapshot import snapshot_app

app.add_typer(snapshot_app, name="snapshot")
import lume.cli.commands.ambient  # noqa: F401  (registers ambient @app.command root commands)
import lume.cli.commands.manage  # noqa: F401  (registers manage root commands)
from lume.cli.commands.hooks import hooks_app, mcp_app

app.add_typer(hooks_app, name="hooks")
app.add_typer(mcp_app, name="mcp")
from lume.cli.commands.daemon import daemon_app

app.add_typer(daemon_app, name="daemon")
from lume.cli.commands.lang import lang_app

app.add_typer(lang_app, name="lang")


# ── Group the flat command list into ordered help panels ─────────────────────
# `lume --help` otherwise dumps ~70 commands as one wall. These panels turn it
# into a guided map. Centralized here (one map) so adding a command is one line,
# not a per-decorator `rich_help_panel=` scattered across files. Anything not
# listed falls to "More" rather than being dropped.
_HELP_COMMAND_PANELS: list[tuple[str, list[str]]] = [
    ("✦ Setup & agents", [
        "setup", "connect", "doctor", "ambient-watch", "codex-notify"]),
    ("Capture", [
        "remember", "fact", "note", "learn", "distill", "lessons", "watch",
        "sync", "import", "tag", "untag", "tags", "tagged", "ttl"]),
    ("Recall & explore", [
        "recall", "why", "overview", "audit", "timeline", "insights", "digest",
        "history", "correlate", "reminders", "goals", "session"]),
    ("Maintain memory", [
        "pin", "forget", "forget-topic", "forget-auto", "decay", "declutter",
        "dedupe", "prune-expired", "prune-graph", "compact", "reindex",
        "regraph", "repair-keyed", "rehearse", "consolidate", "reflect",
        "arcs", "feedback", "migrate-workspaces", "schedule"]),
    ("Workspaces & data", [
        "init", "workspaces", "stats", "list", "export", "dashboard",
        "warmup"]),
    ("Agent internals", [
        "prepare-context", "auto-context", "session-restore",
        "lesson-followcheck", "track-action", "autowrite"]),
]
_HELP_GROUP_PANELS: dict[str, str] = {
    "hooks": "✦ Setup & agents", "mcp": "✦ Setup & agents",
    "daemon": "✦ Setup & agents",
    "workspace": "Workspaces & data", "index": "Workspaces & data",
    "track": "Workspaces & data", "resume": "Workspaces & data",
    "memory": "Workspaces & data", "snapshot": "Workspaces & data",
    "graph": "More", "health": "More", "config": "More",
    "ollama": "More", "lang": "More",
}


def _cmd_name(info) -> str:
    cb = getattr(info, "callback", None)
    return info.name or (cb.__name__.replace("_", "-") if cb else "")


def _organize_help() -> None:
    """Assign each command/group a rich help panel + reorder so the panels
    render in the declared order (Rich uses first-appearance order)."""
    by_name = {_cmd_name(i): i for i in app.registered_commands}
    ordered, seen = [], set()
    for panel, names in _HELP_COMMAND_PANELS:
        for nm in names:
            info = by_name.get(nm)
            if info is not None and nm not in seen:
                info.rich_help_panel = panel
                ordered.append(info)
                seen.add(nm)
    for info in app.registered_commands:        # anything unlisted -> "More"
        if _cmd_name(info) not in seen:
            info.rich_help_panel = "More"
            ordered.append(info)
    app.registered_commands = ordered
    for g in app.registered_groups:             # sub-typers join their panel
        panel = _HELP_GROUP_PANELS.get(g.name)
        if panel:
            g.rich_help_panel = panel


_organize_help()


@app.callback(invoke_without_command=True)
def _root(ctx: typer.Context):
    """Lume - persistent memory for AI agents. Bare `lume` opens the command
    palette (in a terminal) or the status dashboard (piped)."""
    # Any subcommand (and `--help`, which Click handles before this body)
    # passes through untouched.
    if ctx.invoked_subcommand is not None:
        return

    import sys

    from lume.cli._common import console

    # Bare `lume` in a real terminal opens the command palette: type what you
    # want, the list filters live by intent, Enter runs it. Non-interactive
    # (piped, CI, scripts) or any palette error falls back to the static status
    # dashboard, so `pmb | cat` and automation keep their plain output.
    try:
        if sys.stdin.isatty() and console.is_terminal:
            # First ever run: the ✦ boot animation + a one-screen welcome, then
            # stop. Every run after that goes straight to the command palette.
            from lume.cli.intro import maybe_first_run
            if maybe_first_run(console):
                return
            from lume.cli.palette import command_catalog, run_palette
            chosen = run_palette(console, command_catalog(app))
            if chosen:
                import subprocess
                console.print(f"[dim]>[/] [magenta]✦[/] [bold]pmb {chosen}[/]")
                subprocess.run([sys.argv[0], *chosen.split()])
                return
            # Esc / Ctrl-C falls through to the status dashboard below.
    except Exception:
        pass
    from lume.cli.status_panel import render_status
    render_status(console)


if __name__ == "__main__":
    app()
