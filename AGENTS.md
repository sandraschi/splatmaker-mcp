# AGENTS.md — splatmaker-mcp

Self-hosted Gaussian-splat generation (Nerfstudio/Splatfacto) as a Fleet MCP server.

## Entry points

- `src/splatmaker_mcp/server.py` — FastMCP tools (`splat_generate`, `splat_engine_status`, `server_shutdown`), SQLite job store (`~/.splatmaker-mcp/jobs.db`), Nerfstudio subprocess pipeline.
- `src/splatmaker_mcp/__main__.py` — dual transport: stdio (`mcp.run()`) or HTTP (`--http --port 11091`); builds the Starlette app (`/api/*` + `/mcp`).
- `run_server.py` — PyInstaller sidecar: HTTP only (Tauri backend exe). Must stay HTTP-only; stdio lives in `__main__`.
- Webapp: `webapp/` (Vite React, :11092, proxies `/api` + `/mcp` to :11091).

## HTTP daemon

- Backend port 11091, frontend 11092 (fleet registry `WEBAPP_PORTS.md`).
- No NSSM service currently. If one is ever registered: probe `GET /api/health` before DB init is NOT yet implemented in stdio `main()` (open item M10) — add before relying on double-daemon setups.
- Shutdown: `POST /api/shutdown` or `server_shutdown` tool (shared `_do_shutdown`, ~500ms delayed `os._exit`).

## Env

- `SPLATMAKER_MAX_ITERATIONS` (default 15000, half of Nerfstudio's 30000 default — deliberate).
- `SPLATMAKER_HOST` / `SPLATMAKER_PORT` (also honors `MCP_PORT`), `SPLATMAKER_LOG_LEVEL`.
- Engine extra: `uv sync --extra engine` (torch+CUDA, nerfstudio, gsplat). Base install runs; engine calls honestly report `not_implemented` without it.
- See `.env.example` (template) and `docs/CONFIGURATION.md`.

## Key files

- `docs/TOOLS.md` (tool + REST reference), `docs/TROUBLESHOOTING.md`, `docs/DEVELOPMENT.md`, `llms-full.txt`.
- Tests: `uv run --extra dev pytest` (8 tests). Lint: `uv run --extra dev ruff check src tests`. Web type: `bun x tsc --noEmit -p webapp`.
