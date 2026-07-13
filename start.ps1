#Requires -Version 5.1
# start.ps1 - splatmaker-mcp backend launcher (naked-PC compliant)
# No em dashes in this file - Unicode Safety standard.

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name, [string]$WingetId)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "[splatmaker-mcp] '$Name' not found - attempting winget install ($WingetId)..." -ForegroundColor Yellow
        try {
            winget install --id $WingetId -e --accept-package-agreements --accept-source-agreements
        } catch {
            Write-Host "[splatmaker-mcp] Could not auto-install $Name. Install it manually and re-run this script." -ForegroundColor Red
            exit 1
        }
    }
}

Require-Command -Name "uv" -WingetId "astral-sh.uv"

Set-Location -Path $PSScriptRoot

Write-Host "[splatmaker-mcp] Syncing dependencies..." -ForegroundColor Cyan
uv sync

Write-Host "[splatmaker-mcp] Starting HTTP transport on port 11091..." -ForegroundColor Green
uv run splatmaker-mcp --http --port 11091
