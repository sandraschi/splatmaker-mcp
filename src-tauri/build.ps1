$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== ${RepoName} Tauri Release Build ===" -ForegroundColor Cyan

# Step 0: Verify prod API contract BEFORE building (dev Vite proxy masks these;
# dist/ has no proxy, so a wrong port here means "Failed to fetch" in NSIS).
Write-Host "-> [0/5] API contract check (operator port 11259)..." -ForegroundColor Yellow
$apiFile = Join-Path $Root "webapp\src\lib\api.ts"
$apiContent = Get-Content $apiFile -Raw
if ($apiContent -match '127\.0\.0\.1:(\d+)') {
    $apiPort = [int]$Matches[1]
    if ($apiPort -ne 11259) {
        throw "API_BASE in webapp/src/lib/api.ts points at port $apiPort, but the operator backend serves on 11259 (side-by-side rule: never the dev port 11091). Fix before building."
    }
    Write-Host "  API_BASE port: $apiPort (operator backend) OK" -ForegroundColor Green
} else {
    throw "API_BASE absolute backend URL not found in webapp/src/lib/api.ts - Tauri WebView has no Vite proxy."
}
$tauriConf = Get-Content "$PSScriptRoot\tauri.conf.json" -Raw
if ($tauriConf -notmatch 'http://127\.0\.0\.1:11259') {
    throw "tauri.conf.json CSP connect-src does not include http://127.0.0.1:11259."
}
Write-Host "  CSP connect-src includes operator port OK" -ForegroundColor Green

# Step 1: TypeScript lint gate + frontend build
$frontendDirs = @("web_sota", "webapp/frontend", "webapp")
foreach ($dir in $frontendDirs) {
    $frontend = Join-Path $Root $dir
    if (Test-Path "$frontend\package.json") {
        Write-Host "-> [1/5] Building frontend ($dir)..." -ForegroundColor Yellow
        Push-Location $frontend
        # bun-first repo: frozen lockfile install (npm would create a parallel tree)
        & "$env:USERPROFILE\.bun\bin\bun.exe" install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw "Frontend bun install failed" }

        Write-Host "  tsc --noEmit..." -ForegroundColor Gray
        $tscOut = & "$env:USERPROFILE\.bun\bin\bun.exe" x tsc --noEmit 2>&1
        $tscExit = $LASTEXITCODE
        if ($tscExit -ne 0) {
            Write-Host "  TypeScript compilation FAILED - fix errors before building NSIS" -ForegroundColor Red
            Write-Host $tscOut
            throw "TypeScript compilation failed - fix all errors before building NSIS installer"
        }

        & "$env:USERPROFILE\.bun\bin\bun.exe" run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

        # CSS gate: an unstyled dist is a failed build, not a shippable one
        # (2026-11-01: missing postcss.config shipped a 57-byte stylesheet).
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$Root\scripts\gate-web-css.ps1"
        if ($LASTEXITCODE -ne 0) { throw "CSS gate failed - Tailwind did not compile" }
        Pop-Location
        break
    }
}

# Step 2: PyInstaller backend (onefile)
Write-Host "-> [2/5] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\${RepoName}-backend.spec"
if (Test-Path $specFile) {
    Push-Location $Root
    # Patch fastmcp to not crash on missing metadata (dist-info stripped below)
    $fm = "$Root\.venv\Lib\site-packages\fastmcp\__init__.py"
    if (Test-Path $fm) {
        $c = Get-Content $fm -Raw
        if ($c -match 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)') {
            $c = $c -replace 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)', 'except PackageNotFoundError:
    try:
        __version__ = _version("fastmcp")
    except PackageNotFoundError:
        __version__ = "0.0.0"'
            Set-Content $fm -Value $c -Encoding utf8
            Write-Host "  Patched fastmcp metadata fallback" -ForegroundColor Yellow
        }
    }
    # PyInstaller MUST run from the project venv, not `uv run pyinstaller` --
    # that resolves to the isolated global uv-tool environment (no project
    # packages visible there), so copy_metadata("fastmcp") in the spec file
    # silently fails and the frozen exe crashes with PackageNotFoundError at
    # import time. See TAURI_PRODUCTION_PITFALLS.md sec 13 #12-13.
    $pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
    if (-not (Test-Path $pyiExe)) {
        Write-Host "  pyinstaller missing from project venv - adding as dev dependency" -ForegroundColor Yellow
        Push-Location $Root
        uv add --dev pyinstaller pefile altgraph
        uv sync
        Pop-Location
    }
    Remove-Item "$Root\dist\${RepoName}-backend.exe" -Force -ErrorAction SilentlyContinue
    & $pyiExe "$specFile" --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

    # Gate 1: size gate - a onefile backend under 5 MB is a runt/empty binary.
    $frozenExe = "$Root\dist\${RepoName}-backend.exe"
    $sizeMB = (Get-Item $frozenExe).Length / 1MB
    if ($sizeMB -lt 5) {
        throw "Backend exe is only $([math]::Round($sizeMB, 1)) MB - PyInstaller produced an empty/broken binary. Check build\${RepoName}-backend\warn-*.txt for hidden-import misses."
    }
    Write-Host "  Frozen backend size: $([math]::Round($sizeMB, 1)) MB" -ForegroundColor Green

    # Gate 2: smoke-test the frozen binary on an ephemeral port (catches ALL
    # import crashes generically - a traceback here is a broken bundle).
    Write-Host "  Smoke-testing frozen backend..." -ForegroundColor Yellow
    $testPort = 11999
    # 5.1-compatible env passing (Start-Process -Environment is PS7+ only):
    # set process env, the child inherits it, then restore.
    $oldPort = $env:MCP_PORT; $oldHost = $env:MCP_HOST
    $env:MCP_PORT = "$testPort"; $env:MCP_HOST = "127.0.0.1"
    $testProc = Start-Process -FilePath $frozenExe -NoNewWindow -PassThru `
        -RedirectStandardError "$Root\dist\pyi-crash.log"
    if ($null -eq $oldPort) { Remove-Item Env:\MCP_PORT -ErrorAction SilentlyContinue } else { $env:MCP_PORT = $oldPort }
    if ($null -eq $oldHost) { Remove-Item Env:\MCP_HOST -ErrorAction SilentlyContinue } else { $env:MCP_HOST = $oldHost }
    $up = $false
    for ($i = 0; $i -lt 24; $i++) {
        Start-Sleep -Seconds 5
        if ($testProc.HasExited) { break }
        $tcp = New-Object System.Net.Sockets.TcpClient
        try {
            $tcp.Connect("127.0.0.1", $testPort)
            $tcp.Close()
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$testPort/api/health" -TimeoutSec 10
            if ($health.status -eq "ok") { $up = $true; break }
        } catch { } finally { $tcp.Dispose() }
    }
    if ($testProc.HasExited) {
        $crash = Get-Content "$Root\dist\pyi-crash.log" -Raw -ErrorAction SilentlyContinue
        throw "Frozen backend crashed on launch (exit $($testProc.ExitCode)):`n$crash"
    }
    if (-not $up) {
        $testProc.Kill()
        throw "Frozen backend never served /api/health on ${testPort} within 120s."
    }
    Write-Host "  Frozen backend smoke test PASSED (/api/health ok)" -ForegroundColor Green
    $testProc.Kill(); $testProc.Dispose()
    Remove-Item "$Root\dist\pyi-crash.log" -Force -ErrorAction SilentlyContinue
    Pop-Location
} else {
    throw "Backend spec file not found at $specFile - create ${RepoName}-backend.spec before building NSIS installer. Without it, PyInstaller cannot produce the backend binary."
}

