# CHANGELOG (latest release only - see git log for full history)

## 0.2.0 — 2026-07-13

Engine decided and implemented: Nerfstudio/Splatfacto (gsplat as rasterization backend). Real `SplatBackend`: `ns-process-data` → `ns-train splatfacto` → `ns-export gaussian-splat` subprocess pipeline, all flags verified against actual `--help` output (not guessed). Background async job execution — tool calls return immediately with a job_id rather than blocking on real multi-minute training runs; poll with `operation=status`.

Postshot scratched entirely as a candidate: its CLI (the only tier with real automation value) turned out to be a paid Studio-tier feature (~£40pcm) despite the app downloading free — a free-download/paid-CLI split that reads as bait-and-switch regardless of underlying business reasoning. gsplat ruled out earlier as bare-library/no-CLI/too-much-glue.

Installed and verified live on Goliath: `torch 2.6.0+cu124`, CUDA available, RTX 4090 detected, `gsplat 1.0.0` importable, real `ns-train`/`ns-process-data`/`ns-export` executables present and correct. 8/8 tests passing.

**Not yet done:** a full end-to-end training run against real capture data. Nerfstudio's own Google Drive-hosted demo datasets are currently blocked by an external Google permission/quota issue (tried two capture names, same failure both times — not our code). Mechanical pipeline verification (flags, executables, control flow) is complete; producing an actual photorealistic splat needs real photos/video, which was always the plan — same "get real reference material before writing the wrapper" discipline as vcv-rack-mcp's reference patches and Boomy's Leash's ARKit survey. No SQLite persistence yet (jobs are in-memory, lost on restart). Webapp is still a skeleton. No MCPB bundle.

## 0.1.0 — 2026-07-13 (initial scaffold)

Initial scaffold. FastMCP 3.2+ server shell, dual transport (stdio + HTTP), portmanteau `splat_generate` tool, `splat_engine_status` tool, in-memory job tracking, fleet health/registration contract (`/api/health`, hub registration on startup).

**Fixed during real verification (2026-07-13), not just written and assumed correct:**
- Hub registration silently logged "Registered" on any non-exception HTTP response, including a 404 - now checks status code and logs an honest warning instead.
- `--http` startup crashed on `app.router.on_startup.append(...)` - `AttributeError: 'Router' object has no attribute 'on_startup'` on this Starlette version. Registration moved out of the ASGI lifespan hook entirely (runs synchronously before uvicorn starts) rather than depending on a Starlette API that drifted.
- `/api/health` route silently 404'd - `app.routes.append(Route(...))` does not reliably back the live router table on FastMCP's `StarletteWithLifespan`; fixed with `app.add_route(...)`, the actual registration API.
- `pytest-asyncio` was missing from dev deps despite tests using `@pytest.mark.asyncio` - added, plus `asyncio_mode = "auto"` in `[tool.pytest.ini_options]`.
- `uv run pytest` (bare) fails because `uv run` resyncs to the base dependency group on every call, pruning `dev` extras - documented in INSTALL.md and fixed in the justfile (`uv run --extra dev pytest`).
- On this machine specifically: `http://localhost:PORT/...` returns a false 404 against a genuinely healthy server; `http://127.0.0.1:PORT/...` works. Filed as mcp-central-docs/standards/TRAPS_AND_PITFALLS.md #8.
