<#
.SYNOPSIS
    Omni-Operator One-Click Internet & Local Installer for Windows.
    Enables instant setup like Antigravity, uv, or rustup via:
    irm https://raw.githubusercontent.com/PTejasKr/ANDA/main/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   OMNI-OPERATOR | ONE-CLICK WINDOWS INTERNET INSTALLER" -ForegroundColor Cyan
Write-Host "   Hardware Shortcut: [Left Ctrl + Windows Key] -> Floating HUD" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Determine Working / Installation Directory
$scriptDir = $PSScriptRoot

# If executed via internet pipe (irm | iex) or outside the repository
if (-not $scriptDir -or -not (Test-Path (Join-Path $scriptDir "hotkey_daemon.py"))) {
    $installDir = Join-Path $env:USERPROFILE ".omni-operator"
    Write-Host "[*] Web installation detected. Target directory: $installDir" -ForegroundColor Yellow

    if (-not (Test-Path $installDir)) {
        New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    }

    $repoUrl = "https://github.com/PTejasKr/ANDA.git"
    $zipUrl = "https://github.com/PTejasKr/ANDA/archive/refs/heads/main.zip"

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "[*] Fetching latest repository files via git..." -ForegroundColor Gray
        if (Test-Path (Join-Path $installDir ".git")) {
            git -C $installDir pull --quiet
        } else {
            git clone --depth 1 $repoUrl $installDir --quiet
        }
    } else {
        Write-Host "[*] Git not found. Downloading release archive from GitHub..." -ForegroundColor Gray
        $zipFile = Join-Path $env:TEMP "omni-operator.zip"
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing
        Expand-Archive -Path $zipFile -DestinationPath $env:TEMP -Force
        $extractedFolder = Join-Path $env:TEMP "ANDA-main"
        Copy-Item -Path "$extractedFolder\*" -Destination $installDir -Recurse -Force
        Remove-Item -Path $zipFile -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $extractedFolder -Recurse -Force -ErrorAction SilentlyContinue
    }
    $scriptDir = $installDir
} else {
    Write-Host "[*] Local installation source: $scriptDir" -ForegroundColor Gray
}

# 2. Check Python Runtime
Write-Host "[1/5] Verifying Python runtime..." -ForegroundColor Yellow
try {
    $pyVersion = & python --version 2>&1
    Write-Host "      -> Found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Error "Python 3.10+ is required. Please install Python from https://python.org or the Microsoft Store."
    exit 1
}

$pythonPath = (Get-Command python).Source
$pythonwPath = Join-Path (Split-Path $pythonPath) "pythonw.exe"
if (-not (Test-Path $pythonwPath)) {
    $pythonwPath = $pythonPath
}
Write-Host "      -> Headless runner: $pythonwPath" -ForegroundColor Gray

# 3. Install Dependencies
Write-Host "[2/5] Checking Python dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $scriptDir "requirements.txt"
if (Test-Path $reqFile) {
    try {
        & python -m pip install -r $reqFile --quiet --disable-pip-version-check
        Write-Host "      -> Dependencies verified." -ForegroundColor Green
    } catch {
        Write-Host "      -> Pip install skipped or already satisfied." -ForegroundColor Gray
    }
}

# 4. Configure Shortcuts (Startup & Desktop)
Write-Host "[3/5] Configuring Windows Startup and Desktop Shortcuts..." -ForegroundColor Yellow
$wshShell = New-Object -ComObject WScript.Shell

$startupFolder = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
$startupLnkPath = Join-Path $startupFolder "ANDA.lnk"
$daemonScript = Join-Path $scriptDir "hotkey_daemon.py"
$deployScript = Join-Path $scriptDir "execution\deploy_local.py"
$startBat = Join-Path $scriptDir "start.bat"

foreach ($oldShortcut in @(
    (Join-Path $startupFolder "OmniOperator.lnk"),
    (Join-Path ([System.Environment]::GetFolderPath("Desktop")) "Omni-Operator (Ctrl+Win).lnk")
)) {
    Remove-Item -LiteralPath $oldShortcut -Force -ErrorAction SilentlyContinue
}

$shortcut = $wshShell.CreateShortcut($startupLnkPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$deployScript`" --with-hotkey"
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "ANDA local stack and global hotkey daemon"
$shortcut.WindowStyle = 7 # Minimized/Hidden
$shortcut.Save()
Write-Host "      -> Configured Auto-Start: $startupLnkPath" -ForegroundColor Green

$desktopFolder = [System.Environment]::GetFolderPath("Desktop")
$desktopLnkPath = Join-Path $desktopFolder "ANDA.lnk"

$desktopShortcut = $wshShell.CreateShortcut($desktopLnkPath)
$desktopShortcut.TargetPath = $startBat
$desktopShortcut.Arguments = ""
$desktopShortcut.WorkingDirectory = $scriptDir
$desktopShortcut.Description = "Start ANDA local stack and desktop HUD"
$desktopShortcut.Save()
Write-Host "      -> Created Desktop Shortcut: $desktopLnkPath" -ForegroundColor Green

# 5. Launch Background Services
Write-Host "[4/5] Launching ANDA local stack in Background..." -ForegroundColor Yellow

# Terminate previous stale instances
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*hotkey_daemon.py*" -or
    $_.CommandLine -like "*server.py*" -or
    $_.CommandLine -like "*deploy_local.py*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Start full stack in background
Start-Process -FilePath $pythonwPath -ArgumentList "`"$deployScript`" --with-hotkey" -WorkingDirectory $scriptDir -WindowStyle Hidden

Start-Sleep -Seconds 4
Write-Host "      -> ANDA stack launch requested. Hotkey: [Left Ctrl + Win]." -ForegroundColor Green

# 6. Verify Installation
Write-Host "[5/5] Running Verification Tests..." -ForegroundColor Yellow
$verifyScript = Join-Path $scriptDir "verify_installation.py"
if (Test-Path $verifyScript) {
    & python $verifyScript
}

$landingUrl = "http://localhost:8080/install.html"
try {
    Start-Process $landingUrl
} catch {
    Write-Host "      -> Open manually: $landingUrl" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   INSTALLATION COMPLETE! READY TO USE." -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " Hardware Hotkey : Press [Left Ctrl + Windows Key] to summon your UI." -ForegroundColor White
Write-Host " Install Page    : http://localhost:8080/install.html" -ForegroundColor Gray
Write-Host " Local HUD       : http://localhost:8080/index.html" -ForegroundColor Gray
Write-Host " Desktop Shortcut: $desktopLnkPath" -ForegroundColor Gray
Write-Host ""
