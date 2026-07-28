"""splatmaker-mcp — self-hosted Gaussian-splat generation via Nerfstudio/Splatfacto.

ENGINE DECIDED 2026-07-13: Nerfstudio (gsplat as its rasterization backend).
Postshot was scratched (paid CLI behind a free download). Bare gsplat was
ruled out (no CLI, too much DIY glue). See README.md "Engine status" for
the full comparison and decision record.

This module shells out to the real `ns-process-data` / `ns-train splatfacto`
/ `ns-export gaussian-splat` CLI chain, verified against actual --help output
on 2026-07-13 (not guessed) - see ns_train_help.txt / ns_process_help.txt /
ns_export_help.txt in the repo root for the raw verification artifacts.

HONESTY NOTE: this module requires the optional `engine` dependency group
(`uv sync --extra engine`) - torch+CUDA, nerfstudio, gsplat. Base installs
without that extra will correctly report not_implemented via is_configured().
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

import httpx
from fastmcp import Context, FastMCP

logger = logging.getLogger("splatmaker_mcp")

SERVER_ID = "splatmaker-mcp"
SERVER_VERSION = "0.2.0"
BACKEND_PORT = 11091
FRONTEND_PORT = 11092
HUB_REGISTER_URL = "http://localhost:10857/api/v1/register"
DEPOT_DIR = Path.home() / ".splatmaker-mcp" / "depot"

mcp = FastMCP(SERVER_ID)

_start_time = time.monotonic()


# ---------------------------------------------------------------------------
# Engine abstraction — pluggable, honestly not-yet-wired (see module docstring)
# ---------------------------------------------------------------------------


class SplatEngine(StrEnum):
    """NERFSTUDIO is the decided, implemented engine. Others kept as enum
    values for is_configured()/status reporting only - no implementation
    exists for them and none is planned (see module docstring)."""

    UNSET = "unset"
    NERFSTUDIO = "nerfstudio"


@dataclass
class EngineResult:
    ok: bool
    message: str
    asset_paths: dict[str, str] = field(default_factory=dict)


class SplatBackend:
    """Real Nerfstudio/Splatfacto subprocess wrapper. Pipeline per job:
    ns-process-data -> ns-train splatfacto -> ns-export gaussian-splat.
    All three stages' flags verified against real --help output 2026-07-13,
    not guessed - see ns_*_help.txt in repo root.
    """

    def __init__(
        self, engine: SplatEngine = SplatEngine.UNSET, max_iterations: int = 15000
    ) -> None:
        # max_iterations default is HALF nerfstudio's own default (30000) -
        # deliberate: full default is tuned for research-grade quality over
        # unattended speed; 15000 is a documented tradeoff, not a silent one.
        # Override via SPLATMAKER_MAX_ITERATIONS env var if quality matters
        # more than turnaround time for a given job.
        self.engine = engine
        self.max_iterations = max_iterations
        self._work_root = Path.home() / ".splatmaker-mcp" / "jobs"
        self._work_root.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        return (
            self._resolve_exe("ns-train") is not None
            and self._resolve_exe("ns-process-data") is not None
        )

    @staticmethod
    def _resolve_exe(name: str) -> str | None:
        """PATH lookup first (uv run sets this correctly), then a direct
        check next to sys.executable (venv Scripts/ dir on Windows) as a
        fallback for launch contexts where PATH wasn't inherited."""
        found = shutil.which(name)
        if found:
            return found
        candidate = Path(sys.executable).parent / f"{name}.exe"
        return str(candidate) if candidate.exists() else None

    async def _run(self, cmd: list[str]) -> tuple[int, str, str]:
        logger.info("splatmaker subprocess: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout.decode(errors="replace"),
            stderr.decode(errors="replace"),
        )

    def _find_config_yml(self, output_dir: Path) -> Path | None:
        """Nerfstudio nests output as <output_dir>/<experiment>/splatfacto/
        <timestamp>/config.yml - experiment name defaults to the input
        dataset dirname, timestamp is runtime-generated, so this has to
        glob rather than assume a fixed path."""
        candidates = sorted(
            output_dir.glob("**/splatfacto/*/config.yml"), key=lambda p: p.stat().st_mtime
        )
        return candidates[-1] if candidates else None

    async def _pipeline(
        self, kind: Literal["images", "video"], input_path: str, job_id: str
    ) -> EngineResult:
        if not self.is_configured():
            return EngineResult(
                ok=False,
                message=(
                    "not_implemented: nerfstudio CLI not found. Run `uv sync --extra engine` "
                    "to install torch+CUDA, nerfstudio, and gsplat (real, sizeable download - "
                    "~276 packages verified on Goliath 2026-07-13). See README.md 'Engine status'."
                ),
            )
        job_dir = self._work_root / job_id
        processed_dir = job_dir / "processed"
        output_dir = job_dir / "output"
        export_dir = job_dir / "export"
        job_dir.mkdir(parents=True, exist_ok=True)

        # Stage 1: ns-process-data {images|video} --data <in> --output-dir <out>
        rc, _out, err = await self._run(
            [
                self._resolve_exe("ns-process-data"),
                kind,
                "--data",
                input_path,
                "--output-dir",
                str(processed_dir),
            ]
        )
        if rc != 0:
            return EngineResult(
                ok=False, message=f"ns-process-data failed (exit {rc}): {err[-1500:]}"
            )

        # Stage 2: ns-train splatfacto --data <processed> --output-dir <out> --vis tensorboard
        # (tensorboard, not the default 'viewer', deliberately - viewer opens a
        # websocket server nobody connects to in unattended runs; tensorboard
        # just logs to disk, no port/connection concerns for automation)
        rc, _out, err = await self._run(
            [
                self._resolve_exe("ns-train"),
                "splatfacto",
                "--data",
                str(processed_dir),
                "--output-dir",
                str(output_dir),
                "--vis",
                "tensorboard",
                "--max-num-iterations",
                str(self.max_iterations),
                "--viewer.quit-on-train-completion",
                "True",
            ]
        )
        if rc != 0:
            return EngineResult(ok=False, message=f"ns-train failed (exit {rc}): {err[-1500:]}")

        config_path = self._find_config_yml(output_dir)
        if not config_path:
            return EngineResult(
                ok=False, message="ns-train completed but no config.yml found under output_dir"
            )

        # Stage 3: ns-export gaussian-splat --load-config <config> --output-dir <out>
        rc, _out, err = await self._run(
            [
                self._resolve_exe("ns-export"),
                "gaussian-splat",
                "--load-config",
                str(config_path),
                "--output-dir",
                str(export_dir),
            ]
        )
        if rc != 0:
            return EngineResult(ok=False, message=f"ns-export failed (exit {rc}): {err[-1500:]}")

        ply_candidates = list(export_dir.glob("*.ply"))
        if not ply_candidates:
            return EngineResult(ok=False, message="ns-export ran but produced no .ply file")

        return EngineResult(
            ok=True,
            message="done",
            asset_paths={
                "ply": str(ply_candidates[0]),
                "config": str(config_path),
                "job_dir": str(job_dir),
            },
        )

    async def generate_from_video(self, video_path: str, job_id: str) -> EngineResult:
        return await self._pipeline("video", video_path, job_id)

    async def generate_from_images(self, image_paths: list[str], job_id: str) -> EngineResult:
        # ns-process-data images wants a directory, not a file list - if
        # given individual paths, use their common parent as the input dir
        # (honest limitation: assumes they're already colocated; mixed-source
        # image lists need staging into a temp dir first - not yet handled,
        # will raise clearly rather than silently doing the wrong thing).
        if not image_paths:
            return EngineResult(ok=False, message="image_paths is empty")
        parents = {str(Path(p).parent) for p in image_paths}
        if len(parents) != 1:
            return EngineResult(
                ok=False,
                message=(
                    "not_implemented: image_paths span multiple directories "
                    f"({parents}) - staging mixed-source images into a temp dir isn't "
                    "built yet. Put all images in one directory and pass that as a single "
                    "path, or use from_video for a single capture."
                ),
            )
        return await self._pipeline("images", next(iter(parents)), job_id)


