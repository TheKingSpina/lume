# Usage

Concrete, copy-paste recipes. Lume is local-first: SQLite is the durable source
of truth, rebuildable search indexes stay local, and there are no cloud or API
key requirements.

## 60-second setup (guided)

```bash
pip install pmb-ai
lume setup            # detects your agent, wires the MCP entry, appends the rules
lume warmup           # load the model once so the first recall is fast
# restart your agent
```

`lume setup` is interactive and idempotent - run it again any time; it only edits
Lume's own entry and never touches your other MCP servers.

## Manual, per agent

If you'd rather wire one specific agent (or several), use `lume connect <agent>`.
Nine agents are supported; the id for Claude Code is **`claude-code`**:

```bash
lume connect claude-code     # Claude Code   (also gets per-turn auto-recall hooks)
lume connect cursor          # Cursor
lume connect codex           # OpenAI Codex CLI (MCP proxy + AGENTS.md rules + notify)
lume connect windsurf        # Codeium Windsurf
lume connect gemini          # Google Gemini CLI
lume connect vscode          # VS Code (MCP)
lume connect zed             # Zed
lume connect opencode        # opencode
lume connect continue        # Continue
```

Then restart the agent. After `lume connect`, the right usage rules are appended
to that agent's `CLAUDE.md` / `AGENTS.md` automatically, so the model learns the
`prepare()` pattern without you pasting anything.

## Verify it worked

```bash
lume doctor           # checks the install + MCP wiring; exits non-zero only with --strict
lume stats            # workspace counts and storage location
```

Then ask your agent something that needs memory - e.g. *"what did we decide about
auth last week?"*

| Host type | How memory arrives |
|---|---|
| Claude Code | Lifecycle hooks can inject the read-first context before the model thinks. |
| Codex | `lume connect codex` installs MCP plus `AGENTS.md` rules, so Codex calls `prepare` / `recall` when the task needs memory; `notify` powers ambient logging after a turn. |
| Cursor, Zed, VS Code, Windsurf, Gemini, Continue | The agent sees Lume as MCP tools and calls them when its installed rules say memory is relevant. |

## Use it from any directory

A **workspace** is keyed to the directory you run the agent in, so each project
gets its own memory with zero configuration - just `cd` into the project and go.

To point several agents (or several projects) at **one shared** memory, name a
workspace:

```bash
lume connect claude-code --workspace personal
lume connect cursor      --workspace personal
# both now read/write the same `personal` workspace; records from one are
# immediately visible to the other
```

List what exists with `lume workspaces`.

## A first session, end to end

```
You:    fix the pricing bug in the verdict policy we hit last Tuesday

Agent:  prepare(message="fix pricing bug verdict policy")
        ↓ (~10 ms, no LLM call)
        → 12 events about this project, 4 lessons (incl. "never drop the
          threshold under 25%"), 3 decisions, 2 open goals, last-24h activity
        Opening src/engine/verdict-policy.ts (you last changed it Wednesday).
        Per the lesson you saved, restoring the rate-floor guard on line 142.
```

Nothing was pasted; the agent showed up already informed.

## Inspect your memory

```bash
lume dashboard        # local web UI on http://127.0.0.1:8765 (nothing leaves the box)
lume dashboard        # web dashboard (replaces the old TUI)
lume audit            # "what does Lume know about me?" - grouped, read-only
lume recall "query"   # search with the full ranking trace
lume export           # dump everything to Markdown/JSON - your data, in the open
```

## Bring existing history (skip the cold start)

```bash
lume import chatgpt ~/Downloads/conversations.json
lume index pdf paper.pdf            # or a whole dir: lume index pdf ~/docs --recurse
lume index project .               # scan a codebase (symbols, imports, .gitignore-aware)
lume track modules                 # one-line "what this file does" per indexed file
lume track changes                 # new commits: what changed and WHY (Haiku, local)
```

## Session continuity & efficiency (opt-in)

A committable resume note for cross-session handoff, plus self-measurement and
context-budget guards:

```bash
lume resume save                   # write .lume/resume.md - commit it, share with the team
lume resume install                # auto-refresh resume.md at every turn end

lume health lessons-impact         # which lessons actually help outcomes (lift, churn)

# Opt-in token-saving guards
lume config set memory_delta.enabled true     # collapse repeat lesson injections to [Mxx]
lume memory ledger                            # inspect Memory Delta handles this session
```

Full command reference: [Commands](../reference/COMMANDS.md). Sharing memory
across a team: [Team and remote](TEAM.md).
