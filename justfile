set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# justfile - splatmaker-mcp task runner

default:
    @just --list

sync:
    uv sync --extra dev

test:
    uv run --extra dev pytest -v

run-stdio:
    uv run splatmaker-mcp

run-http:
    uv run splatmaker-mcp --http --port 11091

lint:
    uv run --extra dev ruff check src tests

fmt:
    uv run --extra dev ruff format src tests

health:
    curl http://localhost:11091/api/health

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green
# Fleet depot advertise
advertise:
    powershell.exe -NoProfile -File "D:\Dev\repos\mcp-central-docs\scripts\advertise-depot.ps1" -DepotMcpUrl "http://127.0.0.1:10727"