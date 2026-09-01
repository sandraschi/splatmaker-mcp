"""Entry point - dual transport per fleet standard: stdio (default, for
Claude Desktop / Cursor) or streamable HTTP on /mcp (for the webapp + hub).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse

from splatmaker_mcp.server import (
    BACKEND_PORT,
    _do_shutdown,
    _jobs,
    _register_with_hub,
    health_payload,
    mcp,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_VAULT_PATH = Path.home() / ".advanced-memory" / "vault"
_DB_PATH_MEM = Path.home() / ".advanced-memory" / "memory.db"


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


async def _backup_status(request):  # noqa: ANN001
    vault_files = sum(1 for _ in _VAULT_PATH.rglob("*.md")) if _VAULT_PATH.exists() else 0
    vault_mb = (
        sum(f.stat().st_size for f in _VAULT_PATH.rglob("*") if f.is_file()) / (1024 * 1024)
        if _VAULT_PATH.exists()
        else 0
    )
    db_mb = _DB_PATH_MEM.stat().st_size / (1024 * 1024) if _DB_PATH_MEM.exists() else 0
    return JSONResponse(
        {
            "vault_path": str(_VAULT_PATH),
            "vault_files": vault_files,
            "vault_mb": round(vault_mb, 1),
            "db_mb": round(db_mb, 1),
            "derivative": "memory.db + vectors/ rebuilt from vault markdown — vault only needed",
        }
    )


async def _backup_vault(request):  # noqa: ANN001
    import io
    import zipfile

    from starlette.responses import StreamingResponse

    if not _VAULT_PATH.exists():
        return JSONResponse(status_code=404, content={"error": f"vault not found: {_VAULT_PATH}"})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in _VAULT_PATH.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(_VAULT_PATH.parent))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=memops-vault-{time.strftime('%Y-%m-%d')}.zip"
        },
    )


async def _restore_vault(request: Request):  # noqa: ANN001
    import io
    import shutil
    import zipfile

    data = await request.body()
    ctype = request.headers.get("content-type", "")
    if "multipart/form-data" in ctype:
        form = await request.form()
        file = form.get("file")
        if not file:
            return JSONResponse(status_code=400, content={"error": "missing file field"})
        data = await file.read()
    if not data or data[:2] != b"PK":
        return JSONResponse(status_code=400, content={"error": "not a zip (PK header missing)"})
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = _VAULT_PATH.parent / f"vault.bak-{ts}"
    if _VAULT_PATH.exists():
        shutil.copytree(_VAULT_PATH, backup_dir)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if not any(n.endswith(".md") for n in zf.namelist()):
                return JSONResponse(status_code=400, content={"error": "zip contains no .md files"})
            if _VAULT_PATH.exists():
                shutil.rmtree(_VAULT_PATH)
            _VAULT_PATH.mkdir(parents=True, exist_ok=True)
            for member in zf.infolist():
                name = member.filename
                if name.startswith("vault/"):
                    name = name[len("vault/") :]
                target = _VAULT_PATH / name
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
    except Exception as e:
        logging.getLogger("splatmaker_mcp").exception("restore failed")
        return JSONResponse(status_code=500, content={"error": str(e), "backup": str(backup_dir)})
    return JSONResponse(
        {
            "status": "restored",
            "vault": str(_VAULT_PATH),
            "backup": str(backup_dir),
            "note": "db/vectors will re-embed on next sync",
        }
    )


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
    starlette_app.add_route("/api/jobs", _jobs_list)
    starlette_app.add_route("/api/backup/status", _backup_status)
    starlette_app.add_route("/api/backup/vault", _backup_vault)
    starlette_app.add_route("/api/backup/restore", _restore_vault, methods=["POST"])
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
