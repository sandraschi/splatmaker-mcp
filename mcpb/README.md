# splatmaker-mcp (MCPB Bundle)

Self-hosted, zero-marginal-cost Gaussian-splat generation. FOSS alternative
to paid splat APIs - point at a video or images, get a navigable 3D world,
computed on local hardware (Nerfstudio/Splatfacto).

## Usage

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "splatmaker-mcp": {
      "command": "uv",
      "args": ["run", "--project", "<BUNDLE_DIR>", "python", "-m", "splatmaker_mcp"],
      "env": {
        "PYTHONPATH": "<BUNDLE_DIR>/src",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

(replace `<BUNDLE_DIR>` with the unpacked bundle directory)

No API keys. The engine extra (`uv sync --extra engine`) is needed for real
generation; without it the server reports `verified: missing` and explains
the install. Full docs: README.md in the repo.