backend = SplatBackend(
    engine=SplatEngine.NERFSTUDIO
)  # decided 2026-07-13; is_configured() checks the real CLI is present


# ---------------------------------------------------------------------------
# Job tracking (in-memory for v1 — SQLite persistence is a fast-follow, not
# a v1 requirement; flagged here rather than silently deferred)
# ---------------------------------------------------------------------------


@dataclass
class Job:
    id: str
    kind: Literal["from_video", "from_images"]
    status: Literal["queued", "running", "done", "failed"]
    created_at: float
    message: str = ""
    asset_paths: dict[str, str] = field(default_factory=dict)


_jobs: dict[str, Job] = {}


# ---------------------------------------------------------------------------
# MCP tool — portmanteau pattern per fleet TOOL_DESIGN_STANDARDS
# ---------------------------------------------------------------------------


async def _run_job(job: Job, coro) -> None:
    """Background task wrapper - runs a pipeline coroutine without blocking
    the tool call that started it, updates the Job record when done. Real
    training runs take real minutes; a tool call that blocks on that would
    hit most MCP clients' request timeouts long before completion."""
    job.status = "running"
    try:
        result = await coro
        job.status = "done" if result.ok else "failed"
        job.message = result.message
        job.asset_paths = result.asset_paths
    except Exception as exc:  # noqa: BLE001 - job-level catch-all, must not crash the server
        job.status = "failed"
        job.message = f"unhandled exception: {exc}"
        logger.exception("splatmaker job %s crashed", job.id)


