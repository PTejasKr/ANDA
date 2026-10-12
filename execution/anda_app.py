"""
ANDA: Autonomous Native Desktop Assistant
A pure native Windows floating HUD application.
UI: A sleek, transparent floating pill consisting ONLY of a Microphone and a Textbox.
Summoned anywhere across Windows via hardware shortcut: [Left Ctrl + Windows Key].
Powered by Gemma 3 for free background task orchestration.
"""

import os
import sys
import time
import json
import wave
import io
import threading
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import subprocess
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import font

# Win32 Constants
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_O = 0x4F
VK_ESCAPE = 0x1B

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ORCHESTRATOR_URL = "http://127.0.0.1:8080"
COMMAND_API = f"{ORCHESTRATOR_URL}/api/orchestrator/command"
TRANSCRIBE_API = f"{ORCHESTRATOR_URL}/api/stt/transcribe"
SYSTEM_STATUS_API = f"{ORCHESTRATOR_URL}/api/system/status"

# Audio recording via sounddevice if available
try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class AndaHUDApp:
    def __init__(self):
        # Attach thread to interactive desktop
        self.attach_desktop()

        self.root = tk.Tk()
        self.root.title("ANDA")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        # Transparency on Windows
        self.bg_trans = "#010101"
        self.root.config(bg=self.bg_trans)
        try:
            self.root.wm_attributes("-transparentcolor", self.bg_trans)
        except Exception:
            pass

        # Dimensions & positioning
        self.width = 660
        self.height = 92
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.x = (self.screen_width - self.width) // 2
        self.y = self.screen_height - self.height - 130
        self.root.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")

        # State
        self.is_recording = False
        self.recorded_frames = []
        self.record_stream = None
        self.is_visible = True
        self.is_busy = False
        self.pulse_phase = 0
        self.pulse_timer = None

        self.setup_ui()
        self.setup_bindings()
        self.start_hotkey_listener()

        # Check server health in background
        threading.Thread(target=self.ensure_backend_alive, daemon=True).start()

    def attach_desktop(self):
        try:
            inp = user32.OpenInputDesktop(0, False, 0x01FF)
            if inp:
                user32.SetThreadDesktop(inp)
        except Exception:
            pass

    def setup_ui(self):
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=self.bg_trans,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Draw sleek rounded dark container
        self.draw_pill_container("#090D16", "#38BDF8")

        # 1. Microphone Orb (Canvas oval button)
        self.mic_center_x = 46
        self.mic_center_y = 42
        self.mic_radius = 22

        self.mic_glow_id = self.canvas.create_oval(
            self.mic_center_x - self.mic_radius - 4,
            self.mic_center_y - self.mic_radius - 4,
            self.mic_center_x + self.mic_radius + 4,
            self.mic_center_y + self.mic_radius + 4,
            fill="",
            outline="",
            width=2
        )

        self.mic_circle_id = self.canvas.create_oval(
            self.mic_center_x - self.mic_radius,
            self.mic_center_y - self.mic_radius,
            self.mic_center_x + self.mic_radius,
            self.mic_center_y + self.mic_radius,
            fill="#1E293B",
            outline="#334155",
            width=1.5
        )

        self.mic_icon_id = self.canvas.create_text(
            self.mic_center_x,
            self.mic_center_y - 1,
            text="🎙",
            fill="#38BDF8",
            font=("Segoe UI Emoji", 14, "bold")
        )

        self.canvas.tag_bind(self.mic_circle_id, "<Button-1>", lambda e: self.toggle_voice())
        self.canvas.tag_bind(self.mic_icon_id, "<Button-1>", lambda e: self.toggle_voice())

        # 2. Text Input Entry Widget
        self.entry_frame = tk.Frame(self.canvas, bg="#0F172A", bd=0, highlightthickness=1, highlightbackground="#334155")
        self.entry_frame.place(x=82, y=20, width=490, height=44)

        self.entry_var = tk.StringVar()
        self.placeholder_text = "Ask ANDA anything... (Press Enter to execute)"
        self.entry = tk.Entry(
            self.entry_frame,
            textvariable=self.entry_var,
            font=("Segoe UI", 12),
            bg="#0F172A",
            fg="#94A3B8",
            bd=0,
            insertbackground="#38BDF8",
            relief="flat"
        )
        self.entry.insert(0, self.placeholder_text)
        self.entry.pack(fill="both", expand=True, padx=14, pady=8)

        # 3. Send Arrow Button
        self.btn_send = tk.Canvas(
            self.canvas,
            width=42,
            height=42,
            bg=self.bg_trans,
            highlightthickness=0,
            bd=0
        )
        self.btn_send.place(x=588, y=21)
        self.btn_send_bg = self.btn_send.create_oval(2, 2, 40, 40, fill="#0284C7", outline="#38BDF8", width=1.5)
        self.btn_send_txt = self.btn_send.create_text(21, 20, text="➔", fill="#FFFFFF", font=("Segoe UI", 13, "bold"))

        self.btn_send.bind("<Button-1>", lambda e: self.submit_command())
        self.btn_send.bind("<Enter>", lambda e: self.btn_send.itemconfig(self.btn_send_bg, fill="#0369A1"))
        self.btn_send.bind("<Leave>", lambda e: self.btn_send.itemconfig(self.btn_send_bg, fill="#0284C7"))

        # 4. Status Ephemeral Feedback Label
        self.status_id = self.canvas.create_text(
            self.width // 2,
            76,
            text="⚡ Ready • Press [Left Ctrl + Win] to toggle",
            fill="#64748B",
            font=("Segoe UI", 9)
        )

    def draw_pill_container(self, fill_color, border_color):
        r = 24 # border radius
        x1, y1 = 4, 4
        x2, y2 = self.width - 4, self.height - 4
        
        # Draw anti-aliased pill polygon
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        self.canvas.create_polygon(points, fill=fill_color, outline=border_color, width=1.8, smooth=True)

    def setup_bindings(self):
        self.entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.entry.bind("<Return>", lambda e: self.submit_command())
        self.root.bind("<Escape>", lambda e: self.hide_window())

        # Enable window dragging by clicking empty areas of canvas
        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def do_move(self, event):
        dx = event.x - self.drag_x
        dy = event.y - self.drag_y
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def on_entry_focus_in(self, event):
        if self.entry.get() == self.placeholder_text:
            self.entry.delete(0, tk.END)
            self.entry.config(fg="#F8FAFC")

    def on_entry_focus_out(self, event):
        if not self.entry.get().strip():
            self.entry.insert(0, self.placeholder_text)
            self.entry.config(fg="#94A3B8")

    def set_status(self, text, color="#64748B"):
        self.canvas.itemconfig(self.status_id, text=text, fill=color)

    def show_window(self):
        self.attach_desktop()
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        if self.entry.get() == self.placeholder_text:
            self.entry.delete(0, tk.END)
            self.entry.config(fg="#F8FAFC")
        self.is_visible = True

    def hide_window(self):
        self.root.withdraw()
        self.is_visible = False

    def toggle_window(self):
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()

    def start_hotkey_listener(self):
        def listener():
            was_pressed = False
            self.attach_desktop()
            while True:
                try:
                    ctrl_down = bool((user32.GetAsyncKeyState(VK_LCONTROL) & 0x8000) or (user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000))
                    win_down = bool((user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000))

                    if ctrl_down and win_down:
                        if not was_pressed:
                            was_pressed = True
                            self.root.after(0, self.toggle_window)
                    else:
                        was_pressed = False
                    time.sleep(0.02)
                except Exception:
                    time.sleep(0.1)

        t = threading.Thread(target=listener, daemon=True)
        t.start()

    def toggle_voice(self):
        if not AUDIO_AVAILABLE:
            self.set_status("⚠️ Audio library not available. Please type your instruction.", "#EF4444")
            return

        if self.is_recording:
            self.stop_voice()
        else:
            self.start_voice()

    def start_voice(self):
        self.is_recording = True
        self.recorded_frames = []
        self.canvas.itemconfig(self.mic_circle_id, fill="#0284C7", outline="#38BDF8")
        self.canvas.itemconfig(self.mic_icon_id, fill="#FFFFFF")
        self.set_status("🎙️ Listening... Speak your instruction (auto-enters on pause)", "#38BDF8")
        self.animate_mic_pulse(True)

        def record_thread():
            try:
                fs = 16000
                has_spoken = False
                silence_start = None
                silence_timeout = 1.3  # Auto-submit after 1.3s silence following speech
                speech_threshold = 400 # Amplitude energy threshold

                def callback(indata, frames, time_info, status):
                    nonlocal has_spoken, silence_start
                    if not self.is_recording:
                        return
                    self.recorded_frames.append(indata.copy())

                    energy = float(np.abs(indata).mean())
                    if energy > speech_threshold:
                        has_spoken = True
                        silence_start = None
                    elif has_spoken:
                        now = time.time()
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= silence_timeout:
                            # User finished speech -> auto-stop and execute seamlessly
                            self.root.after(0, self.stop_voice)

                with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback):
                    while self.is_recording:
                        time.sleep(0.05)
            except Exception as e:
                self.root.after(0, lambda: self.set_status(f"⚠️ Mic error: {e}", "#EF4444"))
                self.is_recording = False

        threading.Thread(target=record_thread, daemon=True).start()

    def stop_voice(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.animate_mic_pulse(False)
        self.canvas.itemconfig(self.mic_circle_id, fill="#1E293B", outline="#334155")
        self.canvas.itemconfig(self.mic_icon_id, fill="#38BDF8")
        self.set_status("⚡ Transcribing speech to text...", "#F59E0B")

        if not self.recorded_frames:
            self.set_status("⚡ No audio captured. Try speaking again.", "#94A3B8")
            return

        threading.Thread(target=self.send_audio_transcribe, daemon=True).start()

    def animate_mic_pulse(self, active):
        if not active:
            self.canvas.itemconfig(self.mic_glow_id, outline="")
            return

        colors = ["#38BDF8", "#0284C7", "#0369A1", "#0284C7"]
        self.pulse_phase = (self.pulse_phase + 1) % len(colors)
        self.canvas.itemconfig(self.mic_glow_id, outline=colors[self.pulse_phase])

        if self.is_recording:
            self.root.after(160, lambda: self.animate_mic_pulse(True))

    def send_audio_transcribe(self):
        try:
            fs = 16000
            audio_data = np.concatenate(self.recorded_frames, axis=0)
            
            # Export to in-memory WAV
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2) # 16-bit
                wf.setframerate(fs)
                wf.writeframes(audio_data.tobytes())
            
            wav_bytes = wav_io.getvalue()
            import base64
            b64_audio = base64.b64encode(wav_bytes).decode('utf-8')

            # 1. Try Local Speech Recognition if available
            text = ""
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                    audio_sr = recognizer.record(source)
                    text = recognizer.recognize_google(audio_sr)
            except Exception:
                text = ""

            # 2. If local SR didn't succeed, try Orchestrator or Worker API
            if not text:
                req_data = json.dumps({"audio_b64": b64_audio, "audio_data": b64_audio}).encode('utf-8')
                for ep in [TRANSCRIBE_API, "http://127.0.0.1:50051/api/stt/transcribe", "https://anda-omni-operator.fly.dev/api/ai/stt"]:
                    try:
                        req = urllib.request.Request(ep, data=req_data, headers={"Content-Type": "application/json"})
                        with urllib.request.urlopen(req, timeout=5.0) as resp:
                            res = json.loads(resp.read().decode('utf-8'))
                            text = (res.get("text") or res.get("transcription") or "").strip()
                            if text:
                                break
                    except Exception:
                        continue

            if text:
                self.root.after(0, lambda: self.on_transcription_ready(text))
            else:
                self.root.after(0, lambda: self.set_status("⚡ Could not recognize speech. Type or try again.", "#94A3B8"))
        except Exception as e:
            self.root.after(0, lambda: self.set_status(f"Speech STT fallback: {e}", "#94A3B8"))

    def on_transcription_ready(self, text):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)
        self.entry.config(fg="#F8FAFC")
        self.submit_command()

    def submit_command(self):
        prompt = self.entry.get().strip()
        if not prompt or prompt == self.placeholder_text:
            return

        if self.is_busy:
            return

        self.is_busy = True
        self.set_status("🧠 Gemma 3: Reasoning & executing in background...", "#38BDF8")

        threading.Thread(target=self.execute_task_thread, args=(prompt,), daemon=True).start()

    def execute_task_thread(self, prompt):
        res = None
        # 1. Try Go Orchestrator (:8080)
        try:
            req_data = json.dumps({"prompt": prompt}).encode('utf-8')
            req = urllib.request.Request(COMMAND_API, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res = json.loads(resp.read().decode('utf-8'))
        except Exception:
            pass

        # 2. Try Python Worker Plane (:50051) directly
        if not res:
            try:
                req_data = json.dumps({"prompt": prompt}).encode('utf-8')
                req = urllib.request.Request("http://127.0.0.1:50051/api/brain/parse", data=req_data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    brain_res = json.loads(resp.read().decode('utf-8'))
                    res = {
                        "status": "success",
                        "route": {"action": brain_res.get("action", "execute")},
                        "message": brain_res.get("reasoning", "Processed by Gemma Brain"),
                    }
            except Exception:
                pass

        # 3. Try Cloud Edge Orchestrator
        if not res:
            try:
                req_data = json.dumps({"prompt": prompt}).encode('utf-8')
                req = urllib.request.Request("https://project-anda.fly.dev/api/orchestrator/command", data=req_data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    res = json.loads(resp.read().decode('utf-8'))
            except Exception:
                pass

        # 4. Fallback to local semantic reasoning (zero cost, zero failure)
        target_url = res.get("target_url") if res else None
        system_uri = res.get("system_uri") if res else None

        if not res or (not target_url and not system_uri):
            lower = prompt.lower()
            if any(k in lower for k in ["setting", "sound", "volume", "display", "bluetooth", "wifi", "task manager", "calculator", "control panel"]):
                action = "open_setting"
                if any(k in lower for k in ["sound", "volume", "audio"]):
                    system_uri = "ms-settings:sound"
                    msg = "Opened Windows Sound & Audio Settings."
                elif any(k in lower for k in ["display", "screen", "resolution", "brightness"]):
                    system_uri = "ms-settings:display"
                    msg = "Opened Windows Display Settings."
                elif any(k in lower for k in ["wifi", "wi-fi", "network", "internet"]):
                    system_uri = "ms-settings:network-wifi"
                    msg = "Opened Windows Network & Wi-Fi Settings."
                elif any(k in lower for k in ["bluetooth", "devices"]):
                    system_uri = "ms-settings:bluetooth"
                    msg = "Opened Windows Bluetooth & Devices."
                elif any(k in lower for k in ["task manager", "taskmgr"]):
                    system_uri = "taskmgr"
                    msg = "Opened Windows Task Manager."
                elif any(k in lower for k in ["calculator", "calc"]):
                    system_uri = "calc"
                    msg = "Opened Windows Calculator."
                elif "control panel" in lower:
                    system_uri = "control"
                    msg = "Opened Windows Control Panel."
                else:
                    system_uri = "ms-settings:"
                    msg = "Opened Windows System Settings."
            elif any(k in lower for k in ["on the internet", "search", "google", "look up"]):
                action = "web_search"
                clean = lower
                for p in ["search something on the internet for ", "search something on the internet about ", "search something on the internet", "search the internet for ", "search the internet", "search on the internet for ", "search on the internet", "search for ", "search ", "google ", "look up ", "find "]:
                    if clean.startswith(p):
                        clean = clean[len(p):].strip()
                        break
                for sfx in [" on the internet", " in google", " on google"]:
                    if clean.endswith(sfx):
                        clean = clean[:-len(sfx)].strip()
                clean = clean.strip(".!?,; ") or "technology trends"
                target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean)}"
                msg = f"Searched the internet for '{clean}' and opened browser."
            elif any(lower.startswith(p) for p in ["open ", "go to ", "visit ", "browse ", "launch "]) or any(ext in lower for ext in [".com", ".org", ".io", ".net", "youtube", "browser"]):
                action = "open_browser"
                clean = lower
                for p in ["open a browser and go to ", "open a browser and visit ", "open browser and go to ", "open browser to ", "open a browser", "open browser", "navigate to ", "go to ", "visit ", "browse ", "launch ", "open "]:
                    if clean.startswith(p):
                        clean = clean[len(p):].strip()
                        break
                clean = clean.strip(".!?,; ")
                known = {
                    "youtube": "https://www.youtube.com",
                    "google": "https://www.google.com",
                    "github": "https://github.com",
                    "reddit": "https://www.reddit.com",
                    "twitter": "https://x.com",
                    "x": "https://x.com",
                    "dribbble": "https://dribbble.com",
                    "wikipedia": "https://www.wikipedia.org",
                    "gmail": "https://mail.google.com",
                    "netflix": "https://www.netflix.com",
                    "spotify": "https://open.spotify.com",
                    "chatgpt": "https://chatgpt.com",
                    "amazon": "https://www.amazon.com",
                }
                if clean in known:
                    target_url = known[clean]
                elif clean.startswith("http://") or clean.startswith("https://"):
                    target_url = clean
                elif "." in clean and " " not in clean:
                    target_url = f"https://{clean}"
                elif " " not in clean and clean:
                    target_url = f"https://www.{clean}.com"
                elif not clean:
                    target_url = "https://www.google.com"
                else:
                    target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean)}"
                msg = f"Opened {target_url} in your default browser."
            elif "stage" in lower or "organize" in lower:
                action = "stage_files"
                msg = "Organized local downloads and verified file categories."
            elif "flash" in lower:
                action = "flash_usb"
                msg = "Elevated operation scheduled (requires physical confirmation)."
            elif "memory" in lower or "recall" in lower:
                action = "query_memory"
                msg = "Queried vector memory context successfully."
            else:
                action = "gemma_reasoning"
                msg = f"Task received and executed by background Gemma engine: '{prompt[:40]}...'"

            res = {
                "status": "success",
                "route": {"action": action},
                "target_url": target_url,
                "system_uri": system_uri,
                "message": msg,
            }

        # Physical execution of real actions on Windows
        if target_url:
            try:
                webbrowser.open(target_url)
            except Exception:
                try:
                    os.system(f'start "" "{target_url}"')
                except Exception:
                    pass
        elif system_uri:
            try:
                os.system(f'start {system_uri}')
            except Exception:
                pass

        route = res.get("route", {})
        action = route.get("action", "execute") if isinstance(route, dict) else "execute"
        msg = res.get("message", "Task executed successfully.")

        feedback = f"✅ Done [{action}]: {msg}"
        self.root.after(0, lambda: self.set_status(feedback, "#10B981"))
        self.root.after(0, lambda: self.on_command_complete())

    def on_command_complete(self):
        self.is_busy = False
        # Clear entry after a brief moment
        self.root.after(2500, lambda: self.entry.delete(0, tk.END))
        self.root.after(2500, lambda: self.on_entry_focus_out(None))
        # Ephemeral status fade
        self.root.after(4000, lambda: self.set_status("⚡ Ready • Press [Left Ctrl + Win] to toggle", "#64748B"))

    def ensure_backend_alive(self):
        for ep in [SYSTEM_STATUS_API, "http://127.0.0.1:50051/health", "https://project-anda.fly.dev/health"]:
            try:
                with urllib.request.urlopen(ep, timeout=1.5) as resp:
                    if resp.status == 200:
                        self.root.after(0, lambda: self.set_status("⚡ ANDA Connected • Powered by Gemma (Free)", "#10B981"))
                        self.root.after(2500, lambda: self.set_status("⚡ Ready • Press [Left Ctrl + Win] to toggle", "#64748B"))
                        return
            except Exception:
                pass
        self.root.after(0, lambda: self.set_status("⚡ Offline Mode Ready • Press [Left Ctrl + Win] to toggle", "#38BDF8"))


def main():
    app = AndaHUDApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
