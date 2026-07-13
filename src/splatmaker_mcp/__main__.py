"""Entry point — dual transport per fleet standard: stdio (default, for
Claude Desktop / Cursor) or streamable HTTP on /mcp (for the webapp + hub).
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from splatmaker_mcp.server import (
    BACKEND_PORT,
    _register_with_hub,
    health_payload,
    mcp,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _health(request):  # noqa: ANN001 — Starlette handler signature
    return JSONResponse(health_payload())


def build_http_app():
    """Starlette app: /api/health (fleet contract) + FastMCP's own /mcp mount.
    Starlette chosen per STARLETTE_NO_PYDANTIC_STANDARD — this server's REST
    surface (health + job status) doesn't yet earn FastAPI/Swagger; revisit
    if the webapp grows a genuinely browsable API surface."""
    starlette_app = mcp.http_app(path="/mcp")
    starlette_app.routes.append(Route("/api/health", _health))
    return starlette_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="splatmaker-mcp")
    parser.add_argument("--http", action="store_true", help="Run streamable HTTP transport instead of stdio")
    parser.add_argument("--port", type=int, default=BACKEND_PORT)
    args = parser.parse_args()

    if args.http:
        import uvicorn

        async def _startup():
            await _register_with_hub()

        app = build_http_app()
        app.router.on_startup.append(_startup)
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    else:
        mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
