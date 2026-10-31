# DEVELOPMENT — splatmaker-mcp

## Layout

- `src/splatmaker_mcp/server.py` — FastMCP tools, `SplatBackend` (ns-process-data → ns-train splatfacto → ns-export gaussian-splat), SQLite job store.
- `src/splatmaker_mcp/__main__.py` — dual transport + Starlette REST (`/api/*`, `/mcp`). Edit CORS/origins here.
- `run_server.py` — PyInstaller/Tauri sidecar. HTTP-only by design; do not add stdio fallback (the Tauri backend spawns it expecting a bound port).
- `webapp/` — Vite React dashboard (:11092). Same-origin `/api` via proxy; Tauri gate in `src/lib/api.ts`.
- `src-tauri/` — Tauri shell (NSIS target). Backend versions are pinned to the package version (0.2.0).

## Commands

```powershell
just serve        # HTTP backend on :11091
just test         # uv run --extra dev pytest -v
just lint         # ruff check src tests
just fmt          # ruff format src tests
```

Webapp: `bun install` once, then `bun run dev` (in `webapp/`). Typecheck: `bun x tsc --noEmit -p webapp`.

## Conventions (fleet)

- No `print()` in `src/` (ruff T20). Logging via module `logger`; `logger.exception` inside `except`.
- Tool returns are dialogic: `success` + `message` always; `error` key kept on failures for compat.
- Docstrings need `## Return Format` + `## Examples` (fleet docstring standard).
- CORS: explicit origins + LAN/Tailscale regex in `__main__.py`. Never `allow_origins=["*"]`.
- Routes via `app.add_route(...)` — never `app.routes.append(...)` (silent 404s on this Starlette version).
- `mcp.http_app(path="/mcp")` is served directly — never re-mount under `/mcp`, never `run_http_async`.
