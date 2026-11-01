"""Pytest bootstrap — point the job store at a scratch DB BEFORE server import.

server.py resolves _DB_PATH at import time (and _load_jobs() CREATEs the
table on import), so a per-test monkeypatch alone is too late: the real
~/.splatmaker-mcp/jobs.db would already be touched. Setting
SPLATMAKER_JOBS_DB here runs before any test module imports the server.
Per-test tmp isolation lives in test_server._isolated_job_store.
"""

import os
import tempfile
from pathlib import Path

_test_db = Path(tempfile.gettempdir()) / "splatmaker-mcp-test-jobs.db"
os.environ.setdefault("SPLATMAKER_JOBS_DB", str(_test_db))
