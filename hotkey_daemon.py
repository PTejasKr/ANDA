"""
ANDA: Windows Global Hotkey & Desktop Overlay Daemon
Registers Ctrl + Windows Key (and Win + Ctrl) to toggle the transparent popup UI.
Pure standard library: uses ctypes Win32 API.
"""

import os
import sys
import time
import threading
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

APP_URL = "http://localhost:8080/index.html"
INSTALL_URL = "http://localhost:8080/install.html"
STATUS_URL = "http://localhost:8080/api/system/status"
APP_TITLE = "ANDA | Minimal Whisper Flow"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(SCRIPT_DIR, "server.py")
DEPLOY_SCRIPT = os.path.join(SCRIPT_DIR, "execution", "deploy_local.py")


def is_full_stack_running():
    for url in [STATUS_URL, "http://127.0.0.1:8080/api/system/status"]:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status != 200:
                    continue
                import json
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("orchestrator") == "online" and data.get("worker_plane") == "online" and data.get("daemon_ipc") == "online":
                    return True
        except Exception:
            pass
    return False


def start_full_stack(include_hotkey=False):
    args = [sys.executable, DEPLOY_SCRIPT]
    if include_hotkey:
        args.append("--with-hotkey")
    print("[*] Starting ANDA full local stack in background...")
    DETACHED = 0x00000008 | 0x00000200 # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        args,
        cwd=SCRIPT_DIR,
        creationflags=DETACHED,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def ensure_server_running(include_hotkey=False):
    if is_full_stack_running():
        return True

    if os.environ.get("ANDA_STACK_MANAGED") == "1":
        print("[*] Waiting for managed ANDA stack to become responsive...")
        for _ in range(40):
            time.sleep(0.25)
            if is_full_stack_running():
                print("[*] Managed ANDA stack is active.")
                return True
        print("[!] Warning: managed stack is not fully responsive yet.")
        return False

    if os.path.exists(DEPLOY_SCRIPT):
        start_full_stack(include_hotkey=include_hotkey)
        for _ in range(50):
            time.sleep(0.25)
            if is_full_stack_running():
                print("[*] Full ANDA stack is active and responding.")
                return True

    if not is_full_stack_running():
        print("[*] Starting fallback ANDA web server in background...")
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
            try:
                with urllib.request.urlopen(APP_URL, timeout=1.0) as resp:
                    if resp.status == 200:
                        print("[*] Fallback web server is active and responding.")
                        return True
            except Exception:
                pass
        print("[!] Warning: web server started but not fully responding yet.")
        return False
    return True


def open_install_page():
    ensure_server_running(include_hotkey=True)
    browser_exe = get_browser_app_cmd()
    if browser_exe:
        DETACHED = 0x00000008 | 0x00000200
        subprocess.Popen(
            [browser_exe, f"--app={INSTALL_URL}", "--window-size=1180,860"],
            creationflags=DETACHED,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        import webbrowser
        webbrowser.open(INSTALL_URL)


def find_app_window():
    """Finds existing Edge/Chrome/Brave app window hosting ANDA."""
    inp = user32.OpenInputDesktop(0, False, 0x01FF)
    if inp:
        user32.SetThreadDesktop(inp)
    found_hwnd = [None]

    def enum_windows_callback(hwnd, lParam):
        if not user32.IsWindow(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if any(k in title for k in ["ANDA", "Autonomous Native", "Minimal Whisper Flow", "Omni-Operator"]):
                if not any(k in title.lower() for k in ["visual studio", "antigravity", "powershell", "cmd.exe"]):
                    found_hwnd[0] = hwnd
                    return False  # Stop enumeration
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)
    return found_hwnd[0]


def get_browser_app_cmd():
    """Finds brave, msedge or chrome to launch in app mode."""
    brave_paths = [
        os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    for p in brave_paths:
        if os.path.exists(p):
            return p

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
    inp = user32.OpenInputDesktop(0, False, 0x01FF)
    if inp:
        user32.SetThreadDesktop(inp)

    ensure_server_running(include_hotkey=True)

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

    # Window does not exist yet: launch in chromeless app mode with isolated profile
    browser_exe = get_browser_app_cmd()
    user_data = os.path.expandvars(r"%LocalAppData%\ANDA\hud_session")
    if browser_exe:
        print(f"[*] Launching popup window using {os.path.basename(browser_exe)} in app mode...")
        cmd = [
            browser_exe,
            f"--user-data-dir={user_data}",
            f"--app={APP_URL}",
            "--window-size=740,890",
            "--window-position=590,80",
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
        time.sleep(0.8)
        new_hwnd = find_app_window()
        if new_hwnd:
            user32.SetWindowPos(new_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            user32.SetForegroundWindow(new_hwnd)
    else:
        # Fallback to default browser
        import webbrowser
        print("[*] Opening UI in default browser...")
        webbrowser.open(APP_URL)


def hardware_key_listener():
    """Direct hardware keyboard polling for Left Ctrl + Windows Key with debouncing."""
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    was_pressed = False

    inp = user32.OpenInputDesktop(0, False, 0x01FF)
    if inp:
        user32.SetThreadDesktop(inp)

    while True:
        try:
            ctrl_down = bool((user32.GetAsyncKeyState(VK_LCONTROL) & 0x8000) or (user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000))
            win_down = bool((user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000))

            if ctrl_down and win_down:
                if not was_pressed:
                    was_pressed = True
                    print("[!] Hardware Keyboard Shortcut Detected: Left Ctrl + Win")
                    launch_or_toggle_ui()
            else:
                was_pressed = False
            time.sleep(0.02)
        except Exception:
            time.sleep(0.1)


def run_daemon():
    print("=" * 65)
    print(" ANDA | Windows Hotkey Daemon")
    print(" Press Ctrl + Windows Key to toggle the transparent popup UI")
    print("=" * 65)

    inp = user32.OpenInputDesktop(0, False, 0x01FF)
    if inp:
        user32.SetThreadDesktop(inp)

    ensure_server_running(include_hotkey=False)

    # Launch hardware keyboard poller thread for 100% reliable Left Ctrl + Win capture
    hw_thread = threading.Thread(target=hardware_key_listener, daemon=True)
    hw_thread.start()

    # Create message queue for thread
    msg = wintypes.MSG()
    user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

    # Register Fallback hotkey: Ctrl + Alt + O
    h4 = user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_O)

    print(f"[*] Hotkeys Registered:")
    print(f"    - Hardware Key combo [Ctrl + Win] : ARMED & POLLING (20ms)")
    print(f"    - Ctrl + Alt + O                  : {'SUCCESS' if h4 else 'FAILED'} (Secondary Fallback)")
    print("[*] Daemon listening for hotkey combo...")

    try:
        while True:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res > 0:
                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    print(f"[!] Hotkey Triggered! ID: {hotkey_id}")
                    launch_or_toggle_ui()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[*] Stopping hotkey daemon...")
    finally:
        user32.UnregisterHotKey(None, 4)
        print("[*] Unregistered all hotkeys cleanly.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--toggle":
        launch_or_toggle_ui()
    elif len(sys.argv) > 1 and sys.argv[1] == "--install-page":
        open_install_page()
    else:
        run_daemon()
