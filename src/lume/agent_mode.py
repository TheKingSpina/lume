"""Shared instructions for Lume's opt-in proactive agent mode."""
from __future__ import annotations

_ACTIVE_CATEGORY_LINES: dict[str, str] = {
    "decisions": (
        '- **Decision** - chose a library / pattern / schema / config:\n'
        '  `{"type":"activity","kind":"decision","content":"Chose Postgres over Mongo for JSONB"}`'
    ),
    "completed": (
        '- **Done** - shipped a feature, fixed a bug, refactored:\n'
        '  `{"type":"activity","kind":"completed","content":"Fixed JWT 24h-expiry bug in auth.py"}`'
    ),
    "lessons": (
        '- **Lesson** - found a project convention / gotcha, or the user corrected you:\n'
        '  `{"type":"lesson","content":"This repo uses pnpm, never npm"}`'
    ),
    "failures": (
        '- **Failure** - something you tried did NOT work (so it is not repeated):\n'
        '  `{"type":"failure","content":"Bumping numpy to 2.x broke lancedb - stay on 1.x"}`'
    ),
    "goals": (
        '- **Goal** - the user states an intent / plan:\n'
        '  `{"type":"goal","title":"Ship v1 by June","status":"in_progress"}`'
    ),
}

_ACTIVE_DEFAULT_TOGGLES = {
    "log_decisions": True,
    "log_completed": True,
    "log_lessons": True,
    "log_failures": True,
    "log_goals": True,
    "apply_lessons": True,
    "context_continuity": True,
}


def build_active_addendum(toggles: dict | None = None) -> str:
    """Build proactive-logging instructions from the ``agent.log_*`` toggles."""
    settings = {**_ACTIVE_DEFAULT_TOGGLES, **(toggles or {})}
    categories = [
        category
        for category in ("decisions", "completed", "lessons", "failures", "goals")
        if settings.get(f"log_{category}")
    ]
    category_block = "\n".join(_ACTIVE_CATEGORY_LINES[item] for item in categories) or (
        "- (all logging categories are disabled in config)"
    )

    lesson_loop = ""
    if settings.get("apply_lessons"):
        lesson_loop = (
            "\n\n### Self-improvement loop (use what you learned - don't repeat mistakes)\n\n"
            'At the START of a non-trivial task, call `recall("<task topic> '
            'lessons failures")` ONCE. If a ★lesson or ⚠failure comes back, '
            "FOLLOW it. When the user corrects you or something fails, record it "
            "(above) so the NEXT session is smarter - the agent should get better "
            "at THIS project over time."
        )

    continuity = ""
    if settings.get("context_continuity"):
        continuity = (
            "\n\n### Don't lose the thread (long sessions)\n\n"
            "In a long session your own context window compacts and you lose "
            "detail. Lume is your durable session memory - the logging above keeps "
            "the record. If you've lost track (after a compaction, or many turns "
            "in), call `session_brief` ONCE to re-orient on what was decided/done "
            "this session, then continue. Don't re-ask the user what you already did."
        )

    return (
        "\n\n### AI-AGENT ACTIVE MODE (enabled by the Lume server for this connection)\n\n"
        'When YOU do real work, LOG IT proactively - do not wait for "remember" '
        "(still exactly ONE `record_batch` per turn):\n\n"
        f"{category_block}\n\n"
        "Still skip general Q&A and trivial steps. Recall stays lazy on general "
        "and technical questions."
        f"{lesson_loop}{continuity}\n"
    )
