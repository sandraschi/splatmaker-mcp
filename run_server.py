"""PyInstaller entrypoint for splatmaker-mcp HTTP sidecar."""

from __future__ import annotations

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).resolve().parent
if str(base / "src") not in sys.path:
    sys.path.insert(0, str(base / "src"))

os.environ.setdefault("MCP_TRANSPORT", "http")

if __name__ == "__main__":
    from splatmaker_mcp.__main__ import build_http_app

    app = build_http_app()

    host = os.environ.get("SPLATMAKER_HOST", "127.0.0.1")
    port = int(os.environ.get("SPLATMAKER_PORT", os.environ.get("MCP_PORT", "11091")))
    log_level = os.environ.get("SPLATMAKER_LOG_LEVEL", "info")
    uvicorn.run(app, host=host, port=port, log_level=log_level)
