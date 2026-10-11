@echo off
setlocal
cd /d "%~dp0"
echo =====================================================================
echo   ANDA - Dual-Plane Desktop Agent with Hotkey Daemon
echo =====================================================================
echo.
python execution\deploy_local.py --with-hotkey %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Process exited with error code %ERRORLEVEL%.
    pause
)
endlocal
