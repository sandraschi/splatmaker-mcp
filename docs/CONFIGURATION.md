# CONFIGURATION — splatmaker-mcp

All configuration is via environment variables (see `.env.example` — copy to `.env`, never commit `.env`).

| Variable | Default | Purpose |
|---|---|---|
| `SPLATMAKER_MAX_ITERATIONS` | `15000` | `ns-train splatfacto --max-num-iterations`. Half of Nerfstudio's own 30000 default — deliberate tradeoff: full default is tuned for research-grade quality over unattended speed. Raise toward 30000 when quality matters more than turnaround. |
| `SPLATMAKER_HOST` | `127.0.0.1` | HTTP bind host (`run_server.py` / Tauri sidecar). |
| `SPLATMAKER_PORT` | `11091` | HTTP bind port. `MCP_PORT` is honored as a fallback. Fleet registry pair is 11091 backend / 11092 frontend. |
| `SPLATMAKER_LOG_LEVEL` | `info` | uvicorn log level for the sidecar. |
| `SPLATMAKER_JOBS_DB` | `~/.splatmaker-mcp/jobs.db` | SQLite job-store override (tests set this to a tmp file; set it manually to relocate the store). |

Engine install (one time, sizeable ~276 packages, torch+CUDA/nerfstudio/gsplat):

```powershell
uv sync --extra engine
uv run --extra engine ns-train --help
```

WARNING: a plain `uv sync` (without `--extra engine`, e.g. the justfile
`sync` recipe or CI) silently UNINSTALLS the engine packages again — uv
prunes extras not in the target set (observed 2026-11-01: ns-train crashed
on missing absl/appdirs after such a prune). Always re-sync WITH the extra
after any plain sync: `just sync-engine`. Verify with
`ns-train --help` (exit 0). The webapp Status page reports the cached
`ns-train --help` truth (`engine_verified`), not just exe presence.

Requires Python 3.12 (`requires-python = ">=3.12,<3.13"` — nerfstudio's `open3d` has no 3.13 wheel). Job state lives in `~/.splatmaker-mcp/jobs.db` (SQLite) and `~/.splatmaker-mcp/jobs/<id>/` (work dirs).
