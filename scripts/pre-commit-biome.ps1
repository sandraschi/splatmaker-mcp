# Runs Biome check on the webapp (fleet pre-commit Biome hook).
# Exits non-zero with the failing file list so the commit blocks.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$webRoots = @("webapp", "web_sota", "webapp\frontend", "web") | ForEach-Object {
    Join-Path $repoRoot $_
} | Where-Object { Test-Path -LiteralPath $_ }
if ($webRoots.Count -eq 0) { Write-Host "pre-commit-biome: no web root, skipping."; exit 0 }
$bun = Join-Path $env:USERPROFILE ".bun\bin\bun.exe"
if (-not (Test-Path -LiteralPath $bun)) { $bun = "bun" }
foreach ($root in $webRoots) {
    Push-Location $root
    try {
        if (Test-Path -LiteralPath (Join-Path $root "biome.json")) {
            & $bun x @biomejs/biome ci src/
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        } else {
            Write-Host "pre-commit-biome: no biome.json in $root, skipping."
        }
    } finally {
        Pop-Location
    }
}
