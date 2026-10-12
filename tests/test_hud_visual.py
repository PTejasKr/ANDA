"""
HUD Visual Verification Script
Starts AndaHUDApp in a controlled test harness, takes a screenshot of the window,
and saves it to test_hud_pinterest.png for visual verification.
"""

import sys
import os
import time
import threading
from PIL import ImageGrab

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "execution"))
from anda_app import AndaHUDApp

def capture_and_close(app):
    time.sleep(1.0)
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import Image

        hwnd = app.root.winfo_id()
        w = app.root.winfo_width()
        h = app.root.winfo_height()

        hdc_win = ctypes.windll.user32.GetWindowDC(hwnd)
        hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_win)
        hbm = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_win, w, h)
        ctypes.windll.gdi32.SelectObject(hdc_mem, hbm)

        # PrintWindow flag 2 (PW_RENDERFULLCONTENT)
        ctypes.windll.user32.PrintWindow(hwnd, hdc_mem, 2)

        # Extract bits
        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        ctypes.windll.gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bmi), 0)

        ctypes.windll.gdi32.DeleteObject(hbm)
        ctypes.windll.gdi32.DeleteDC(hdc_mem)
        ctypes.windll.user32.ReleaseDC(hwnd, hdc_win)

        img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
        img.save("test_hud_pinterest.png")
        print(f"[+] Screen capture succeeded: test_hud_pinterest.png ({w}x{h})")
    except Exception as e:
        print(f"[-] Win32 capture failed: {e}")
    finally:
        app.root.after(100, app.root.destroy)

if __name__ == "__main__":
    app = AndaHUDApp()
    threading.Thread(target=capture_and_close, args=(app,), daemon=True).start()
    app.root.mainloop()
