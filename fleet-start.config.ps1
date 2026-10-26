# Per-repo fleet start config for splatmaker-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'splatmaker-mcp'
    BackendPort  = 11091
    FrontendPort = 11092
    HealthPath   = '/api/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind    = 'custom'
        Command = "uv run --no-sync --project '$PSScriptRoot' splatmaker-mcp --http --port 11091"
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
    }
}
