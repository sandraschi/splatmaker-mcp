# justfile - splatmaker-mcp task runner

default:
    @just --list

sync:
    uv sync

test:
    uv run pytest -v

run-stdio:
    uv run splatmaker-mcp

run-http:
    uv run splatmaker-mcp --http --port 11091

lint:
    uv run ruff check src tests

fmt:
    uv run ruff format src tests

health:
    curl http://localhost:11091/api/health
