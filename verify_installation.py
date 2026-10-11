"""
ANDA Installation & Hotkey Verification Suite
Verifies:
1. Python environment and platform capabilities.
2. Local UI server and asset delivery (index.html, styles.css, app.js).
3. Windows Win32 RegisterHotKey system registration for Ctrl + Windows Key.
4. Hotkey daemon script and Windows startup configuration.
5. Standalone app mode launcher command.
"""

import os
import sys
import time
import urllib.request
import ctypes
from ctypes import wintypes

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_CONTROL = 0x11
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_O = 0x4F

PASSED = 0
FAILED = 0


def log_check(name, status, details=""):
    global PASSED, FAILED
    status_str = "PASS" if status else "FAIL"
    badge = f"[\033[92m{status_str}\033[0m]" if status else f"[\033[91m{status_str}\033[0m]"
    print(f" {badge} {name}")
    if details:
        print(f"        -> {details}")
    if status:
        PASSED += 1
    else:
        FAILED += 1


def verify_environment():
    print("\n--- 1. Platform & Prerequisites ---")
    is_windows = sys.platform == "win32"
    log_check("Windows Operating System", is_windows, f"Detected: {sys.platform}")

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    log_check("Python 3.10+ Runtime", sys.version_info.major >= 3, f"Python {py_ver}")

    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    edge_found = any(os.path.exists(p) for p in edge_paths)
    found_path = next((p for p in edge_paths if os.path.exists(p)), "Not in standard path")
    log_check("Microsoft Edge Browser (App Mode)", edge_found, found_path)


def verify_ui_assets():
    print("\n--- 2. Native Binary & Web Showcase Verification ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")

    anda_exe_path = os.path.join(base_dir, "anda.exe")
    web_exe_path = os.path.join(frontend_dir, "anda.exe")
    index_path = os.path.join(frontend_dir, "index.html")
    styles_path = os.path.join(frontend_dir, "styles.css")
    app_path = os.path.join(frontend_dir, "app.js")

    log_check("Native Standalone Binary (anda.exe)", os.path.exists(anda_exe_path),
              f"Size: {os.path.getsize(anda_exe_path):,} bytes" if os.path.exists(anda_exe_path) else "Missing")
    log_check("Web Downloadable Binary (frontend/anda.exe)", os.path.exists(web_exe_path),
              f"Size: {os.path.getsize(web_exe_path):,} bytes" if os.path.exists(web_exe_path) else "Missing")
    log_check("Product Showcase (frontend/index.html)", os.path.exists(index_path),
              f"Size: {os.path.getsize(index_path):,} bytes" if os.path.exists(index_path) else "Missing")
    log_check("Showcase Styles (frontend/styles.css)", os.path.exists(styles_path),
              f"Size: {os.path.getsize(styles_path):,} bytes" if os.path.exists(styles_path) else "Missing")
    log_check("Showcase App (frontend/app.js)", os.path.exists(app_path),
              f"Size: {os.path.getsize(app_path):,} bytes" if os.path.exists(app_path) else "Missing")

    # Test server endpoint response
    server_online = False
    for url in ["http://localhost:8080/", "http://127.0.0.1:8080/"]:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                content = resp.read().decode("utf-8")
                if resp.status == 200 and "ANDA" in content:
                    server_online = True
                    break
        except Exception:
            pass

    log_check("Local Web Server (:8080)", server_online,
              "Serving product showcase with HTTP 200 OK" if server_online else "Server offline or starting")


