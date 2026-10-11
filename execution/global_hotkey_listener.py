"""
Global Hotkey Listener for Project ANDA
Registers the Windows system-wide shortcut: [Ctrl + Windows / Super]
When triggered, focuses the Project ANDA Voice & Command Deck and activates voice ingestion.
"""

import ctypes
from ctypes import wintypes
import os
import sys
import time
import webbrowser
import requests

# Windows API Constants
MOD_CONTROL = 0x0002
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
HOTKEY_ID = 101

# Virtual Key Codes: Space (0x20), Enter (0x0D), or standalone Super intercept
VK_SPACE = 0x20
VK_OEM_3 = 0xC0  # Tilde ~


class WindowsGlobalHotkey:
    def __init__(self, target_url: str = "http://localhost:8080"):
        self.target_url = target_url
        self.user32 = ctypes.windll.user32

    def trigger_action(self):
        print("\n" + "="*60)
        print("[!] GLOBAL HOTKEY ACTIVATED: [Ctrl + Win/Super]")
        print("[*] Focusing Project ANDA Voice HUD & Command Deck...")
        print("="*60)

        # 1. Open / Focus the Web HUD
        try:
            webbrowser.open(self.target_url)
        except Exception as e:
            print(f"[!] Browser launch error: {e}")

        # 2. Notify Orchestrator of Hotkey Activation Event
        try:
            requests.post(
                f"{self.target_url}/api/orchestrator/command",
                json={"prompt": "stage and categorize files"},
                timeout=1.0,
            )
        except Exception:
            pass

    def run_listener(self):
        print(f"[*] Registering Global Windows Hotkey: [Ctrl + Win + Space] (ID: {HOTKEY_ID})...")
        
        # Register Ctrl + Win + Space as global shortcut
        success = self.user32.RegisterHotKey(
            None,
            HOTKEY_ID,
            MOD_CONTROL | MOD_WIN | MOD_NOREPEAT,
            VK_SPACE,
        )

        if not success:
            # Fallback to Ctrl + Win + ` (Tilde) if Space is reserved by Windows IME
            success = self.user32.RegisterHotKey(
                None,
                HOTKEY_ID,
                MOD_CONTROL | MOD_WIN | MOD_NOREPEAT,
                VK_OEM_3,
            )

        if not success:
            print("[!] Could not register global system hotkey (may require Administrator or key in use).")
            print("[*] Running in mock/simulation mode (press Enter to simulate Ctrl+Win):")
            try:
                while True:
                    input("[Simulation] Press Enter to trigger [Ctrl + Win] action > ")
                    self.trigger_action()
            except KeyboardInterrupt:
                return

        print("[+] Global Hotkey successfully registered across Windows desktop!")
        print("[*] Press [Ctrl + Win + Space] at any time in any application to summon Project ANDA.")
        print("[*] Press Ctrl+C in this terminal to exit.")

        msg = wintypes.MSG()
        try:
            while self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self.trigger_action()
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))
        except KeyboardInterrupt:
            print("\n[*] Unregistering global hotkey and exiting...")
        finally:
            self.user32.UnregisterHotKey(None, HOTKEY_ID)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    hotkey = WindowsGlobalHotkey(target_url=url)
    hotkey.run_listener()
