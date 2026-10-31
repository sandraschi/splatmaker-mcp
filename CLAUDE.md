# CLAUDE.md — splatmaker-mcp (per-repo agent instructions)

## What this is

Self-hosted, zero-marginal-cost Gaussian-splat generation. FOSS alternative to worldlabs-mcp's Marble API: photo/video in, navigable 3D splat out, on the local RTX 4090 via Nerfstudio/Splatfacto. Downstream: `blender-mcp` (collision mesh — mandatory, this server produces no collider) → Resonite/VRChat.

## Standards that apply

Fleet hub: `D:\Dev\repos\mcp-central-docs\`. Read before coding:
`standards/TOOL_DESIGN_STANDARDS.md` (portmanteau, dialogic returns, docstrings),
`standards/STARLETTE_NO_PYDANTIC_STANDARD.md` (Starlette for small REST surfaces),
`standards/TAURI_PRODUCTION_PITFALLS.md` before any NSIS build,
`troubleshooting/BUGS_DEPOT.md` by symptom before debugging.

## Entry points & commands

- Server: `src/splatmaker_mcp/server.py` + `__main__.py`. Run stdio: `uv run splatmaker-mcp`. HTTP: `uv run splatmaker-mcp --http --port 11091`. Just: `just serve`, `just test`, `just lint`, `just fmt`.
- Webapp: `webapp/` (`bun install`, `bun run dev` on :11092). Typecheck: `bun x tsc --noEmit -p webapp`.
- Tests need the dev extra: `uv run --extra dev pytest` (bare `uv run pytest` prunes dev deps and fails).

## Non-obvious, do not regress

- `mcp.http_app(path="/mcp")` is returned directly — never re-mount under `/mcp` (double-prefix 404) and never call `run_http_async` (drops CORS).
- Routes must be added with `app.add_route(...)`, not `app.routes.append(...)` (silent 404s).
- Hub registration runs synchronously before uvicorn starts (no ASGI startup hook — Starlette router hooks drift across versions).
- Frontend uses same-origin `/api` via vite proxy; absolute `127.0.0.1:11091` only behind the Tauri gate in `lib/api.ts`.
- `SplatBackend` flags were verified against real `--help` output; `max_iterations` default is a documented tradeoff, not a guess.
- No `print()` in `src/` (ruff T20 enforced). No bare `except:`. Errors return `success: False` + `error` + `message`.
