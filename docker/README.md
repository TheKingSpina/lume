# Lume in Docker

Optional containerized mode. The default install path (`pip install pmb-ai`
or `make install`) is unchanged - this is purely an alternative that keeps
Lume off your host Python and out of your host `~/.lume`.

## Layout

```
docker/
  Dockerfile     single image used by every compose profile
   data/          Lume data home inside the container (bind-mounted, git-ignored)
  README.md      this file
compose.yaml     (repo root) shell / dashboard / mcp / server profiles
```

One image is enough: Lume is local-first with embedded SQLite + LanceDB, so
there is no separate database service to split out.

## Data isolation

- `LUME_HOME=/data` → bind-mounted to `./docker/data`. Your host `~/.lume` is
  never touched. Back up or inspect memory by looking in `./docker/data`.
- The HuggingFace embedding model (downloaded on first recall) is cached in
  the named volume `pmb_hf_cache`, so rebuilds don't re-download it.
- Drop a `config.yaml` into `./docker/data/` to set global Lume config; place
  per-workspace config under `./docker/data/workspaces/<id>/config.yaml`.

## CPU vs GPU

The image ships **CPU-only by default**, because for normal Lume usage a GPU
buys you almost nothing. Here's the reasoning, then the commands.

### Why CPU is the default

The only GPU-relevant work Lume does is computing **embeddings** - one forward
pass through a small sentence-transformer model, done once per stored memory
(at write time) and once per query (at recall time). Everything else in the
recall pipeline - BM25, SQLite lookups, the entity graph, reranking fusion -
is plain CPU work that a GPU can't speed up.

For interactive use that means:

- **A single-query embedding is tiny.** On CPU it's milliseconds. The real
  cost of the first recall is **loading the model into memory** (cold start),
  not the math - and a GPU doesn't make loading faster.
- **Warm recall is already fast on CPU** (single-digit to tens of ms), which is
  far below the latency of the LLM you're feeding. The agent never waits on Lume.

So a GPU sits idle during normal "remember / recall" traffic. It only earns its
keep on **bulk embedding** jobs:

- `lume reindex` re-embedding a large existing corpus,
- importing a big history (`lume import …`),
- running the LoCoMo / stress benchmarks over thousands of items.

There, embeddings are computed in large batches and GPU throughput genuinely
helps. If that's not your workload, stay on CPU.

### Differences at a glance

| | **CPU** (default, `lume:local`) | **GPU** (opt-in, `lume:gpu`) |
| :-- | :-- | :-- |
| torch wheel | `+cpu` (no CUDA) | default CUDA wheel + bundled NVIDIA libs |
| Image size | ~1.9 GB | ~5.9 GB |
| Host requirements | none - runs anywhere | NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| Interactive recall | fast (model load dominates) | no meaningful gain |
| Bulk re-embed / import / benchmarks | slower | faster (batched throughput) |
| When to use | normal agent memory, dev, dashboard | you routinely re-embed large corpora |

Note: a CUDA image on a host **without** a GPU is not just bigger - it can be
*slower* to start, because torch probes for CUDA and falls back. Don't build the
GPU image unless you actually have (and pass through) a GPU.

### Commands

```bash
# CPU (default)
make docker-build           # → image lume:local
make docker-shell

# GPU (opt-in)
make docker-build-gpu       # → image lume:gpu (CUDA torch)
make docker-shell-gpu
make docker-dashboard-gpu
```

Under the hood the GPU targets layer `docker/compose.gpu.yaml` over the base
compose (`docker compose -f compose.yaml -f docker/compose.gpu.yaml …`), which
flips the `TORCH_VARIANT` build arg to `cuda` and reserves the GPU. The two
images are tagged separately (`lume:local` vs `lume:gpu`) so they don't clobber
each other.

## Quick start

```bash
# build (UID/GID default to your user so ./docker/data stays writable)
make docker-build

# interactive dev sandbox: pip, python, pytest, ruff, lume …
make docker-shell
#   inside: lume note "hello from the container"
#           lume recall "hello"
#           make test-core

# web dashboard → http://127.0.0.1:8766
make docker-dashboard

# run the core test suite in the container
make docker-test

# stop everything
make docker-down
```

