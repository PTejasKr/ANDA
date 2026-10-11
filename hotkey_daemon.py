"""
ANDA: Windows Global Hotkey & Desktop Overlay Daemon
Registers Ctrl + Windows Key (and Win + Ctrl) to toggle the transparent popup UI.
Pure standard library: uses ctypes Win32 API.
"""

import os
import sys
import time
import subprocess
import urllib.request
import ctypes
from ctypes import wintypes

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_CONTROL = 0x11
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_O = 0x4F
VK_SPACE = 0x20

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9

HWND_TOP = 0
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

APP_URL = "http://localhost:8080"
APP_TITLE = "ANDA | Minimal Whisper Flow"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, "server.py")


def is_server_running():
    for url in [f"{APP_URL}/", "http://127.0.0.1:8080/"]:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    return False


def ensure_server_running():
    if not is_server_running():
        print("[*] Starting ANDA web server in background...")
        DETACHED = 0x00000008 | 0x00000200 # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            cwd=SCRIPT_DIR,
            creationflags=DETACHED,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        for _ in range(25):
            time.sleep(0.2)
            if is_server_running():
                print("[*] Web server is active and responding.")
                return True
        print("[!] Warning: Web server started but not responding yet.")
        return False
    return True


def find_app_window():
    """Finds existing Edge/Chrome app window hosting ANDA."""
    found_hwnd = [None]

    def enum_windows_callback(hwnd, lParam):
        if not user32.IsWindow(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if "ANDA" in title or "Minimal Whisper Flow" in title:
                found_hwnd[0] = hwnd
                return False  # Stop enumeration
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    return found_hwnd[0]


def get_browser_app_cmd():
    """Finds msedge or chrome to launch in app mode."""
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in edge_paths:
        if os.path.exists(p):
            return p

    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in chrome_paths:
        if os.path.exists(p):
            return p

    return None


def launch_or_toggle_ui():
    """Toggles the transparent popup UI or launches it if not open."""
    ensure_server_running()

    hwnd = find_app_window()
    if hwnd:
        # Window exists: check visibility
        if user32.IsWindowVisible(hwnd):
            foreground_hwnd = user32.GetForegroundWindow()
            if foreground_hwnd == hwnd:
                # Active in foreground -> toggle hide
                print("[*] Toggling UI: Hiding active window.")
                user32.ShowWindow(hwnd, SW_HIDE)
                return
            else:
                # Visible in background -> bring to front
                print("[*] Toggling UI: Bringing to foreground.")
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                user32.SetForegroundWindow(hwnd)
                return
        else:
            # Window was hidden -> show and bring to front
            print("[*] Toggling UI: Unhiding window.")
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            user32.SetForegroundWindow(hwnd)
            return

    # Window does not exist yet: launch in chromeless app mode
    browser_exe = get_browser_app_cmd()
    if browser_exe:
        print(f"[*] Launching popup window using {os.path.basename(browser_exe)} in app mode...")
        cmd = [
            browser_exe,
            f"--app={APP_URL}",
            "--window-size=740,890",
            "--window-position=400,80",
            "--disable-features=TranslateUI",
            "--disable-extensions",
        ]
        DETACHED = 0x00000008 | 0x00000200
        subprocess.Popen(
            cmd,
            creationflags=DETACHED,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        # Fallback to default browser
        import webbrowser
        print("[*] Opening UI in default browser...")
        webbrowser.open(APP_URL)


def run_daemon():
    print("=" * 65)
    print(" ANDA | Windows Hotkey Daemon")
    print(" Press Ctrl + Windows Key to toggle the transparent popup UI")
    print("=" * 65)

    ensure_server_running()

    # Create message queue for thread
    msg = wintypes.MSG()
    user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

    # Register Global Hotkeys:
    # 1. Ctrl + Left Windows Key
    h1 = user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_NOREPEAT, VK_LWIN)
    # 2. Ctrl + Right Windows Key
    h2 = user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_NOREPEAT, VK_RWIN)
    # 3. Windows Key + Ctrl Key
    h3 = user32.RegisterHotKey(None, 3, MOD_WIN | MOD_NOREPEAT, VK_CONTROL)
    # 4. Fallback secondary hotkey: Ctrl + Alt + O
    h4 = user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_O)

    print(f"[*] Hotkeys Registered:")
    print(f"    - Ctrl + Left Win : {'SUCCESS' if h1 else 'FAILED'}")
    print(f"    - Ctrl + Right Win: {'SUCCESS' if h2 else 'FAILED'}")
    print(f"    - Win + Ctrl      : {'SUCCESS' if h3 else 'FAILED'}")
    print(f"    - Ctrl + Alt + O  : {'SUCCESS' if h4 else 'FAILED'} (Secondary Fallback)")
    print("[*] Daemon listening for hotkey combo...")

    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                print(f"[!] Hotkey Triggered! ID: {hotkey_id}")
                launch_or_toggle_ui()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except KeyboardInterrupt:
        print("\n[*] Stopping hotkey daemon...")
    finally:
        user32.UnregisterHotKey(None, 1)
        user32.UnregisterHotKey(None, 2)
        user32.UnregisterHotKey(None, 3)
        user32.UnregisterHotKey(None, 4)
        print("[*] Unregistered all hotkeys cleanly.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--toggle":
        launch_or_toggle_ui()
    else:
        run_daemon()
