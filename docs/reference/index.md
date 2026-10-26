# Reference

Use reference pages when you already know the task and need the exact command,
flag, or configuration key.

``` mermaid
flowchart LR
  Task["Task"] --> Command["Command reference"]
  Task --> Config["Configuration"]
  Command --> Run["Run lume command"]
  Config --> Tune["Tune behavior"]
  Run --> Verify["doctor, stats, dashboard"]
  Tune --> Verify
```

<div class="grid cards" markdown>

-   **Commands**

    Every Lume command grouped by setup, capture, recall, lifecycle, sync, and UI.

    [Open the command reference →](COMMANDS.md)

-   **MCP tools**

    The tools an agent calls (prepare, recall, record_batch, and more), plus the
    tool profiles.

    [See the MCP tools →](mcp-tools.md)

-   **Configuration**

    Settings for recall, models, hooks, graph extraction, and active logging.

    [Open configuration →](configuration.md)

</div>

## Fast lookup

| Task | Start with |
|---|---|
| Wire Lume into an agent | `lume setup` or `lume connect <agent>` |
| Check install health | `lume doctor` |
| Search memory manually | `lume recall "query"` |
| Inspect memory visually | `lume dashboard` |
| Change model profile | `lume model` |
| Tune behavior | `lume config list` |
