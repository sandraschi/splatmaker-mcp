"""splatmaker-mcp - self-hosted Gaussian-splat generation via Nerfstudio/Splatfacto.

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
import json as _json
import logging
import shutil
import sqlite3 as _sqlite
import subprocess
import sys
import tempfile as _tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

import httpx
from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from fastmcp.tools.tool import ToolAnnotations  # type: ignore[reportMissingImports]

logger = logging.getLogger("splatmaker_mcp")

# In-memory log ring (backs GET /api/logs for the webapp Logs page).
_LOG_RING: deque[str] = deque(maxlen=500)


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_RING.append(self.format(record))
        except Exception:
            pass


_ring_handler = _RingHandler()
_ring_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.getLogger().addHandler(_ring_handler)


def _error_response(message: str, error: str | None = None) -> dict:
    """Shared error shape with auto-logging (TOOL_DESIGN_STANDARDS.md §7.1 Pattern 3).

    Always logs the traceback via logger.exception so the failure is visible
    in server logs, and returns the fleet dialogic shape (success + message,
    error key kept for backward compatibility).
    """
    logger.exception("splatmaker error: %s", message)
    return {"success": False, "error": error or message, "message": message}


SERVER_ID = "splatmaker-mcp"
SERVER_VERSION = "0.2.0"
BACKEND_PORT = 11091
FRONTEND_PORT = 11092
HUB_REGISTER_URL = "http://localhost:10857/api/v1/register"
DEPOT_DIR = Path.home() / ".splatmaker-mcp" / "depot"

mcp = FastMCP(SERVER_ID)

_start_time = time.monotonic()


# ---------------------------------------------------------------------------
# Engine abstraction - pluggable, honestly not-yet-wired (see module docstring)
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

        exe_process = self._resolve_exe("ns-process-data")
        exe_train = self._resolve_exe("ns-train")
        exe_export = self._resolve_exe("ns-export")
        if not (exe_process and exe_train and exe_export):
            return EngineResult(
                ok=False,
                message="ns-process-data/ns-train/ns-export not all found on PATH",
            )

        # Stage 1: ns-process-data {images|video} --data <in> --output-dir <out>
        rc, _out, err = await self._run(
            [
                exe_process,
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
                exe_train,
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
                exe_export,
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
        # ns-process-data images wants a directory, not a file list
        if not image_paths:
            return EngineResult(ok=False, message="image_paths is empty")
        parents = {str(Path(p).parent) for p in image_paths}
        if len(parents) == 1:
            return await self._pipeline("images", next(iter(parents)), job_id)
        # Fast win 2026-09-01: mixed-source staging — copy scattered images into a temp dir
        staging = Path(_tempfile.mkdtemp(prefix=f"splatmaker-{job_id}-"))
        try:
            for src in image_paths:
                src_p = Path(src)
                if not src_p.exists():
                    return EngineResult(ok=False, message=f"image not found: {src}")
                shutil.copy2(src_p, staging / src_p.name)
            logger.info("staged %d images from %s into %s", len(image_paths), parents, staging)
            return await self._pipeline("images", str(staging), job_id)
        except Exception as exc:
            return EngineResult(ok=False, message=f"staging failed: {exc}")


backend = SplatBackend(
    engine=SplatEngine.NERFSTUDIO
)  # decided 2026-07-13; is_configured() checks the real CLI is present


# ---------------------------------------------------------------------------
# Engine truth - exe-present is NOT sufficient (2026-11-01: ns-train.exe
# existed while the CLI crashed on missing modules, so
# is_configured() reported a broken engine as ready). The fast exe check
# stays for liveness; this cached `--help` probe is the truth. Three
# states: pending (probe running) / ok / broken|missing. Never blocks -
# callers get the current state immediately and the daemon thread fills it in.
# ---------------------------------------------------------------------------

_ENGINE_STATE: dict = {"status": "pending", "version": "", "error": ""}
_ENGINE_CHECK_STARTED = False
_ENGINE_LOCK = threading.Lock()


def _engine_check_worker() -> None:
    # NOTE: ns-train has NO --version flag (it exits 2 with usage text).
    # Proof of life is `--help` (exit 0); the version comes from the installed
    # distribution metadata (fast, no heavy import).
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _dist_version

        try:
            ns_version = _dist_version("nerfstudio")
        except PackageNotFoundError:
            ns_version = ""
    except Exception:
        ns_version = ""
    exe = SplatBackend._resolve_exe("ns-train")
    if not exe:
        with _ENGINE_LOCK:
            _ENGINE_STATE.update(status="missing", error="ns-train not found on PATH")
        return
    try:
        proc = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=180)
        lines = (proc.stdout + proc.stderr).strip().splitlines()
        with _ENGINE_LOCK:
            if proc.returncode == 0:
                _ENGINE_STATE.update(status="ok", version=ns_version, error="")
            else:
                _ENGINE_STATE.update(
                    status="broken",
                    version=ns_version,
                    error=f"ns-train --help exit {proc.returncode}: {(lines[-1] if lines else '')[:300]}",
                )
    except Exception as exc:
        with _ENGINE_LOCK:
            _ENGINE_STATE.update(status="broken", version=ns_version, error=str(exc)[:300])


def ensure_engine_check() -> dict:
    """Start the one-shot background `--version` probe if never started.

    Always returns the current state immediately (never blocks).
    """
    global _ENGINE_CHECK_STARTED
    with _ENGINE_LOCK:
        if not _ENGINE_CHECK_STARTED and _ENGINE_STATE["status"] == "pending":
            _ENGINE_CHECK_STARTED = True
            threading.Thread(target=_engine_check_worker, daemon=True).start()
        return dict(_ENGINE_STATE)


# ---------------------------------------------------------------------------
# Job tracking — SQLite-backed (fast win 2026-09-01), in-memory dict is cache
# ---------------------------------------------------------------------------


def _resolve_db_path() -> Path:
    """Job store location — honors SPLATMAKER_JOBS_DB so tests can isolate
    to a tmp file instead of writing the real ~/.splatmaker-mcp/jobs.db
    (M36: pytest previously polluted the real store with failed test rows)."""
    import os

    override = os.environ.get("SPLATMAKER_JOBS_DB")
    if override:
        return Path(override)
    return Path.home() / ".splatmaker-mcp" / "jobs.db"


_DB_PATH = _resolve_db_path()
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _db() -> _sqlite.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = _sqlite.connect(str(_DB_PATH))
    con.execute(
        "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, kind TEXT, status TEXT, created_at REAL, message TEXT, asset_paths TEXT)"
    )
    return con


def _load_jobs() -> dict[str, Job]:
    try:
        con = _db()
        rows = con.execute(
            "SELECT id, kind, status, created_at, message, asset_paths FROM jobs"
        ).fetchall()
        con.close()
        out: dict[str, Job] = {}
        for jid, kind, status, created_at, message, asset_json in rows:
            try:
                ap = _json.loads(asset_json) if asset_json else {}
            except Exception:
                ap = {}
            out[jid] = Job(
                id=jid,
                kind=kind,
                status=status,
                created_at=created_at,
                message=message or "",
                asset_paths=ap,
            )
        if out:
            logger.info("loaded %d jobs from %s", len(out), _DB_PATH)
        return out
    except Exception:
        logger.exception("job load failed")
        return {}


def _save_job(job: Job) -> None:
    try:
        con = _db()
        con.execute(
            "INSERT OR REPLACE INTO jobs (id, kind, status, created_at, message, asset_paths) VALUES (?,?,?,?,?,?)",
            (
                job.id,
                job.kind,
                job.status,
                job.created_at,
                job.message,
                _json.dumps(job.asset_paths),
            ),
        )
        con.commit()
        con.close()
    except Exception:
        logger.exception("job save failed for %s", job.id)


@dataclass
class Job:
    id: str
    kind: Literal["from_video", "from_images"]
    status: Literal["queued", "running", "done", "failed"]
    created_at: float
    message: str = ""
    asset_paths: dict[str, str] = field(default_factory=dict)


_jobs: dict[str, Job] = _load_jobs()


# ---------------------------------------------------------------------------
# MCP tool - portmanteau pattern per fleet TOOL_DESIGN_STANDARDS
# ---------------------------------------------------------------------------


async def _run_job(job: Job, coro) -> None:
    """Background task wrapper - runs a pipeline coroutine without blocking
    the tool call that started it, updates the Job record when done. Real
    training runs take real minutes; a tool call that blocks on that would
    hit most MCP clients' request timeouts long before completion."""
    job.status = "running"
    _save_job(job)
    try:
        result = await coro
        job.status = "done" if result.ok else "failed"
        job.message = result.message
        job.asset_paths = result.asset_paths
        _save_job(job)
    except Exception as exc:  # noqa: BLE001 - job-level catch-all, must not crash the server
        job.status = "failed"
        job.message = f"unhandled exception: {exc}"
        logger.exception("splatmaker job %s crashed", job.id)
        _save_job(job)


