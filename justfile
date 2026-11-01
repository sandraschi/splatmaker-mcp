set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# justfile - splatmaker-mcp task runner

default:
    @just --list

sync:
    uv sync --extra dev

# Engine sync - the ONLY correct way to (re)install the nerfstudio engine.
# Plain `just sync` / `uv sync` PRUNES engine packages (uv removes extras not
# in the target set). Always run this after any plain sync. Verifies with
# ns-train --help (exit 0). See docs/CONFIGURATION.md.
sync-engine:
    uv sync --extra engine
    uv run --extra engine ns-train --help

test:
    uv run --extra dev pytest -v

run-stdio:
    uv run splatmaker-mcp

run-http:
    uv run splatmaker-mcp --http --port 11091

# Fleet serve: run the HTTP backend (what start.ps1 launches)
serve:
    uv run splatmaker-mcp --http --port 11091

lint:
    uv run --extra dev ruff check src tests

fmt:
    uv run --extra dev ruff format src tests

health:
    curl http://localhost:11091/api/health

# Bootstrap: install dev deps + pre-commit hook + webapp deps
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green
    Push-Location webapp; bun install --frozen-lockfile; Pop-Location

# Gates: full local gate set (ruff + format check + pytest with coverage + tsc + biome)
gates:
    uv run --no-sync --extra dev ruff check src tests
    uv run --no-sync --extra dev ruff format src tests --check
    uv run --no-sync --extra dev pyright src/
    uv run --no-sync --extra dev pytest tests/ -q
    bun x tsc --noEmit -p webapp
    bun run --cwd webapp biome:ci
    bun run --cwd webapp build
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{{justfile_directory()}}\\scripts\\gate-web-css.ps1"

# Native shell build (Tauri NSIS) — delegates to src-tauri/build.ps1
build-native:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{{justfile_directory()}}\\src-tauri\\build.ps1"

# MCPB packaging — validates 3-4-100 prompts, fresh-copies src/ -> mcpb/src/,
# packs via the fleet pipeline (scripts/mcpb-pack.ps1 shim).
mcpb-pack:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{{justfile_directory()}}\\scripts\\mcpb-pack.ps1"
# Fleet depot advertise
advertise:
    powershell.exe -NoProfile -File "D:\Dev\repos\mcp-central-docs\scripts\advertise-depot.ps1" -DepotMcpUrl "http://127.0.0.1:10727"
