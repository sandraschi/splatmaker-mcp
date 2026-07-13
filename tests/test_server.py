"""Smoke tests — real assertions, not placeholders. Honesty-standard-compliant:
these test what actually works (schema, job tracking, honest not_implemented
responses), not a fake success path for the unwired engine.

SAFETY NOTE: test_server_shutdown_schedules_exit mocks os._exit. Never remove
that mock and call server_shutdown() for real in a test - it calls os._exit(0)
after a short delay, which kills the entire pytest process, not a simulated
server. Verified for real via live PowerShell script instead (see CHANGELOG).
"""

import asyncio
from unittest.mock import patch

import pytest

from splatmaker_mcp.server import backend, health_payload, server_shutdown, splat_engine_status, splat_generate


@pytest.mark.asyncio
async def test_health_payload_shape():
    h = health_payload()
    assert h["server"] == "splatmaker-mcp"
    assert h["status"] == "ok"
    assert "uptime_seconds" in h


@pytest.mark.asyncio
async def test_engine_status_reports_unconfigured_by_default():
    result = await splat_engine_status(ctx=None)
    assert result["configured"] is False
    assert result["engine"] == "unset"


@pytest.mark.asyncio
async def test_generate_from_video_is_honestly_not_implemented():
    result = await splat_generate(ctx=None, operation="from_video", video_path="/tmp/fake.mp4")
    assert result["status"] == "not_implemented"
    assert "job_id" in result


@pytest.mark.asyncio
async def test_generate_from_video_requires_path():
    result = await splat_generate(ctx=None, operation="from_video")
    assert "error" in result


@pytest.mark.asyncio
async def test_status_unknown_job_errors():
    result = await splat_generate(ctx=None, operation="status", job_id="does-not-exist")
    assert "error" in result


@pytest.mark.asyncio
async def test_list_returns_jobs_list():
    result = await splat_generate(ctx=None, operation="list")
    assert "jobs" in result
    assert isinstance(result["jobs"], list)


@pytest.mark.asyncio
async def test_server_shutdown_schedules_exit():
    """Verifies server_shutdown returns the right ack and schedules an exit
    task - WITHOUT ever letting the real os._exit(0) fire (see module
    docstring safety note). Patches os._exit to a no-op tracker instead."""
    with patch("os._exit") as mock_exit:
        result = await server_shutdown(ctx=None)
        assert result["status"] == "shutting_down"
        # give the scheduled background task a moment to run within this
        # test's own event loop, then confirm it WOULD have called os._exit
        await asyncio.sleep(0.6)
        mock_exit.assert_called_once_with(0)