@mcp.tool(
    output_schema={"type": "object"},
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def splat_generate(
    ctx: Context,
    operation: Literal["from_video", "from_images", "status", "list", "get_asset"],
    video_path: str | None = None,
    image_paths: list[str] | None = None,
    job_id: str | None = None,
) -> dict:
    """Generate or inspect a Gaussian-splat world from local media.

    Operations:
        from_video    - start a job from a video file (video_path required)
        from_images   - start a job from a set of images (image_paths required)
        status        - check a job's status (job_id required)
        list          - list all known jobs
        get_asset     - return asset paths for a completed job (job_id required)

    from_video/from_images return IMMEDIATELY with status="running" - the
    real ns-process-data -> ns-train -> ns-export pipeline runs as a
    background task (real training takes real minutes, not seconds). Poll
    with operation="status" until status is "done" or "failed".

    ## Return Format
    Always a dict with a `success` bool and a human-readable `message`.
    Success paths also carry the documented payload keys (`job_id`, `status`,
    `jobs`, `asset_paths`). Error paths carry `success: False` plus an `error`
    key with the machine-readable reason; the `error` key is kept for backward
    compatibility with existing clients.

    ## Examples
    `splat_generate(operation="from_video", video_path="D:/cap/walk.mp4")`
    -> `{"success": True, "job_id": "...", "status": "queued", "message": ...}`
    `splat_generate(operation="status", job_id="<id>")`
    -> `{"success": True, "job_id": "<id>", "status": "running", "message": ...}`
    `splat_generate(operation="list")` -> `{"success": True, "jobs": [...], ...}`
    """
    if operation == "from_video":
        if not video_path:
            return {
                "success": False,
                "error": "video_path is required for operation=from_video",
                "message": "video_path is required for operation=from_video",
            }
        jid = str(uuid.uuid4())
        job = Job(id=jid, kind="from_video", status="queued", created_at=time.time())
        _jobs[jid] = job
        _save_job(job)
        asyncio.create_task(_run_job(job, backend.generate_from_video(video_path, jid)))
        return {
            "success": True,
            "job_id": jid,
            "status": job.status,
            "message": "pipeline started in background, poll with status",
        }

    if operation == "from_images":
        if not image_paths:
            return {
                "success": False,
                "error": "image_paths is required for operation=from_images",
                "message": "image_paths is required for operation=from_images",
            }
        jid = str(uuid.uuid4())
        job = Job(id=jid, kind="from_images", status="queued", created_at=time.time())
        _jobs[jid] = job
        _save_job(job)
        asyncio.create_task(_run_job(job, backend.generate_from_images(image_paths, jid)))
        return {
            "success": True,
            "job_id": jid,
            "status": job.status,
            "message": "pipeline started in background, poll with status",
        }

    if operation == "status":
        if not job_id or job_id not in _jobs:
            return {
                "success": False,
                "error": f"unknown job_id: {job_id!r}",
                "message": f"unknown job_id: {job_id!r}",
            }
        j = _jobs[job_id]
        return {"success": True, "job_id": j.id, "status": j.status, "message": j.message}

    if operation == "list":
        jobs = [{"job_id": j.id, "status": j.status, "kind": j.kind} for j in _jobs.values()]
        return {
            "success": True,
            "jobs": jobs,
            "message": f"{len(jobs)} job(s) tracked",
        }

    if operation == "get_asset":
        if not job_id or job_id not in _jobs:
            return {
                "success": False,
                "error": f"unknown job_id: {job_id!r}",
                "message": f"unknown job_id: {job_id!r}",
            }
        j = _jobs[job_id]
        if j.status != "done":
            return {
                "success": False,
                "error": f"job {job_id} is not done (status={j.status})",
                "message": f"job {job_id} is not done (status={j.status})",
            }
        return {"success": True, "job_id": j.id, "asset_paths": j.asset_paths, "message": "done"}

    return {
        "success": False,
        "error": f"unknown operation: {operation!r}",
        "message": f"unknown operation: {operation!r}",
    }


@mcp.tool(
    output_schema={"type": "object"},
    annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False),
)
async def splat_engine_status(ctx: Context) -> dict:
    """Report which splat engine is configured and whether the real CLI
    tools are actually present (requires `uv sync --extra engine`).

    ## Return Format
    `{"success": True, "engine": str, "configured": bool,
    "max_iterations": int, "note": str, "message": str,
    "verified": "pending"|"ok"|"broken"|"missing",
    "engine_version": str, "engine_error": str}` — `message` mirrors
    `note` so fleet tooling can render the result without special-casing it.
    `configured` is the fast exe check; `verified` is the cached
    `ns-train --help` truth (pending until the background probe lands).

    ## Examples
    `splat_engine_status()` -> `{"success": True, "engine": "nerfstudio",
    "configured": True, "max_iterations": 15000, "note": ..., "message": ...}`
    """
    configured = backend.is_configured()
    state = ensure_engine_check()
    note = (
        "nerfstudio CLI not found on PATH or next to the venv's python - "
        "run `uv sync --extra engine` (real, sizeable install: torch+CUDA, "
        "nerfstudio, and gsplat - ~276 packages, verified working on Goliath "
        "2026-07-13 with an RTX 4090)."
        if not configured
        else "nerfstudio CLI verified present; real ns-process-data/ns-train/ns-export "
        "pipeline wired and ready."
    )
    return {
        "success": True,
        "engine": backend.engine.value,
        "configured": configured,
        "verified": state["status"],
        "engine_version": state["version"],
        "engine_error": state["error"],
        "max_iterations": backend.max_iterations,
        "note": note,
        "message": note,
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
        except Exception:  # noqa: BLE001 - intentionally broad, non-fatal per hub contract
            logger.exception("Hub registration failed (non-fatal, hub may not be running)")


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


@mcp.tool(
    output_schema={"type": "object"},
    annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False
    ),
)
async def server_shutdown(ctx: Context) -> dict:
    """Gracefully shut down this server. Matches the REST /api/shutdown
    endpoint - both call the same underlying implementation.

    ## Return Format
    `{"success": True, "status": "shutting_down", "message": str}`.

    ## Examples
    `server_shutdown()` -> `{"success": True, "status": "shutting_down",
    "message": "Server will exit in ~0.5s"}`
    """
    await _do_shutdown()
    return {"success": True, "status": "shutting_down", "message": "Server will exit in ~0.5s"}


