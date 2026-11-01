# Detached NSIS build runner: logs internally so no redirect handles are held
# by the parent (harness reaps redirected children). Poll the log; the
# sentinel line "=== NSIS BUILD DONE ===" marks completion.
$log = "C:\Users\sandr\AppData\Local\Temp\opencode\nsis-build.log"
"=== NSIS build started $(Get-Date -Format o) ===" | Out-File -FilePath $log -Encoding utf8
try {
    & "D:\Dev\repos\splatmaker-mcp\src-tauri\build.ps1" 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    "EXIT:$LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
} catch {
    "FATAL: $($_.Exception.Message)" | Out-File -FilePath $log -Append -Encoding utf8
}
"=== NSIS BUILD DONE ===" | Out-File -FilePath $log -Append -Encoding utf8
