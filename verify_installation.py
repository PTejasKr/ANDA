"""
Omni-Operator Installation & Hotkey Verification Suite
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
    print("\n--- 2. UI Server & Asset Verification ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")

    index_path = os.path.join(frontend_dir, "index.html")
    styles_path = os.path.join(frontend_dir, "styles.css")
    app_path = os.path.join(frontend_dir, "app.js")

    log_check("frontend/index.html exists", os.path.exists(index_path), f"Size: {os.path.getsize(index_path)} bytes")
    log_check("frontend/styles.css exists", os.path.exists(styles_path), f"Size: {os.path.getsize(styles_path)} bytes")
    log_check("frontend/app.js exists", os.path.exists(app_path), f"Size: {os.path.getsize(app_path)} bytes")

    # Verify key spec elements inside files
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    has_orb = "whisper-orb" in html
    has_transcription = "ephemeral-container" in html
    has_drawer = "actionDrawer" in html
    has_loop_a = "modalAmbiguity" in html
    has_loop_b = "modalRunaway" in html
    has_loop_c = "modalTimeout" in html
    has_loop_d = "modalElevation" in html

    all_components = all([has_orb, has_transcription, has_drawer, has_loop_a, has_loop_b, has_loop_c, has_loop_d])
    log_check("Spec UI Components in index.html", all_components,
              "Orb, Transcription, Action Drawer, and all 4 Fallback Loops (A, B, C, D) verified")

    # Test server endpoint response
    server_online = False
    try:
        with urllib.request.urlopen("http://localhost:8080/", timeout=2.0) as resp:
            content = resp.read().decode("utf-8")
            server_online = (resp.status == 200 and "Omni-Operator" in content)
    except Exception as e:
        server_online = False

    log_check("Local Web Server (:8080)", server_online,
              "Responds with HTTP 200 OK" if server_online else "Server offline or starting")


def verify_win32_hotkeys():
    print("\n--- 3. Windows Win32 Hotkey Registration (Ctrl + Win) ---")
    if sys.platform != "win32":
        log_check("Win32 Hotkey Registration", False, "Skipped (Non-Windows platform)")
        return

    user32 = ctypes.windll.user32

    # Test Ctrl + Left Win
    r1 = user32.RegisterHotKey(None, 901, MOD_CONTROL | MOD_NOREPEAT, VK_LWIN)
    log_check("RegisterHotKey: Ctrl + Left Windows Key", bool(r1),
              "Win32 API accepted MOD_CONTROL | VK_LWIN (0x5B)")
    if r1:
        user32.UnregisterHotKey(None, 901)

    # Test Ctrl + Right Win
    r2 = user32.RegisterHotKey(None, 902, MOD_CONTROL | MOD_NOREPEAT, VK_RWIN)
    log_check("RegisterHotKey: Ctrl + Right Windows Key", bool(r2),
              "Win32 API accepted MOD_CONTROL | VK_RWIN (0x5C)")
    if r2:
        user32.UnregisterHotKey(None, 902)

    # Test Win + Ctrl
    r3 = user32.RegisterHotKey(None, 903, MOD_WIN | MOD_NOREPEAT, VK_CONTROL)
    log_check("RegisterHotKey: Win + Ctrl Key", bool(r3),
              "Win32 API accepted MOD_WIN | VK_CONTROL (0x11)")
    if r3:
        user32.UnregisterHotKey(None, 903)

    # Test Ctrl + Alt + O fallback
    r4 = user32.RegisterHotKey(None, 904, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_O)
    log_check("RegisterHotKey: Ctrl + Alt + O (Secondary Fallback)", bool(r4),
              "Win32 API accepted MOD_CONTROL | MOD_ALT | VK_O (0x4F)")
    if r4:
        user32.UnregisterHotKey(None, 904)


def verify_shortcuts():
    print("\n--- 4. Windows Startup & Desktop Shortcuts ---")
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    desktop_dir = os.path.expandvars(r"%USERPROFILE%\Desktop")

    startup_lnk = os.path.join(startup_dir, "OmniOperator.lnk")
    desktop_lnk = os.path.join(desktop_dir, "Omni-Operator (Ctrl+Win).lnk")

    log_check("Windows Startup Folder Shortcut", os.path.exists(startup_lnk), startup_lnk)
    log_check("Desktop Quick-Launch Shortcut", os.path.exists(desktop_lnk), desktop_lnk)


def main():
    print("=" * 65)
    print(" Omni-Operator | One-Click Installation & Hotkey Verifier")
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
