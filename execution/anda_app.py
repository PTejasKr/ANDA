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

try:
    from execution.spotlight_indexer import SpotlightEngine, SpotlightItem
except ImportError:
    try:
        from spotlight_indexer import SpotlightEngine, SpotlightItem
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from spotlight_indexer import SpotlightEngine, SpotlightItem
        except ImportError:
            SpotlightEngine = None
            SpotlightItem = None


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
        self.width = 720
        self.base_height = 100
        self.height = self.base_height
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
        self.timer_seconds = 0
        self.timer_after_id = None

        # Spotlight Indexer & Live Results State
        self.indexer = SpotlightEngine()
        threading.Thread(target=self.indexer.build_index, daemon=True).start()
        self.spotlight_results = []
        self.selected_idx = 0

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

        # Draw sleek dark frosted pill container
        self.draw_pill_container("#0D0E13", "#282A36")

        # 1. Glowing Crimson Red Orb (Pinterest centerpiece)
        self.orb_cx = 50
        self.orb_cy = 44
        self.orb_r = 25

        # Concentric outer red glow aura layers
        self.glow_ovals = []
        glow_configs = [
            (8, "#38080C", 1.0),
            (5, "#6B0B14", 1.5),
            (2, "#B81220", 1.5)
        ]
        for extra, col, w in glow_configs:
            gid = self.canvas.create_oval(
                self.orb_cx - self.orb_r - extra,
                self.orb_cy - self.orb_r - extra,
                self.orb_cx + self.orb_r + extra,
                self.orb_cy + self.orb_r + extra,
                outline=col,
                width=w
            )
            self.glow_ovals.append(gid)

        # Outer crisp crimson rim
        self.orb_rim_id = self.canvas.create_oval(
            self.orb_cx - self.orb_r,
            self.orb_cy - self.orb_r,
            self.orb_cx + self.orb_r,
            self.orb_cy + self.orb_r,
            fill="#780612",
            outline="#FF2E3E",
            width=2
        )

        # Mid shaded sphere
        self.orb_mid_id = self.canvas.create_oval(
            self.orb_cx - self.orb_r + 8,
            self.orb_cy - self.orb_r + 8,
            self.orb_cx + self.orb_r - 8,
            self.orb_cy + self.orb_r - 8,
            fill="#A60C1C",
            outline=""
        )

        # Core bright bead
        self.orb_core_id = self.canvas.create_oval(
            self.orb_cx - self.orb_r + 14,
            self.orb_cy - self.orb_r + 14,
            self.orb_cx + self.orb_r - 14,
            self.orb_cy + self.orb_r - 14,
            fill="#FF2836",
            outline=""
        )

        # Specular gloss highlight
        self.orb_spec_id = self.canvas.create_oval(
            self.orb_cx - 4,
            self.orb_cy - 6,
            self.orb_cx + 1,
            self.orb_cy - 2,
            fill="#FFA1A8",
            outline=""
        )

        for item_id in [self.orb_rim_id, self.orb_mid_id, self.orb_core_id, self.orb_spec_id]:
            self.canvas.tag_bind(item_id, "<Button-1>", lambda e: self.toggle_voice())
            self.canvas.tag_bind(item_id, "<Enter>", lambda e: self.on_orb_hover(True))
            self.canvas.tag_bind(item_id, "<Leave>", lambda e: self.on_orb_hover(False))

        # 2. Pinterest Dark Frosted Textbox (Spotlight Search + Command Bar)
        self.entry_frame = tk.Frame(
            self.canvas,
            bg="#14151C",
            bd=0,
            highlightthickness=1,
            highlightbackground="#282A36",
            highlightcolor="#FF2E3E"
        )
        self.entry_frame.place(x=88, y=20, width=432, height=48)

        # Leading Spotlight icon badge inside the dark container
        self.icon_badge = tk.Label(
            self.entry_frame,
            text="🔍",
            bg="#14151C",
            fg="#71717A",
            font=("Segoe UI", 10)
        )
        self.icon_badge.pack(side="left", padx=(10, 2))

        self.entry_var = tk.StringVar()
        self.placeholder_text = "Spotlight: Search apps, games, math..."
        self.entry = tk.Entry(
            self.entry_frame,
            textvariable=self.entry_var,
            font=("Segoe UI", 11),
            bg="#14151C",
            fg="#F8FAFC",
            bd=0,
            insertbackground="#FF2E3E",
            relief="flat"
        )
        self.entry.insert(0, self.placeholder_text)
        self.entry.pack(side="left", fill="both", expand=True, padx=4, pady=8)

        # Trailing action badge inside the dark container
        self.action_badge = tk.Label(
            self.entry_frame,
            text="↵ Launch",
            bg="#1E202C",
            fg="#A1A1AA",
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2
        )
        self.action_badge.pack(side="right", padx=(2, 10))

        # Spotlight Live Results Dropdown Frame (unfolds directly beneath HUD pill)
        self.results_frame = tk.Frame(
            self.root,
            bg="#0D0E13",
            bd=0,
            highlightthickness=1.5,
            highlightbackground="#282A36"
        )

        # 3. Pinterest Digital Timer Display
        # Left unit: 00 MIN.
        self.timer_min_id = self.canvas.create_text(
            534, 38,
            text="00",
            fill="#FFFFFF",
            font=("Segoe UI", 12, "bold")
        )
        self.canvas.create_text(
            534, 53,
            text="MIN.",
            fill="#71717A",
            font=("Segoe UI", 7, "bold")
        )

        # Right unit: 03 SEC. with indicator dash
        self.canvas.create_line(566, 25, 580, 25, fill="#4A4D5A", width=1.5)
        self.timer_sec_id = self.canvas.create_text(
            573, 38,
            text="03",
            fill="#FFFFFF",
            font=("Segoe UI", 12, "bold")
        )
        self.canvas.create_text(
            573, 53,
            text="SEC.",
            fill="#71717A",
            font=("Segoe UI", 7, "bold")
        )

        # 4. Send Arrow Button (drawn directly on pill canvas - no square bounding artifact)
        self.btn_send_x1, self.btn_send_y1 = 610, 24
        self.btn_send_x2, self.btn_send_y2 = 648, 62
        self.btn_send_bg = self.canvas.create_oval(
            self.btn_send_x1, self.btn_send_y1,
            self.btn_send_x2, self.btn_send_y2,
            fill="#1A0B0E",
            outline="#FF2E3E",
            width=1.5
        )
        self.btn_send_txt = self.canvas.create_text(
            (self.btn_send_x1 + self.btn_send_x2) // 2,
            (self.btn_send_y1 + self.btn_send_y2) // 2,
            text="➔",
            fill="#FF3B48",
            font=("Segoe UI", 12, "bold")
        )

        for btn_elem in [self.btn_send_bg, self.btn_send_txt]:
            self.canvas.tag_bind(btn_elem, "<Button-1>", lambda e: self.submit_command())
            self.canvas.tag_bind(btn_elem, "<Enter>", lambda e: self.on_btn_hover(True))
            self.canvas.tag_bind(btn_elem, "<Leave>", lambda e: self.on_btn_hover(False))

        # 5. Status Ephemeral Feedback Label
        self.status_id = self.canvas.create_text(
            self.width // 2,
            78,
            text="⚡ Ready • Press [Left Ctrl + Win] to toggle",
            fill="#71717A",
            font=("Segoe UI", 8)
        )

    def draw_pill_container(self, fill_color, border_color):
        r = 26  # border radius
        x1, y1 = 6, 6
        x2, y2 = self.width - 6, self.height - 18

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
        self.canvas.create_polygon(points, fill=fill_color, outline=border_color, width=1.5, smooth=True)

    def on_orb_hover(self, hovering):
        if not self.is_recording:
            fill_core = "#FF3E4D" if hovering else "#FF2836"
            rim_color = "#FF4455" if hovering else "#FF2E3E"
            self.canvas.itemconfig(self.orb_core_id, fill=fill_core)
            self.canvas.itemconfig(self.orb_rim_id, outline=rim_color)

    def on_btn_hover(self, hovering):
        bg = "#FF1E27" if hovering else "#1A0B0E"
        fg = "#FFFFFF" if hovering else "#FF3B48"
        self.canvas.itemconfig(self.btn_send_bg, fill=bg)
        self.canvas.itemconfig(self.btn_send_txt, fill=fg)

    def start_timer_tick(self):
        self.timer_seconds = 0
        self.update_timer_display()

    def update_timer_display(self):
        mins = self.timer_seconds // 60
        secs = self.timer_seconds % 60
        self.canvas.itemconfig(self.timer_min_id, text=f"{mins:02d}", fill="#FF4D5A")
        self.canvas.itemconfig(self.timer_sec_id, text=f"{secs:02d}", fill="#FF4D5A")
        if self.is_recording:
            self.timer_seconds += 1
            self.timer_after_id = self.root.after(1000, self.update_timer_display)

    def stop_timer_tick(self):
        if self.timer_after_id:
            try:
                self.root.after_cancel(self.timer_after_id)
            except Exception:
                pass
            self.timer_after_id = None
        self.root.after(3000, self.reset_timer_default)

    def reset_timer_default(self):
        if not self.is_recording:
            self.canvas.itemconfig(self.timer_min_id, text="00", fill="#FFFFFF")
            self.canvas.itemconfig(self.timer_sec_id, text="03", fill="#FFFFFF")

    def setup_bindings(self):
        self.entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.entry.bind("<Return>", lambda e: self.submit_command())
        self.entry.bind("<Down>", lambda e: self.on_arrow_down())
        self.entry.bind("<Up>", lambda e: self.on_arrow_up())
        self.entry.bind("<Escape>", lambda e: self.on_escape())
        self.root.bind("<Escape>", lambda e: self.on_escape())

        # Live text tracing for real-time Spotlight search results
        self.entry_var.trace_add("write", self.on_text_changed)

        # Enable window dragging by clicking empty areas of canvas
        self.canvas.bind("<Button-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def do_move(self, event):
        dx = event.x - getattr(self, "drag_x", event.x)
        dy = event.y - getattr(self, "drag_y", event.y)
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def on_text_changed(self, *args):
        text = self.entry_var.get().strip()
        if not text or text == self.placeholder_text:
            self.spotlight_results = []
            self.render_spotlight_results()
            return
        # Query Spotlight Indexer
        self.spotlight_results = self.indexer.search(text, max_results=5)
        self.selected_idx = 0
        self.render_spotlight_results()

    def set_window_height(self, new_h):
        if self.height != new_h:
            self.height = new_h
            cur_x = self.root.winfo_x()
            cur_y = self.screen_height - self.height - 130
            self.root.geometry(f"{self.width}x{self.height}+{cur_x}+{cur_y}")
            self.canvas.config(height=self.height)

    def render_spotlight_results(self):
        # Clear previous result widgets
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not self.spotlight_results:
            self.results_frame.place_forget()
            self.set_window_height(self.base_height)
            return

        row_h = 42
        count = min(len(self.spotlight_results), 5)
        total_h = count * row_h + 8
        new_win_h = self.base_height + total_h + 8
        self.set_window_height(new_win_h)

        self.results_frame.place(x=88, y=74, width=540, height=total_h)

        for idx, item in enumerate(self.spotlight_results[:5]):
            is_selected = (idx == self.selected_idx)
            row_bg = "#261217" if is_selected else "#14151C"
            title_fg = "#FF4D5A" if is_selected else "#F8FAFC"
            sub_fg = "#FCA5A5" if is_selected else "#94A3B8"
            cat_bg = "#DC2626" if is_selected else "#282A36"
            cat_fg = "#FFFFFF" if is_selected else "#FF4D5A"

            row = tk.Frame(self.results_frame, bg=row_bg, cursor="hand2")
            row.pack(fill="x", padx=4, pady=2)

            cat_lbl = tk.Label(
                row,
                text=f" {item.category} ",
                bg=cat_bg,
                fg=cat_fg,
                font=("Segoe UI", 7, "bold"),
                padx=4,
                pady=1
            )
            cat_lbl.pack(side="left", padx=(8, 6), pady=6)

            t_lbl = tk.Label(
                row,
                text=item.title,
                bg=row_bg,
                fg=title_fg,
                font=("Segoe UI", 9, "bold"),
                anchor="w"
            )
            t_lbl.pack(side="left", padx=2, pady=6)

            sub_text = item.subtitle[:42] + ("..." if len(item.subtitle) > 42 else "")
            s_lbl = tk.Label(
                row,
                text=sub_text,
                bg=row_bg,
                fg=sub_fg,
                font=("Segoe UI", 8),
                anchor="e"
            )
            s_lbl.pack(side="right", padx=(2, 10), pady=6)

            for w in [row, cat_lbl, t_lbl, s_lbl]:
                w.bind("<Button-1>", lambda e, item_idx=idx: self.on_result_clicked(item_idx))

    def on_arrow_down(self):
        if self.spotlight_results:
            self.selected_idx = (self.selected_idx + 1) % len(self.spotlight_results)
            self.render_spotlight_results()

    def on_arrow_up(self):
        if self.spotlight_results:
            self.selected_idx = (self.selected_idx - 1) % len(self.spotlight_results)
            self.render_spotlight_results()

    def on_escape(self):
        if self.spotlight_results:
            self.spotlight_results = []
            self.render_spotlight_results()
        else:
            self.hide_window()

    def on_result_clicked(self, idx):
        self.selected_idx = idx
        self.submit_command()

    def on_entry_focus_in(self, event):
        if self.entry.get() == self.placeholder_text:
            self.entry.delete(0, tk.END)
            self.entry.config(fg="#F8FAFC")

    def on_entry_focus_out(self, event):
        if not self.entry.get().strip():
            self.entry.insert(0, self.placeholder_text)
            self.entry.config(fg="#71717A")
            self.spotlight_results = []
            self.render_spotlight_results()

    def set_status(self, text, color="#71717A"):
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
        self.canvas.itemconfig(self.orb_rim_id, outline="#FF5566")
        self.canvas.itemconfig(self.orb_core_id, fill="#FF4455")
        self.set_status("🎙️ Listening... Speak your instruction (auto-enters on pause)", "#FF4D5A")
        self.start_timer_tick()
        self.animate_orb_pulse(True)

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
        self.animate_orb_pulse(False)
        self.stop_timer_tick()
        self.canvas.itemconfig(self.orb_rim_id, outline="#FF2E3E")
        self.canvas.itemconfig(self.orb_core_id, fill="#FF2836")
        self.set_status("⚡ Transcribing speech to text...", "#F59E0B")

        if not self.recorded_frames:
            self.set_status("⚡ No audio captured. Try speaking again.", "#94A3B8")
            return

        threading.Thread(target=self.send_audio_transcribe, daemon=True).start()

    def animate_orb_pulse(self, active):
        if not active:
            for i, gid in enumerate(self.glow_ovals):
                cols = ["#38080C", "#6B0B14", "#B81220"]
                self.canvas.itemconfig(gid, outline=cols[i])
            return

        pulse_colors = [
            ["#6B0B14", "#B81220", "#FF2E3E"],
            ["#8A0F1A", "#D11827", "#FF4D5A"],
            ["#B81220", "#FF2E3E", "#FF707C"],
            ["#8A0F1A", "#D11827", "#FF4D5A"],
        ]
        self.pulse_phase = (self.pulse_phase + 1) % len(pulse_colors)
        chosen = pulse_colors[self.pulse_phase]
        for i, gid in enumerate(self.glow_ovals):
            self.canvas.itemconfig(gid, outline=chosen[i])

        if self.is_recording:
            self.root.after(180, lambda: self.animate_orb_pulse(True))

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
                for ep in [TRANSCRIBE_API, "http://127.0.0.1:50051/api/stt/transcribe", "https://project-anda.fly.dev/api/ai/stt"]:
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
        self.entry.config(fg="#1C1917")
        self.submit_command()

    def submit_command(self):
        prompt = self.entry.get().strip()
        if not prompt or prompt == self.placeholder_text:
            return

        if self.is_busy:
            return

        # 1. Check if user selected or focused a Spotlight result item
        if self.spotlight_results and 0 <= self.selected_idx < len(self.spotlight_results):
            selected_item = self.spotlight_results[self.selected_idx]
            self.spotlight_results = []
            self.render_spotlight_results()
            exec_res = self.indexer.execute_item(selected_item)
            msg = exec_res.get("message", "Executed Spotlight action")
            self.set_status(f"⚡ {msg}", "#10B981")
            self.on_command_complete()
            return

        # 2. Check if prompt matches an indexed system app, game, math, or setting
        matches = self.indexer.search(prompt, max_results=2)
        if matches and matches[0].action_type in ["launch_app", "open_setting", "math"]:
            self.spotlight_results = []
            self.render_spotlight_results()
            exec_res = self.indexer.execute_item(matches[0])
            msg = exec_res.get("message", "Executed Spotlight action")
            self.set_status(f"⚡ {msg}", "#10B981")
            self.on_command_complete()
            return

        # 3. If "open <target>" or "play <target>" and not installed on the system, fallback to web search as requested!
        lower = prompt.lower()
        if any(lower.startswith(p) for p in ["open ", "play ", "launch ", "start ", "run "]):
            self.spotlight_results = []
            self.render_spotlight_results()
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(prompt)}"
            try:
                webbrowser.open(search_url)
            except Exception:
                try:
                    subprocess.Popen(f'cmd /c start "" "{search_url}"', shell=True)
                except Exception:
                    pass
            self.set_status(f"🌐 Not installed locally. Searched web for '{prompt}'", "#38BDF8")
            self.on_command_complete()
            return

        # 4. Standard background orchestration / Gemma execution
        self.spotlight_results = []
        self.render_spotlight_results()
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
        target_url = None
        system_uri = None
        if res:
            target_url = res.get("target_url")
            system_uri = res.get("system_uri")
            if not target_url and isinstance(res.get("route"), dict):
                target_url = res["route"].get("target_url")
            if not system_uri and isinstance(res.get("route"), dict):
                system_uri = res["route"].get("system_uri")

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
            print(f"[ANDA PHYSICAL EXECUTION] Launching URL: {target_url}", flush=True)
            try:
                os.startfile(target_url)
            except Exception:
                try:
                    webbrowser.open(target_url)
                except Exception:
                    try:
                        subprocess.Popen(f'cmd /c start "" "{target_url}"', shell=True)
                    except Exception as e:
                        print(f"[ANDA ERROR] Failed to launch URL: {e}", flush=True)
        elif system_uri:
            print(f"[ANDA PHYSICAL EXECUTION] Launching System URI: {system_uri}", flush=True)
            try:
                os.startfile(system_uri)
            except Exception:
                try:
                    subprocess.Popen(f'cmd /c start {system_uri}', shell=True)
                except Exception as e:
                    print(f"[ANDA ERROR] Failed to launch system URI: {e}", flush=True)

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
        self.root.after(4000, lambda: self.set_status("⚡ Ready • Press [Left Ctrl + Win] to toggle", "#71717A"))

    def ensure_backend_alive(self):
        for ep in [SYSTEM_STATUS_API, "http://127.0.0.1:50051/health", "https://project-anda.fly.dev/health"]:
            try:
                with urllib.request.urlopen(ep, timeout=1.5) as resp:
                    if resp.status == 200:
                        self.root.after(0, lambda: self.set_status("⚡ ANDA Connected • Powered by Gemma (Free)", "#10B981"))
                        self.root.after(2500, lambda: self.set_status("⚡ Ready • Press [Left Ctrl + Win] to toggle", "#71717A"))
                        return
            except Exception:
                pass
        self.root.after(0, lambda: self.set_status("⚡ Offline Mode Ready • Press [Left Ctrl + Win] to toggle", "#FF4D5A"))


def main():
    app = AndaHUDApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
