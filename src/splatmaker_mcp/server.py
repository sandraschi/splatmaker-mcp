"""splatmaker-mcp — self-hosted FOSS Gaussian-splat generation.

HONESTY NOTE (Implementation Honesty Standard): the underlying splat-generation
ENGINE is not yet chosen (candidates: Postshot CLI, gsplat, Nerfstudio-derived
pipelines — see gestating-chains/medium-chains.md for the tradeoffs). This
scaffold ships a real, working MCP server shell — tool schemas, job tracking,
health/registration, webapp REST surface — with the engine layer as an
explicit pluggable interface that returns `not_implemented` until one is
wired. No tool here claims success it can't deliver.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

import httpx
from fastmcp import Context, FastMCP

logger = logging.getLogger("splatmaker_mcp")

SERVER_ID = "splatmaker-mcp"
SERVER_VERSION = "0.1.0"
BACKEND_PORT = 11091
FRONTEND_PORT = 11092
HUB_REGISTER_URL = "http://localhost:10857/api/v1/register"
DEPOT_DIR = Path.home() / ".splatmaker-mcp" / "depot"

mcp = FastMCP(SERVER_ID)

_start_time = time.monotonic()


# ---------------------------------------------------------------------------
# Engine abstraction — pluggable, honestly not-yet-wired (see module docstring)
# ---------------------------------------------------------------------------

class SplatEngine(str, Enum):
    """Candidate FOSS backends. None are wired yet — see gestating-chains
    medium-chains.md for the comparison this scaffold doesn't prejudge."""

    UNSET = "unset"
    POSTSHOT = "postshot"
    GSPLAT = "gsplat"
    NERFSTUDIO = "nerfstudio"


@dataclass
class EngineResult:
    ok: bool
    message: str
    asset_paths: dict[str, str] = field(default_factory=dict)


class SplatBackend:
    """Real interface, honest implementation. Every method that would touch
    an actual splat engine returns not_implemented=True until §ENGINE_CHOICE
    is resolved and a concrete subprocess/API wrapper is written here."""

    def __init__(self, engine: SplatEngine = SplatEngine.UNSET) -> None:
        self.engine = engine

    def is_configured(self) -> bool:
        return self.engine != SplatEngine.UNSET

    async def generate_from_video(self, video_path: str, job_id: str) -> EngineResult:
        if not self.is_configured():
            return EngineResult(
                ok=False,
                message=(
                    "not_implemented: no splat engine configured. Set SPLATMAKER_ENGINE "
                    "env var to one of: postshot, gsplat, nerfstudio — and implement the "
                    "corresponding subprocess wrapper in engine_<name>.py before this will "
                    "produce a real splat. See README.md 'Engine status'."
                ),
            )
        # Real wiring point for whichever engine gets chosen. Deliberately
        # not stubbed with a fake success path — see Implementation Honesty
        # Standard. Raises NotImplementedError rather than pretending.
        raise NotImplementedError(f"engine '{self.engine}' selected but no wrapper written yet")

    async def generate_from_images(self, image_paths: list[str], job_id: str) -> EngineResult:
        if not self.is_configured():
            return EngineResult(
                ok=False,
                message="not_implemented: no splat engine configured (see generate_from_video).",
            )
        raise NotImplementedError(f"engine '{self.engine}' selected but no wrapper written yet")


backend = SplatBackend()  # engine unset by default — honest starting state


# ---------------------------------------------------------------------------
# Job tracking (in-memory for v1 — SQLite persistence is a fast-follow, not
# a v1 requirement; flagged here rather than silently deferred)
# ---------------------------------------------------------------------------

@dataclass
class Job:
    id: str
    kind: Literal["from_video", "from_images"]
    status: Literal["queued", "running", "done", "failed", "not_implemented"]
    created_at: float
    message: str = ""
    asset_paths: dict[str, str] = field(default_factory=dict)


_jobs: dict[str, Job] = {}


# ---------------------------------------------------------------------------
# MCP tool — portmanteau pattern per fleet TOOL_DESIGN_STANDARDS
# ---------------------------------------------------------------------------

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

    Honesty: from_video/from_images will return status="not_implemented" until
    a splat engine is configured — see module docstring. This is intentional,
    not a bug; the tool schema is real and ready for whichever engine gets wired.
    """
    if operation == "from_video":
        if not video_path:
            return {"error": "video_path is required for operation=from_video"}
        jid = str(uuid.uuid4())
        job = Job(id=jid, kind="from_video", status="queued", created_at=time.time())
        _jobs[jid] = job
        result = await backend.generate_from_video(video_path, jid)
        job.status = "done" if result.ok else "not_implemented"
        job.message = result.message
        job.asset_paths = result.asset_paths
        return {"job_id": jid, "status": job.status, "message": job.message}

    if operation == "from_images":
        if not image_paths:
            return {"error": "image_paths is required for operation=from_images"}
        jid = str(uuid.uuid4())
        job = Job(id=jid, kind="from_images", status="queued", created_at=time.time())
        _jobs[jid] = job
        result = await backend.generate_from_images(image_paths, jid)
        job.status = "done" if result.ok else "not_implemented"
        job.message = result.message
        job.asset_paths = result.asset_paths
        return {"job_id": jid, "status": job.status, "message": job.message}

    if operation == "status":
        if not job_id or job_id not in _jobs:
            return {"error": f"unknown job_id: {job_id!r}"}
        j = _jobs[job_id]
        return {"job_id": j.id, "status": j.status, "message": j.message}

    if operation == "list":
        return {"jobs": [{"job_id": j.id, "status": j.status, "kind": j.kind} for j in _jobs.values()]}

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
    """Report which splat engine (if any) is configured. See README.md
    'Engine status' for the current state — this is the honest single
    source of truth for whether generate operations will actually work."""
    return {
        "engine": backend.engine.value,
        "configured": backend.is_configured(),
        "note": (
            "Engine not yet chosen — see gestating-chains/medium-chains.md "
            "for the Postshot/gsplat/Nerfstudio comparison."
            if not backend.is_configured()
            else "Engine configured but wrapper implementation status not tracked here yet."
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
    for attempt in range(1):  # non-fatal, single attempt at startup; retry loop is a fast-follow
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
