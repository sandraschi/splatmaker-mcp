"""Entry point — dual transport per fleet standard: stdio (default, for
Claude Desktop / Cursor) or streamable HTTP on /mcp (for the webapp + hub).
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from starlette.responses import JSONResponse

from splatmaker_mcp.server import (
    BACKEND_PORT,
    _do_shutdown,
    _register_with_hub,
    health_payload,
    mcp,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _health(request):  # noqa: ANN001 - Starlette handler signature
    return JSONResponse(health_payload())


async def _shutdown(request):  # noqa: ANN001 - Starlette handler signature
    await _do_shutdown()
    return JSONResponse({"status": "shutting_down", "message": "Server will exit in ~0.5s"})


def build_http_app():
    """Starlette app: /api/health (fleet contract) + FastMCP's own /mcp mount.
    Starlette chosen per STARLETTE_NO_PYDANTIC_STANDARD - this server's REST
    surface (health + job status) doesn't yet earn FastAPI/Swagger; revisit
    if the webapp grows a genuinely browsable API surface.

    NOTE: use add_route(), not routes.append() - the .routes property on
    FastMCP's StarletteWithLifespan doesn't reliably back the live router
    table; add_route() is the real registration API and was verified to
    work during scaffold smoke-testing (routes.append() silently produced
    404s despite the route object existing in the returned list).
    """
    starlette_app = mcp.http_app(path="/mcp")
    starlette_app.add_route("/api/health", _health)
    starlette_app.add_route("/api/shutdown", _shutdown, methods=["POST"])
    return starlette_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="splatmaker-mcp")
    parser.add_argument(
        "--http", action="store_true", help="Run streamable HTTP transport instead of stdio"
    )
    parser.add_argument("--port", type=int, default=BACKEND_PORT)
    args = parser.parse_args()

    if args.http:
        import uvicorn

        # Registration run synchronously before uvicorn takes over rather than
        # via an ASGI startup hook - the Starlette Router object returned by
        # mcp.http_app() doesn't consistently expose on_startup/add_event_handler
        # across FastMCP/Starlette versions (confirmed broken on Starlette 1.3.1
        # during scaffold verification). This is simpler and version-independent.
        asyncio.run(_register_with_hub())

        app = build_http_app()
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    else:
        mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
