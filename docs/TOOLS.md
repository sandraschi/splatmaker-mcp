# TOOLS — splatmaker-mcp

## MCP tools (stdio + HTTP `/mcp`)

### `splat_generate(operation, video_path?, image_paths?, job_id?)`

Portmanteau. `operation` is one of:

- `from_video` — start a job from a local video file. Requires `video_path`. Returns immediately with `status: "queued"`; the `ns-process-data → ns-train → ns-export` pipeline runs in the background. Poll with `status`.
- `from_images` — start a job from image files. Requires `image_paths`. A single directory is passed straight through; scattered files from multiple directories are staged into a temp dir first.
- `status` — one job's status/message. Requires `job_id`.
- `list` — all known jobs (persisted in SQLite, survives restart).
- `get_asset` — asset paths (`ply`, `config`, `job_dir`) for a `done` job. Requires `job_id`.

All returns carry `success` + `message`; failures also carry `error`.

### `splat_engine_status()`

`{success, engine, configured, max_iterations, note, message}`. `configured` is False until `uv sync --extra engine` puts the real `ns-*` CLI on PATH.

### `server_shutdown()`

`{success, status: "shutting_down", message}`. Same implementation as `POST /api/shutdown`.

## Prompt + resource

- Prompt `splat_workflow` — guided capture → generate → poll → fetch → collider-mesh briefing.
- Resource `splatmaker://jobs` — live job ledger JSON (same rows as `GET /api/jobs`).

## REST (backend :11091)

| Method + path | Purpose |
|---|---|
| `GET /api/health` | Liveness probe for `start.ps1` / frontend dot. |
| `GET /api/status` | Tool list, job counts by status, uptime. |
| `GET /api/capabilities` | Machine-readable tool catalog + REST routes + ports. |
| `GET /api/jobs` | All jobs. |
| `POST /api/jobs/status` | Body `{"job_id": ...}` → status/message. |
| `POST /api/shutdown` | Orderly exit (responds 200, exits ~500ms later). |

## Downstream note (load-bearing)

None of the FOSS engines emit a collision mesh. Every splat consumed by Blender/Resonite/VRChat MUST be routed through `blender-mcp`'s `blender_splatting` collision-mesh stage first. Skipping it yields a correct-looking render with no floor.