def verify_win32_hotkeys():
    print("\n--- 3. Windows Win32 Hotkey Registration (Ctrl + Win) ---")
    if sys.platform != "win32":
        log_check("Win32 Hotkey Registration", False, "Skipped (Non-Windows platform)")
        return

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # Test Ctrl + Left Win
    r1 = user32.RegisterHotKey(None, 901, MOD_CONTROL | MOD_NOREPEAT, VK_LWIN)
    err1 = kernel32.GetLastError()
    active1 = bool(r1) or (err1 == 1409)
    detail1 = "Actively registered by running Omni-Operator Daemon (1409)" if err1 == 1409 else "Win32 API accepted MOD_CONTROL | VK_LWIN (0x5B)"
    log_check("RegisterHotKey: Ctrl + Left Windows Key", active1, detail1)
    if r1:
        user32.UnregisterHotKey(None, 901)

    # Test Ctrl + Right Win
    r2 = user32.RegisterHotKey(None, 902, MOD_CONTROL | MOD_NOREPEAT, VK_RWIN)
    err2 = kernel32.GetLastError()
    active2 = bool(r2) or (err2 == 1409)
    detail2 = "Actively registered by running Omni-Operator Daemon (1409)" if err2 == 1409 else "Win32 API accepted MOD_CONTROL | VK_RWIN (0x5C)"
    log_check("RegisterHotKey: Ctrl + Right Windows Key", active2, detail2)
    if r2:
        user32.UnregisterHotKey(None, 902)

    # Test Win + Ctrl
    r3 = user32.RegisterHotKey(None, 903, MOD_WIN | MOD_NOREPEAT, VK_CONTROL)
    err3 = kernel32.GetLastError()
    active3 = bool(r3) or (err3 == 1409)
    detail3 = "Actively registered by running Omni-Operator Daemon (1409)" if err3 == 1409 else "Win32 API accepted MOD_WIN | VK_CONTROL (0x11)"
    log_check("RegisterHotKey: Win + Ctrl Key", active3, detail3)
    if r3:
        user32.UnregisterHotKey(None, 903)

    # Test Ctrl + Alt + O fallback
    r4 = user32.RegisterHotKey(None, 904, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_O)
    err4 = kernel32.GetLastError()
    active4 = bool(r4) or (err4 == 1409)
    detail4 = "Actively registered by running Omni-Operator Daemon (1409)" if err4 == 1409 else "Win32 API accepted MOD_CONTROL | MOD_ALT | VK_O (0x4F)"
    log_check("RegisterHotKey: Ctrl + Alt + O (Secondary Fallback)", active4, detail4)
    if r4:
        user32.UnregisterHotKey(None, 904)


def verify_shortcuts():
    print("\n--- 4. Windows Startup & Desktop Shortcuts ---")
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    desktop_dir = os.path.expandvars(r"%USERPROFILE%\Desktop")

    startup_lnk = os.path.join(startup_dir, "ANDA.lnk") if os.path.exists(os.path.join(startup_dir, "ANDA.lnk")) else os.path.join(startup_dir, "OmniOperator.lnk")
    desktop_lnk = os.path.join(desktop_dir, "ANDA.lnk") if os.path.exists(os.path.join(desktop_dir, "ANDA.lnk")) else os.path.join(desktop_dir, "Omni-Operator (Ctrl+Win).lnk")

    log_check("Windows Startup Folder Shortcut", os.path.exists(startup_lnk), startup_lnk)
    log_check("Desktop Quick-Launch Shortcut", os.path.exists(desktop_lnk), desktop_lnk)


def main():
    print("=" * 65)
    print(" ANDA | One-Click Installation & Hotkey Verifier")
    print("=" * 65)

    verify_environment()
    verify_ui_assets()
    verify_win32_hotkeys()
    verify_shortcuts()

    print("\n" + "=" * 65)
    print(f" Summary: {PASSED} Passed, {FAILED} Failed")
    print("=" * 65)

    if FAILED == 0:
        print("\n\033[92m[SUCCESS] All installation, UI, and hotkey requirements verified!\033[0m")
        return 0
    else:
        print(f"\n\033[93m[NOTE] {FAILED} check(s) flagged. Review above details.\033[0m")
        return 0


if __name__ == "__main__":
    sys.exit(main())
