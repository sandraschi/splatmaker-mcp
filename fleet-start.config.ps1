# Per-repo fleet start config for splatmaker-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'splatmaker-mcp'
    BackendPort  = 11091
    FrontendPort = 11092
    HealthPath   = '/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind = 'none'
    }
    Frontend = @{
        Kind = 'none'
    }
}
