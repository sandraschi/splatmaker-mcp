# TROUBLESHOOTING — splatmaker-mcp

## `uv run pytest` (bare) fails with "program not found"

`uv run` re-syncs to the base dependency group on every invocation, pruning the `dev` extras. Always pass the extra: `uv run --extra dev pytest`, or use `just test` / `just lint` (they do this correctly).

## Engine reports `not_implemented` / `engine_configured: false`

The `engine` extra is not installed in the active venv: `uv sync --extra engine`. Verify with `uv run --extra engine ns-train --help` and `python -c "import torch; print(torch.cuda.is_available())"`. Needs Python 3.12 (open3d has no 3.13 wheel) and an NVIDIA GPU for real training.

## `http://localhost:PORT/...` 404s against a healthy server

On this machine `localhost` can resolve to a path that misses the bound socket; `http://127.0.0.1:PORT/...` works. The webapp and launcher always use `127.0.0.1`. (Fleet TRAPS_AND_PITFALLS #8.)

## Dashboard says unreachable but curl is fine

curl never exercises the browser CORS path. Check the vite proxy (`/api/*` → `:11091`) and the `Origin` the tab actually sends — absolute backend URLs only work from `localhost` tabs or the Tauri gate. See `__main__.py` CORSMiddleware origins.

## Nerfstudio demo datasets fail with Google permission/quota errors

External issue on Google's side (tried two capture names, same failure). Use Sandra's own photos/video instead — single directory preferred, scattered multi-dir sets are auto-staged.

## Jobs disappear after restart

Pre-0.2.0 behavior (in-memory store). v0.2.0 persists to `~/.splatmaker-mcp/jobs.db`. If the DB path is not writable, jobs fall back to memory-only and log `job save failed`.
