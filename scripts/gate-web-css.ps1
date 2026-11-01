# CSS gate: Tailwind must actually compile. A missing postcss.config.js or a
# broken tailwind.config.js makes `vite build` succeed with a ~50-byte empty
# stylesheet and the webapp renders as plain unstyled HTML. This gate fails
# the build loudly instead (incident 2026-11-01: 57-byte CSS shipped).
$ErrorActionPreference = "Stop"

$css = Get-ChildItem "$PSScriptRoot/../webapp/dist/assets/*.css" -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending | Select-Object -First 1
if (-not $css) {
    throw "CSS gate failed: no stylesheet in webapp/dist/assets - did the frontend build run?"
}
if ($css.Length -lt 5120) {
    throw "CSS gate failed: $($css.Name) is $($css.Length) bytes (< 5kB) - Tailwind did not compile. Check webapp/postcss.config.js and webapp/tailwind.config.js."
}
$raw = Get-Content $css.FullName -Raw
if ($raw -match "@tailwind") {
    throw "CSS gate failed: raw @tailwind directives in built CSS - PostCSS did not process webapp/src/index.css."
}
Write-Host "CSS gate passed: $($css.Name) $($css.Length) bytes, no raw directives." -ForegroundColor Green