# Step 3: Embed in Tauri resources (+ dev fallback)
Write-Host "-> [3/5] Embedding backend..." -ForegroundColor Yellow
$src = "$Root\dist\${RepoName}-backend.exe"
if (-not (Test-Path $src)) { throw "Backend exe not found at $src - PyInstaller step failed" }
Copy-Item $src "$ResourceDir\${RepoName}-backend.exe" -Force
Copy-Item $src "$DevDir\${RepoName}-backend-$Triple.exe" -Force
Write-Host "  Backend exe: $((Get-Item $src).Length / 1MB) MB" -ForegroundColor Green

# Bundle .env.example (NOT .env - the dev .env holds personal keys) plus the
# vendored MCP-client registration script the NSIS hook calls.
$envExample = "$Root\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$ResourceDir\.env.example" -Force
    Write-Host "  Bundled .env.example" -ForegroundColor Green
} else {
    Write-Host "  WARNING: .env.example not found at repo root" -ForegroundColor DarkYellow
}
$mcpClients = "$Root\scripts\install-mcp-clients.ps1"
if (Test-Path $mcpClients) {
    Copy-Item $mcpClients "$ResourceDir\install-mcp-clients.ps1" -Force
    Write-Host "  Bundled install-mcp-clients.ps1" -ForegroundColor Green
} else {
    Write-Host "  WARNING: scripts/install-mcp-clients.ps1 missing - hook will skip registration" -ForegroundColor DarkYellow
}

# Step 4: Single NSIS installer
Write-Host "-> [4/5] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
# MSVC link.exe must be on PATH for the Rust linker - import the VS env
# (tauri build fails with "linker `link.exe` not found" without this).
$vcvars = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) {
    $vcvars = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
}
if (Test-Path $vcvars) {
    cmd /c "`"$vcvars`" > nul & set" | Where-Object { $_ -match '^(INCLUDE|LIB|LIBPATH|Path|VCToolsVersion|WindowsSdkDir|UniversalCRTSdkDir|UCRTVersion)=' } | ForEach-Object {
        $parts = $_.Split('=', 2)
        Set-Item -Path "env:$($parts[0])" -Value $parts[1]
    }
    Write-Host "  MSVC env imported" -ForegroundColor Gray
} else {
    Write-Host "  WARNING: vcvars64.bat not found - link.exe may be missing" -ForegroundColor DarkYellow
}
npx @tauri-apps/cli build --bundles nsis
if ($LASTEXITCODE -ne 0) { throw "Tauri build failed with exit code $LASTEXITCODE" }
Pop-Location

# Step 5: cleanup + stage (a stale shadow backend.exe beside the Tauri exe
# resolves first and masks the real resource - checklist H.2)
Write-Host "-> [5/5] Cleanup + stage..." -ForegroundColor Yellow
Remove-Item -Force "$PSScriptRoot\target\release\${RepoName}-backend.exe" -ErrorAction SilentlyContinue

# Stage to repo dist/
$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$nsisDir = "$PSScriptRoot\target\release\bundle\nsis"
if (Test-Path $nsisDir) { Copy-Item "$nsisDir\*-setup.exe" "$distDir\" -Force }

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Ship: $nsisDir\*.exe"
