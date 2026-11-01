# CHANGELOG (latest release only - see git log for full history)

## Unreleased — assfix 2026-11-01 (engine truth + catch-them-all webapp)

- Engine truth: `ns-train` CLI was broken (missing absl/appdirs after a plain `uv sync` pruned the engine extra) while `is_configured()` reported ready on exe presence alone. Repaired (`uv pip install nerfstudio` full tree; verified `ns-train --help` exit 0, nerfstudio 1.1.4). New cached background `ns-train --help` probe: `/api/status` + `splat_engine_status` now report `engine_verified` (pending/ok/broken/missing) + `engine_version` + `engine_error`. Dashboard shows a repair banner when not ok.
- `just sync-engine` recipe (the only correct engine install; plain sync strips it — documented in CONFIGURATION.md).
- New REST: `GET /api/skills`, `GET /api/logs` (500-line ring), `GET /api/llm/models` + `POST /api/llm/chat` (local Ollama passthrough, proven live with llama3.2:3b).
- Webapp catch-them-all: Tools, Skills, Help (incl. what-Nerfstudio-is + install/repair), Logs, Inbox (failed/in-flight jobs), Chat (local models, persisted history), plus real Gallery (finished jobs + .ply paths) and Settings (engine + env). Nav grew 5 → 11 entries.
- CSS gate (`scripts/gate-web-css.ps1`) wired into `just gates` + CI: built CSS < 5 kB or raw `@tailwind` fails loudly.

## Unreleased — assfix 2026-11-01 (earlier same day)

- Webapp: added `@tauri-apps/api ^2.2.0` dependency (checklist 1H gate — was the single HIGH blocking the native row; `bun install` + `tsc` + `biome:ci` re-proven green).
- Tests: SQLite job-store isolation — `SPLATMAKER_JOBS_DB` env override plus `tests/conftest.py` bootstrap and a per-test tmp fixture, so pytest no longer writes failed-job rows to the real `~/.splatmaker-mcp/jobs.db` (M36 closed; proven: real DB mtime untouched by a full run).
- Testing: `pytest-cov` in dev extras with `--cov-fail-under=40` enforced (51% measured, 8/8 passing).
- Error handling: shared `_error_response()` helper with `logger.exception` auto-logging (TOOL_DESIGN_STANDARDS.md §7.1 Pattern 3; M14 closed).
- justfile: `gates` aggregate (ruff + format-check + pytest + tsc + biome), `build-native` (Tauri NSIS via `src-tauri/build.ps1`), honest `mcpb-pack` guard (runs the fleet MCPB audit; fails loudly while issue #1 has no compliant manifest), `bootstrap` now also installs webapp deps (`bun install --frozen-lockfile`; L10 closed).

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
