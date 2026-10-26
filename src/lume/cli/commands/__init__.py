"""Per-area PMB CLI command modules.

Each module defines either a sub-Typer (e.g. `graph_app`) or registers root
commands onto the shared `lume.cli._common.app`. `lume.cli.main` imports them so
their command registrations run; nothing here imports `lume.cli.main` (that
would be a cycle).
"""
