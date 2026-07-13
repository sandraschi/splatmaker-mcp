"""Smoke tests — real assertions, not placeholders. Honesty-standard-compliant:
these test what actually works (schema, job tracking, honest not_implemented
responses), not a fake success path for the unwired engine."""

import pytest

from splatmaker_mcp.server import backend, health_payload, splat_engine_status, splat_generate


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
