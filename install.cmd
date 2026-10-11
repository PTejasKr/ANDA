@echo off
setlocal
echo =================================================================
echo   Starting ANDA One-Click Installer...
echo =================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Installation failed with exit code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)
endlocal
