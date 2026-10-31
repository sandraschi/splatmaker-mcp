# ONBOARDING — splatmaker-mcp

## What you need

- Windows 10/11, Python 3.12, an NVIDIA GPU (RTX 4090 used for all verification; smaller VRAM works with lower `--max-num-iterations`).
- No account, no API key, no payment anywhere in this pipeline. The engine is Apache-2.0 (Nerfstudio) + PyTorch.

## Install (5 minutes + one big download)

```powershell
git clone https://github.com/sandraschi/splatmaker-mcp.git
cd splatmaker-mcp
uv sync            # base server + webapp shell
.\start.ps1        # backend :11091, frontend :11092, opens the dashboard
```

Engine (real training — ~276 packages, several GB, one time):

```powershell
uv sync --extra engine
uv run --extra engine python -c "import torch; print(torch.cuda.is_available())"
```

Copy `.env.example` to `.env` if you want non-default iterations or ports.

## First splat (sanity path)

1. Dashboard should show Backend `ok` and Engine `ready` (or `not configured` until the engine extra is installed).
2. From Claude/Cursor: `splat_generate(operation="from_video", video_path="D:/cap/walk.mp4")` → `job_id`.
3. Poll `splat_generate(operation="status", job_id="...")` until `done` (real training takes real minutes).
4. `splat_generate(operation="get_asset", job_id="...")` → `.ply` path under `~/.splatmaker-mcp/jobs/<id>/export/`.
5. Route the `.ply` through `blender-mcp` `blender_splatting` for a collision mesh before any VR use.

## If the engine shows "not configured"

See `docs/TROUBLESHOOTING.md` — 90% of the time the `engine` extra is missing from the active venv, or the venv is Python 3.13 (needs 3.12 for open3d).
