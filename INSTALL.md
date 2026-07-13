# INSTALL

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) — `winget install astral-sh.uv` if missing
- Windows: PowerShell 7+ recommended (`start.ps1` works on 5.1 too)

## Naked-PC install

```powershell
git clone https://github.com/sandraschi/splatmaker-mcp.git
cd splatmaker-mcp
uv sync
.\start.ps1
```

`start.ps1` auto-installs `uv` via winget if missing (`Require-Command` pattern, per `NAKED_PC_INSTALL_STANDARD.md`), then starts the HTTP transport on port 11091.

## Claude Desktop / Cursor (stdio)

Add to your MCP client config:

```json
{
  "mcpServers": {
    "splatmaker-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:\\Dev\\repos\\splatmaker-mcp", "splatmaker-mcp"]
    }
  }
}
```

## Verify

```powershell
uv run pytest
```

Should pass 6/6 — all tests are honesty-standard-compliant smoke tests (they verify the schema and the honest `not_implemented` responses, not a fake engine).

## Engine setup (not yet applicable)

No engine is wired yet — see README.md "Engine status". This section will be filled in once one is chosen and implemented.
