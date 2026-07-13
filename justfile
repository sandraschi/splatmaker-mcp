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
