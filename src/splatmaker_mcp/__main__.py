"""Entry point - dual transport per fleet standard: stdio (default, for
Claude Desktop / Cursor) or streamable HTTP on /mcp (for the webapp + hub).
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from splatmaker_mcp.server import (
    BACKEND_PORT,
    SERVER_ID,
    SERVER_VERSION,
    _do_shutdown,
    _jobs,
    _register_with_hub,
    health_payload,
    mcp,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _health(request):  # noqa: ANN001 - Starlette handler signature
    return JSONResponse(health_payload())


async def _jobs_list(request):  # noqa: ANN001
    return JSONResponse(
        {
            "jobs": [
                {
                    "job_id": j.id,
                    "kind": j.kind,
                    "status": j.status,
                    "created_at": j.created_at,
                    "message": j.message,
                }
                for j in _jobs.values()
            ]
        }
    )


async def _shutdown(request):  # noqa: ANN001 - Starlette handler signature
    await _do_shutdown()
    return JSONResponse({"status": "shutting_down", "message": "Server will exit in ~0.5s"})


async def _status(request):  # noqa: ANN001 - Starlette handler signature
    h = health_payload()
    return JSONResponse(
        {
            "server": h["server"],
            "version": h["version"],
            "status": h["status"],
            "uptime_seconds": h["uptime_seconds"],
            "engine_configured": h["engine_configured"],
            "tool_count": 3,
            "tools": ["splat_generate", "splat_engine_status", "server_shutdown"],
            "job_count": len(_jobs),
            "jobs_by_status": {
                s: sum(1 for j in _jobs.values() if j.status == s)
                for s in ("queued", "running", "done", "failed")
            },
        }
    )


async def _capabilities(request):  # noqa: ANN001 - Starlette handler signature
    return JSONResponse(
        {
            "server": SERVER_ID,
            "version": SERVER_VERSION,
            "tools": [
                {
                    "name": "splat_generate",
                    "operations": ["from_video", "from_images", "status", "list", "get_asset"],
                    "description": "Generate or inspect a Gaussian-splat world from local media.",
                },
                {
                    "name": "splat_engine_status",
                    "operations": [],
                    "description": "Report which splat engine is configured and whether its CLI is present.",
                },
                {
                    "name": "server_shutdown",
                    "operations": [],
                    "description": "Gracefully shut down this server.",
                },
            ],
            "rest": [
                "/api/health",
                "/api/status",
                "/api/capabilities",
                "/api/jobs",
                "/api/v1/diagnostics",
            ],
            "ports": {"backend": BACKEND_PORT},
        }
    )


async def _diagnostics(request):  # noqa: ANN001 - Starlette handler signature
    import platform

    h = health_payload()
    return JSONResponse(
        {
            "server": SERVER_ID,
            "version": SERVER_VERSION,
            "tools": ["splat_generate", "splat_engine_status", "server_shutdown"],
            "system": {"python": platform.python_version(), "platform": platform.platform()},
            "engine_configured": h["engine_configured"],
            "job_count": len(_jobs),
            "errors": [],
        }
    )


async def _job_status(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": 'invalid JSON body, expected {"job_id": ...}'}, status_code=400
        )
    job_id = body.get("job_id") if isinstance(body, dict) else None
    job = _jobs.get(job_id) if job_id else None
    if job is None:
        return JSONResponse({"error": f"unknown job_id: {job_id!r}"}, status_code=404)
    return JSONResponse({"job_id": job.id, "status": job.status, "message": job.message})


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
    # Fleet CORS standard: explicit origins + unconditional regex for
    # Tailscale/LAN, plus the Tauri WebView schemes. Never allow_origins=["*"].
    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:11092",
            "http://localhost:11092",
            "tauri://localhost",
            "http://tauri.localhost",
            "https://tauri.localhost",
        ],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|[a-z0-9-]+(\.[a-z0-9-]+)*)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    starlette_app.add_route("/api/health", _health)
    starlette_app.add_route("/api/status", _status)
    starlette_app.add_route("/api/capabilities", _capabilities)
    starlette_app.add_route("/api/jobs", _jobs_list)
    starlette_app.add_route("/api/jobs/status", _job_status, methods=["POST"])
    starlette_app.add_route("/api/v1/diagnostics", _diagnostics)
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