@mcp.tool(
    app=True,
    output_schema={"type": "object"},
    annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False),
)
async def show_status_card(ctx: Context) -> ToolResult:
    """Show splatmaker engine + job-queue status as a rich Prefab card.

    ## Return Format
    A `ToolResult` with plain-text `content` (same numbers as the card) and
    `structured_content` carrying the `PrefabApp` view for Prefab-capable hosts.

    ## Examples
    `show_status_card()` -> card with engine state, job counts by status, backend port.
    """
    from prefab_ui.app import PrefabApp
    from prefab_ui.components import (
        Card,
        CardContent,
        Column,
        Grid,
        Heading,
        Muted,
        Separator,
    )

    h = health_payload()
    state = ensure_engine_check()
    by_status = {
        s: sum(1 for j in _jobs.values() if j.status == s)
        for s in ("queued", "running", "done", "failed")
    }
    with Column(gap=4, css_class="p-4") as view:
        Heading("Splatmaker - Engine + Job Queue")
        Separator()
        with Grid(columns=3, gap=3):
            for label, value in [
                ("Engine", backend.engine.value),
                (
                    "Engine ready",
                    "yes" if h["engine_configured"] else "no (uv sync --extra engine)",
                ),
                ("Jobs tracked", str(len(_jobs))),
                ("Queued", str(by_status["queued"])),
                ("Running", str(by_status["running"])),
                ("Done / failed", f"{by_status['done']} / {by_status['failed']}"),
            ]:
                with Card(), CardContent(css_class="pt-4"):
                    Muted(label)
                    Heading(value)

    text = (
        f"Splatmaker status: engine={backend.engine.value} "
        f"(configured={h['engine_configured']}, verified={state['status']}"
        + (f" {state['version']}" if state["version"] else "")
        + (f" - {state['error']}" if state["error"] else "")
        + f"), jobs={len(_jobs)} "
        f"(queued={by_status['queued']}, running={by_status['running']}, "
        f"done={by_status['done']}, failed={by_status['failed']})."
    )
    return ToolResult(
        content=text,
        structured_content=PrefabApp(view=view, title="Splatmaker Status"),
    )


