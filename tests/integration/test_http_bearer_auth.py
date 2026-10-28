"""E2e for the streamable-http transport's bearer-token auth.

Rather than boot a full uvicorn server (slow, flaky to tear down on
Windows), we mount the real `_build_bearer_middleware` middleware on a tiny
Starlette app and drive it through Starlette's TestClient — the same ASGI
path a live request takes. This pins the auth contract:

  • no token / wrong token              → 401
  • correct token (constant-time match) → passes through (200)
  • CORS preflight (OPTIONS) + health    → pass through unauthenticated
  • empty token config                  → middleware is None (auth disabled)
"""

from __future__ import annotations

import pytest

starlette = pytest.importorskip("starlette")
pytest.importorskip("httpx")

from pmb.mcp.server import (
    _build_bearer_middleware,
    _install_cors_middleware,
    _install_health_routes,
)
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

TOKEN = "s3cr3t-bearer-token-xyz"
TRUSTED_ORIGIN = "https://agent.example.com"


def _app(token: str) -> Starlette:
    async def ok(request):
        return PlainTextResponse("ok")

    async def health(request):
        return PlainTextResponse("healthy")

    app = Starlette(routes=[
        Route("/mcp", ok, methods=["GET", "POST", "OPTIONS"]),
        Route("/healthz", health, methods=["GET"]),
        Route("/", health, methods=["GET"]),
    ])
    mw = _build_bearer_middleware(token)
    if mw is not None:
        app.add_middleware(mw)
    return app


def test_no_token_rejected():
    client = TestClient(_app(TOKEN))
    r = client.post("/mcp", json={"jsonrpc": "2.0"})
    assert r.status_code == 401
    assert r.json().get("error") == "unauthorized"


def test_wrong_token_rejected():
    client = TestClient(_app(TOKEN))
    r = client.post("/mcp", headers={"Authorization": "Bearer nope"},
                    json={"jsonrpc": "2.0"})
    assert r.status_code == 401


def test_correct_token_passes():
    client = TestClient(_app(TOKEN))
    r = client.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"},
                    json={"jsonrpc": "2.0"})
    assert r.status_code == 200
    assert r.text == "ok"


def test_malformed_header_rejected():
    client = TestClient(_app(TOKEN))
    # right token value but missing the "Bearer " scheme prefix
    r = client.post("/mcp", headers={"Authorization": TOKEN},
                    json={"jsonrpc": "2.0"})
    assert r.status_code == 401


def test_cors_preflight_passes_without_auth():
    client = TestClient(_app(TOKEN))
    r = client.options("/mcp")
    assert r.status_code < 400  # preflight allowed through


def test_health_endpoints_pass_without_auth():
    client = TestClient(_app(TOKEN))
    assert client.get("/healthz").status_code == 200
    assert client.get("/").status_code == 200


def test_health_routes_are_installed_on_http_app():
    app = Starlette()
    _install_health_routes(app)
    app.add_middleware(_build_bearer_middleware(TOKEN))

    client = TestClient(app)
    assert client.get("/healthz").json() == {
        "status": "ok", "service": "lume-mcp",
    }
    assert client.get("/").status_code == 200


def test_configured_cors_origin_can_preflight_authenticated_mcp():
    app = _app(TOKEN)
    _install_cors_middleware(app, TRUSTED_ORIGIN)

    response = TestClient(app).options(
        "/mcp",
        headers={
            "Origin": TRUSTED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,mcp-protocol-version",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == TRUSTED_ORIGIN
    assert "authorization" in response.headers["access-control-allow-headers"].lower()

    actual = TestClient(app).post(
        "/mcp",
        headers={"Origin": TRUSTED_ORIGIN, "Authorization": f"Bearer {TOKEN}"},
        json={"jsonrpc": "2.0"},
    )
    assert actual.status_code == 200
    assert "mcp-session-id" in actual.headers["access-control-expose-headers"].lower()


def test_configured_cors_rejects_unlisted_origins():
    app = _app(TOKEN)
    _install_cors_middleware(app, TRUSTED_ORIGIN)

    response = TestClient(app).options(
        "/mcp",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_wildcard_is_rejected():
    app = _app(TOKEN)
    with pytest.raises(ValueError, match="explicit origins"):
        _install_cors_middleware(app, "*")


def test_empty_token_disables_auth():
    # No token configured → middleware factory returns None → no auth gate.
    assert _build_bearer_middleware("") is None
    client = TestClient(_app(""))
    r = client.post("/mcp", json={"jsonrpc": "2.0"})
    assert r.status_code == 200  # unauthenticated but allowed (network-ACL mode)


def test_case_insensitive_header_name():
    # HTTP header names are case-insensitive; the check must still work.
    client = TestClient(_app(TOKEN))
    r = client.post("/mcp", headers={"AUTHORIZATION": f"Bearer {TOKEN}"},
                    json={"jsonrpc": "2.0"})
    assert r.status_code == 200
