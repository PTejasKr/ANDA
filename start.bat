@echo off
setlocal
cd /d "%~dp0"
echo =====================================================================
echo   OMNI-OPERATOR - Dual-Plane Stack with Hotkey Daemon
echo =====================================================================
echo.
python execution\deploy_local.py --with-hotkey %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Process exited with error code %ERRORLEVEL%.
    pause
)
endlocal