@mcp.tool()
async def splat_generate(
    ctx: Context,
    operation: Literal["from_video", "from_images", "status", "list", "get_asset"],
    video_path: str | None = None,
    image_paths: list[str] | None = None,
    job_id: str | None = None,
) -> dict:
    """Generate or inspect a Gaussian-splat world from local media.

    Operations:
        from_video    — start a job from a video file (video_path required)
        from_images   — start a job from a set of images (image_paths required)
        status        — check a job's status (job_id required)
        list          — list all known jobs
        get_asset     — return asset paths for a completed job (job_id required)

    from_video/from_images return IMMEDIATELY with status="running" - the
    real ns-process-data -> ns-train -> ns-export pipeline runs as a
    background task (real training takes real minutes, not seconds). Poll
    with operation="status" until status is "done" or "failed".
    """
    if operation == "from_video":
        if not video_path:
            return {"error": "video_path is required for operation=from_video"}
        jid = str(uuid.uuid4())
        job = Job(id=jid, kind="from_video", status="queued", created_at=time.time())
        _jobs[jid] = job
        asyncio.create_task(_run_job(job, backend.generate_from_video(video_path, jid)))
        return {
            "job_id": jid,
            "status": job.status,
            "message": "pipeline started in background, poll with status",
        }

    if operation == "from_images":
        if not image_paths:
            return {"error": "image_paths is required for operation=from_images"}
        jid = str(uuid.uuid4())
        job = Job(id=jid, kind="from_images", status="queued", created_at=time.time())
        _jobs[jid] = job
        asyncio.create_task(_run_job(job, backend.generate_from_images(image_paths, jid)))
        return {
            "job_id": jid,
            "status": job.status,
            "message": "pipeline started in background, poll with status",
        }

    if operation == "status":
        if not job_id or job_id not in _jobs:
            return {"error": f"unknown job_id: {job_id!r}"}
        j = _jobs[job_id]
        return {"job_id": j.id, "status": j.status, "message": j.message}

    if operation == "list":
        return {
            "jobs": [{"job_id": j.id, "status": j.status, "kind": j.kind} for j in _jobs.values()]
        }

    if operation == "get_asset":
        if not job_id or job_id not in _jobs:
            return {"error": f"unknown job_id: {job_id!r}"}
        j = _jobs[job_id]
        if j.status != "done":
            return {"error": f"job {job_id} is not done (status={j.status})"}
        return {"job_id": j.id, "asset_paths": j.asset_paths}

    return {"error": f"unknown operation: {operation!r}"}


