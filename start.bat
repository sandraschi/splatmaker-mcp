@echo off
REM start.bat - delegate to start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
