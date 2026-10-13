# Per-repo fleet start config for splatmaker-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'splatmaker-mcp'
    BackendPort  = 0
    FrontendPort = 0
    HealthPath   = '/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind = 'none'
    }
    Frontend = @{
        Kind = 'none'
    }
}