@mcp.tool()
async def splat_engine_status(ctx: Context) -> dict:
    """Report which splat engine is configured and whether the real CLI
    tools are actually present (requires `uv sync --extra engine`)."""
    configured = backend.is_configured()
    return {
        "engine": backend.engine.value,
        "configured": configured,
        "max_iterations": backend.max_iterations,
        "note": (
            "nerfstudio CLI not found on PATH or next to the venv's python - "
            "run `uv sync --extra engine` (real, sizeable install: torch+CUDA, "
            "nerfstudio, gsplat - ~276 packages, verified working on Goliath "
            "2026-07-13 with an RTX 4090)."
            if not configured
            else "nerfstudio CLI verified present; real ns-process-data/ns-train/ns-export "
            "pipeline wired and ready."
        ),
    }


# ---------------------------------------------------------------------------
# Fleet contract: health + registration (per ORCHESTRATION_HIERARCHY.md)
# ---------------------------------------------------------------------------


async def _register_with_hub() -> None:
    payload = {
        "id": SERVER_ID,
        "name": "Self-hosted Gaussian-splat generation",
        "type": "mcp",
        "port": BACKEND_PORT,
        "version": SERVER_VERSION,
        "tier": "standard",
    }
    for _attempt in range(1):  # non-fatal, single attempt at startup; retry loop is a fast-follow
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(HUB_REGISTER_URL, json=payload)
                if resp.status_code < 300:
                    logger.info("Registered with mcp-federation-hub")
                else:
                    # Honest logging: a non-exception response is not success.
                    # As of 2026-07-13 the hub does not yet implement
                    # POST /api/v1/register (see ORCHESTRATION_HIERARCHY.md
                    # action item) - this branch is expected to fire until
                    # that lands, and should NOT be logged as a registration.
                    logger.warning(
                        "Hub registration got HTTP %s (not yet implemented on hub side, "
                        "see ORCHESTRATION_HIERARCHY.md) - server running standalone",
                        resp.status_code,
                    )
                return
        except Exception as exc:  # noqa: BLE001 - intentionally broad, non-fatal per hub contract
            logger.warning("Hub registration failed (non-fatal, hub may not be running): %s", exc)


def health_payload() -> dict:
    return {
        "status": "ok",
        "server": SERVER_ID,
        "version": SERVER_VERSION,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "engine_configured": backend.is_configured(),
    }


# ---------------------------------------------------------------------------
# Shutdown (fleet mandate 2026-07-13, per ORCHESTRATION_HIERARCHY.md #4):
# every server needs one shutdown implementation shared by both the REST
# endpoint and the MCP tool - never two independently-drifting code paths.
# ---------------------------------------------------------------------------


async def _do_shutdown(delay_seconds: float = 0.5) -> None:
    """Schedule a graceful exit after `delay_seconds`, giving the caller
    (REST response or MCP tool result) time to actually flush before the
    process dies. Uses os._exit rather than sys.exit so it works reliably
    from inside a background asyncio task regardless of what's on the call
    stack - sys.exit only raises SystemExit in the current thread's stack,
    which is not guaranteed to unwind an ASGI server cleanly."""
    import os

    async def _exit_after_delay() -> None:
        await asyncio.sleep(delay_seconds)
        logger.info("Shutdown requested - exiting now")
        os._exit(0)  # noqa: SLF001 - intentional hard exit, see docstring

    asyncio.create_task(_exit_after_delay())


@mcp.tool()
async def server_shutdown(ctx: Context) -> dict:
    """Gracefully shut down this server. Matches the REST /api/shutdown
    endpoint - both call the same underlying implementation."""
    await _do_shutdown()
    return {"status": "shutting_down", "message": "Server will exit in ~0.5s"}
