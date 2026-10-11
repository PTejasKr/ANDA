@echo off
setlocal
cd /d "%~dp0"
echo =====================================================================
echo   ANDA - Autonomous Native Desktop Assistant for Windows
echo   Hardware Shortcut: [Left Ctrl + Windows Key]
echo =====================================================================
echo.
echo Showcase & Install Portal : http://localhost:8080/
echo Native Floating HUD App   : anda.exe (Microphone + Textbox Only)
echo.
python execution\deploy_local.py --with-hotkey %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Process exited with error code %ERRORLEVEL%.
    pause
)
endlocal