Without the Makefile, the equivalents are:

```bash
docker compose build
docker compose run --rm shell
docker compose --profile dashboard up
docker compose run --rm -i mcp
docker compose --profile dev --profile dashboard --profile mcp --profile server down
```

## Shared HTTP server (local and remote clients)

The `server` profile runs one persistent streamable-HTTP MCP server against
the same `./docker/data` bind mount used by the other profiles. By default,
the host port is loopback-only (`127.0.0.1:8765`). The dashboard also defaults
to loopback (`127.0.0.1:8766`). It can be bound to the server's Tailscale IP,
but it has no application-level authentication: anyone permitted to reach that
port by the tailnet ACL can view it. Keep it on loopback unless that access is
intended; never bind it to `0.0.0.0` or a public interface.

Create a local `.env` file (it is git-ignored) with a bearer token:

```bash
umask 077
printf 'LUME_MCP_BEARER_TOKEN=%s\n' "$(openssl rand -hex 32)" > .env
make docker-server
docker compose --profile server ps
curl http://127.0.0.1:8765/healthz
```

The local MCP endpoint is `http://127.0.0.1:8765/mcp`. For remote clients over
Tailscale, add the server's Tailscale IPv4 address to `.env`:

```dotenv
LUME_MCP_BIND_ADDRESS=100.x.y.z
LUME_MCP_PORT=8765
LUME_DASHBOARD_BIND_ADDRESS=100.x.y.z
LUME_DASHBOARD_PORT=8766
```

Then recreate only the Lume server with `docker compose --profile server up -d`.
Clients use `http://100.x.y.z:8765/mcp` and must send the bearer token. Tailscale
encrypts traffic between devices; keep the token private and grant access only
to trusted tailnet devices. Binding is limited to the specified interface, not
all network interfaces. The dashboard shares that Tailscale interface when its
variables are set; control access to port 8766 with Tailscale ACLs. **Do not use
an empty token for remote MCP access** or
expose plain HTTP to the public internet; for internet-facing deployments use
HTTPS behind a trusted reverse proxy. To stop Lume, run
`docker compose --profile server down` (the dashboard is a separate profile).

### Browser-hosted MCP clients

Browser clients require HTTPS and a CORS allowlist. Keep the MCP listener on
its Tailscale-only HTTP port, set the browser application's exact origin in
`.env`, and publish the MCP path through Tailscale Serve (the `--set-path`
route is additive to any existing Serve paths). Compose also publishes a
loopback-only backend port (default `127.0.0.1:18765`) for Tailscale Serve; the
existing Tailscale-IP listener remains available to other clients:

```dotenv
LUME_MCP_CORS_ORIGINS=https://agent.example.com
```

```bash
tailscale serve --bg --set-path=/mcp http://127.0.0.1:18765
tailscale serve status
```

Use the HTTPS MagicDNS URL reported for the machine, ending in `/mcp`, as the
browser client's endpoint. The browser must be able to access the tailnet. Only
the configured exact web origin receives CORS permission; do not use `*`.
Restart the MCP service after changing the origin setting.

To connect a host-side Lume installation to the shared endpoint, run:

```bash
lume connect claude-code --remote http://127.0.0.1:8765/mcp \
  --bearer-token "$(sed -n 's/^LUME_MCP_BEARER_TOKEN=//p' .env)"
```

Replace `claude-code` with a supported host such as `cursor` or `opencode`.

## Wiring the stdio MCP server to an agent

The MCP server talks over stdio, so the agent must launch it as a command.
Point your agent's MCP config at:

```json
{
  "mcpServers": {
    "lume": {
      "command": "docker",
      "args": ["compose", "-f", "/abs/path/to/pmb/compose.yaml",
               "run", "--rm", "-i", "mcp"]
    }
  }
}
```

(Use an absolute path to `compose.yaml`; agents don't run from the repo root.)

## Notes

- The repo is bind-mounted at `/app`, and the package is installed editable,
  so source edits on the host take effect immediately in the container.
- If `./docker/data` ends up root-owned, rebuild with your IDs:
  `make docker-build UID=$(id -u) GID=$(id -g)`.
