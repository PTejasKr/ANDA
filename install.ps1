<#
.SYNOPSIS
    ANDA One-Click Installer for Windows Laptops.
    Configures the transparent popup UI, background hotkey daemon, and auto-start.
    Enables toggle via [Ctrl + Windows Key].

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   OMNI-OPERATOR | ONE-CLICK WINDOWS LAPTOP INSTALLER" -ForegroundColor Cyan
Write-Host "   Transparent Popup UI & Global Hotkey [Ctrl + Windows Key]" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/5] Verifying Python installation..." -ForegroundColor Yellow
try {
    $pyVersion = & python --version 2>&1
    Write-Host "      -> Found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Error "Python is not found in PATH. Please install Python 3.10+ from python.org or the Microsoft Store."
    exit 1
}

# Locate pythonw.exe (headless python without console window)
$pythonPath = (Get-Command python).Source
$pythonwPath = Join-Path (Split-Path $pythonPath) "pythonw.exe"
if (-not (Test-Path $pythonwPath)) {
    $pythonwPath = $pythonPath
}
Write-Host "      -> Headless runner: $pythonwPath" -ForegroundColor Gray

# 2. Install dependencies
Write-Host "[2/5] Checking Python dependencies..." -ForegroundColor Yellow
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

$reqFile = Join-Path $scriptDir "requirements.txt"
if (Test-Path $reqFile) {
    try {
        & python -m pip install -r $reqFile --quiet --disable-pip-version-check
        Write-Host "      -> Dependencies verified." -ForegroundColor Green
    } catch {
        Write-Host "      -> Pip install skipped or already satisfied." -ForegroundColor Gray
    }
}

# 3. Create Windows Shortcuts (Startup & Desktop)
Write-Host "[3/5] Configuring Windows Startup and Desktop Shortcuts..." -ForegroundColor Yellow

$wshShell = New-Object -ComObject WScript.Shell

# A. Windows Startup Shortcut (Background Hotkey Daemon)
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
$startupLnkPath = Join-Path $startupFolder "OmniOperator.lnk"
$daemonScript = Join-Path $scriptDir "hotkey_daemon.py"

$shortcut = $wshShell.CreateShortcut($startupLnkPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$daemonScript`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "ANDA Global Hotkey Daemon (Ctrl+Win)"
$shortcut.WindowStyle = 7 # Minimized/Hidden
$shortcut.Save()
Write-Host "      -> Configured Auto-Start: $startupLnkPath" -ForegroundColor Green

# B. Desktop Quick-Launch Shortcut (Toggle UI)
$desktopFolder = [System.Environment]::GetFolderPath("Desktop")
$desktopLnkPath = Join-Path $desktopFolder "ANDA (Ctrl+Win).lnk"

$desktopShortcut = $wshShell.CreateShortcut($desktopLnkPath)
$desktopShortcut.TargetPath = $pythonwPath
$desktopShortcut.Arguments = "`"$daemonScript`" --toggle"
$desktopShortcut.WorkingDirectory = $scriptDir
$desktopShortcut.Description = "ANDA Transparent Popup UI"
$desktopShortcut.Save()
Write-Host "      -> Created Desktop Shortcut: $desktopLnkPath" -ForegroundColor Green

# 4. Start Background Services Immediately
Write-Host "[4/5] Launching ANDA Hotkey Daemon in Background..." -ForegroundColor Yellow

# Kill any existing stale instances
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*hotkey_daemon.py*" -or $_.CommandLine -like "*server.py*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Start server.py in background
$serverScript = Join-Path $scriptDir "server.py"
Start-Process -FilePath $pythonwPath -ArgumentList "`"$serverScript`"" -WorkingDirectory $scriptDir -WindowStyle Hidden

# Start hotkey_daemon.py in background
Start-Process -FilePath $pythonwPath -ArgumentList "`"$daemonScript`"" -WorkingDirectory $scriptDir -WindowStyle Hidden

Start-Sleep -Seconds 2
Write-Host "      -> Background Daemon is ACTIVE and listening for [Ctrl + Win]!" -ForegroundColor Green

# 5. Run Verification Suite
Write-Host "[5/5] Running Verification Tests..." -ForegroundColor Yellow
$verifyScript = Join-Path $scriptDir "verify_installation.py"
& python $verifyScript

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   INSTALLATION COMPLETE! READY TO USE." -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " Hotkey Activated: Press [Ctrl + Windows Key] to toggle your popup UI." -ForegroundColor White
Write-Host " Local Web URL   : http://localhost:8080" -ForegroundColor Gray
Write-Host " Desktop Icon    : $desktopLnkPath" -ForegroundColor Gray
Write-Host ""