SPLAT_WORKFLOW_TEXT = (
    "Splatmaker workflow: (1) capture - one folder of sharp, overlapping phone "
    "photos (or a slow walk-around video); (2) generate - call splat_generate "
    "from_video/from_images, it returns immediately with a job_id; (3) poll - "
    "splat_generate status until done (real training takes minutes); (4) fetch - "
    "get_asset for the .ply path; (5) collide - route the .ply through "
    "blender-mcp blender_splatting for a collision mesh before any VR use "
    "(this server never emits a collider)."
)


@mcp.prompt()
def splat_workflow() -> str:
    """Guided prompt: capture -> generate -> poll -> collider mesh.

    ## Return Format
    A plain-text workflow briefing the caller pastes into the session.

    ## Examples
    `splat_workflow` -> multi-step instructions for a from_video job.
    """
    return SPLAT_WORKFLOW_TEXT


@mcp.resource("splatmaker://jobs")
def jobs_resource() -> str:
    """Live job ledger (same rows as GET /api/jobs).

    ## Return Format
    JSON array of {job_id, kind, status, created_at, message}.

    ## Examples
    Read `splatmaker://jobs` -> current ledger without calling list.
    """
    return _json.dumps(
        [
            {
                "job_id": j.id,
                "kind": j.kind,
                "status": j.status,
                "created_at": j.created_at,
                "message": j.message,
            }
            for j in _jobs.values()
        ]
    )
