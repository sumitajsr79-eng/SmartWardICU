"""
D.B.M.S. Smart Ward ICU - Next-Gen Live Telephony & Softphone Calling Console
Features: Real-time Audio Waveform Visualizer, DTMF Tones, Call State Machine,
Speed-Dial Presets, Live Voice Dispatch Transcript, and Claude Light/Dark Theme.
"""

import math
import time
import threading
import tkinter as tk
import customtkinter as ctk

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# Claude Theme Palette
COLOR_BG_MAIN = ("#FAF9F5", "#0b0f19")
COLOR_BG_CARD = ("#FFFFFF", "#1e293b")
COLOR_BORDER = ("#E8E6DF", "#334155")
COLOR_TEXT_MAIN = ("#1C1917", "#F8FAFC")
COLOR_TEXT_MUTED = ("#57534E", "#94A3B8")
COLOR_TEXT_DIM = ("#78716C", "#64748B")
COLOR_CLAUDE_AMBER = ("#D97706", "#F59E0B")
COLOR_CLAUDE_HOVER = ("#B45309", "#D97706")
COLOR_STAT_BOX = ("#F5F4EF", "#0f172a")

# DTMF frequencies for tactile audio feedback
DTMF_TONES = {
    '1': 697, '2': 770, '3': 852,
    '4': 697, '5': 770, '6': 852,
    '7': 697, '8': 770, '9': 852,
    '*': 941, '0': 770, '#': 941
}

def play_tone(freq=800, duration=100):
    """Plays audio frequency tone asynchronously"""
    if HAS_SOUND:
        try:
            threading.Thread(target=lambda: winsound.Beep(int(freq), int(duration)), daemon=True).start()
        except Exception:
            pass

class LiveCallingConsole(ctk.CTkToplevel):
    def __init__(self, master, recipient_name, phone_number, alert_payload=None, on_hangup=None):
        super().__init__(master)

        self.recipient_name = recipient_name or "Emergency Responder"
        self.phone_number = phone_number or "+1 (555) 911-0420"
        self.alert_payload = alert_payload or {}
        self.on_hangup = on_hangup

        # Call state variables
        self.call_state = "DIALING"  # DIALING -> RINGING -> CONNECTED -> ENDED
        self.start_time = None
        self.call_duration_seconds = 0
        self.is_muted = False
        self.is_speaker = True
        self.anim_phase = 0.0
        self.running = True

        # Window Setup
        self.title("D.B.M.S. Emergency Voice Telephony Console")
        self.geometry("520x760")
        self.minsize(480, 700)
        self.configure(fg_color=COLOR_BG_MAIN)
        self.attributes("-topmost", True)

        self.protocol("WM_DELETE_WINDOW", self.hang_up)

        self.create_header()
        self.create_status_and_timer()
        self.create_waveform_visualizer()
        self.create_transcript_display()
        self.create_call_controls()
        self.create_dialpad()

        # Start call sequence animation & state machine
        self.after(50, self.start_call_lifecycle)
        self.after(40, self.animate_audio_wave)
        self.after(1000, self.update_timer)

    # --------------------------------------------------------------------------
    # UI CONSTRUCTION
    # --------------------------------------------------------------------------
    def create_header(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        header.pack(fill="x", padx=16, pady=(16, 6))

        # Avatar / Phone Icon
        avatar = ctk.CTkLabel(
            header, 
            text="📞", 
            font=ctk.CTkFont(size=28), 
            fg_color=COLOR_STAT_BOX, 
            corner_radius=22, 
            width=50, 
            height=50
        )
        avatar.pack(side="left", padx=14, pady=12)

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=10)

        ctk.CTkLabel(
            info,
            text=self.recipient_name,
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        ctk.CTkLabel(
            info,
            text=self.phone_number,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(anchor="w")

        ward = self.alert_payload.get("ward", "Zone-B ICU // Bed 03")
        ctk.CTkLabel(
            info,
            text=f"Distress Origin: {ward}",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

    def create_status_and_timer(self):
        stat_frame = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        stat_frame.pack(fill="x", padx=16, pady=4)

        # Status badge
        self.badge_status = ctk.CTkLabel(
            stat_frame,
            text="● DIALING SECURE TELEPHONY GATEWAY...",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=("#D97706", "#F59E0B"),
            fg_color=("#FEF3C7", "#78350F"),
            corner_radius=8,
            padx=14,
            pady=4
        )
        self.badge_status.pack(side="left", padx=14, pady=10)

        # Stopwatch Call Timer
        self.lbl_timer = ctk.CTkLabel(
            stat_frame,
            text="00:00",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_timer.pack(side="right", padx=16, pady=10)

    def create_waveform_visualizer(self):
        """Audio waveform canvas showing dynamic voice transmission"""
        wave_frame = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        wave_frame.pack(fill="x", padx=16, pady=4)

        top_row = ctk.CTkFrame(wave_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            top_row,
            text="VOICE AUDIO STREAM & TRANSMISSION SPECTRUM",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        self.audio_spec_tag = ctk.CTkLabel(
            top_row,
            text="AUDIO CODEC: OPUS / G.711 (HD VOICE)",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        )
        self.audio_spec_tag.pack(side="right")

        self.wave_canvas = tk.Canvas(
            wave_frame, 
            height=70, 
            bg="#FDFCF7", 
            highlightthickness=1, 
            highlightbackground="#E8E6DF"
        )
        self.wave_canvas.pack(fill="x", padx=14, pady=(2, 10))

    def create_transcript_display(self):
        trans_frame = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        trans_frame.pack(fill="both", expand=True, padx=16, pady=4)

        ctk.CTkLabel(
            trans_frame,
            text="LIVE EMERGENCY DISPATCH TRANSCRIPT (TRANSMITTED AUDIO)",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(8, 4))

        self.txt_transcript = ctk.CTkTextbox(
            trans_frame,
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family="Consolas", size=11),
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.txt_transcript.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.txt_transcript.insert("1.0", "[TELEPHONY INITIALIZED]\nConnecting caller to recipient audio channel...\n")
        self.txt_transcript.configure(state="disabled")

    def append_transcript(self, text):
        self.txt_transcript.configure(state="normal")
        self.txt_transcript.insert("end", f"{text}\n")
        self.txt_transcript.see("end")
        self.txt_transcript.configure(state="disabled")

    def create_call_controls(self):
        ctrls = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        ctrls.pack(fill="x", padx=16, pady=4)

        # Mute Button
        self.btn_mute = ctk.CTkButton(
            ctrls,
            text="🎙️ Mute",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            width=90,
            height=36,
            corner_radius=8,
            command=self.toggle_mute
        )
        self.btn_mute.pack(side="left", padx=10, pady=10)

        # Speaker Button
        self.btn_speaker = ctk.CTkButton(
            ctrls,
            text="🔊 Speaker: ON",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            width=120,
            height=36,
            corner_radius=8,
            command=self.toggle_speaker
        )
        self.btn_speaker.pack(side="left", padx=4, pady=10)

        # Redial Button
        self.btn_redial = ctk.CTkButton(
            ctrls,
            text="🔁 Redial",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            width=90,
            height=36,
            corner_radius=8,
            command=self.redial
        )
        self.btn_redial.pack(side="left", padx=4, pady=10)

        # End Call Button (Prominent Crimson)
        self.btn_hangup = ctk.CTkButton(
            ctrls,
            text="🔴 END CALL",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            width=120,
            height=36,
            corner_radius=8,
            command=self.hang_up
        )
        self.btn_hangup.pack(side="right", padx=10, pady=10)

    def create_dialpad(self):
        """Tactile Softphone Dialpad with real acoustic tone feedback"""
        pad_frame = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        pad_frame.pack(fill="x", padx=16, pady=(4, 14))

        title_row = ctk.CTkFrame(pad_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            title_row,
            text="SOFTPHONE KEYPAD (DTMF TOUCH-TONE)",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        self.btn_toggle_pad = ctk.CTkButton(
            title_row,
            text="Show Dialpad ▼",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            width=90,
            height=20,
            corner_radius=4,
            command=self.toggle_dialpad
        )
        self.btn_toggle_pad.pack(side="right")

        self.grid_container = ctk.CTkFrame(pad_frame, fg_color="transparent")
        self.grid_container.pack(padx=14, pady=(0, 10))

        # 3x4 Grid for touch tones
        keys = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['*', '0', '#']
        ]

        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                btn = ctk.CTkButton(
                    self.grid_container,
                    text=key,
                    font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
                    fg_color=COLOR_STAT_BOX,
                    text_color=COLOR_TEXT_MAIN,
                    hover_color=COLOR_BORDER,
                    border_width=1,
                    border_color=COLOR_BORDER,
                    width=60,
                    height=32,
                    corner_radius=6,
                    command=lambda k=key: self.press_key(k)
                )
                btn.grid(row=r, column=c, padx=5, pady=3)

    def toggle_dialpad(self):
        if self.grid_container.winfo_viewable():
            self.grid_container.pack_forget()
            self.btn_toggle_pad.configure(text="Show Dialpad ▼")
        else:
            self.grid_container.pack(padx=14, pady=(0, 10))
            self.btn_toggle_pad.configure(text="Hide Dialpad ▲")

    def press_key(self, key):
        freq = DTMF_TONES.get(key, 800)
        play_tone(freq, 120)
        self.append_transcript(f"[DTMF TONE TRANSMITTED: '{key}' ({freq} Hz)]")

    # --------------------------------------------------------------------------
    # CALL LIFECYCLE & STATE MACHINE
    # --------------------------------------------------------------------------
    def start_call_lifecycle(self):
        """Simulates realistic telephony call progression: Dialing -> Ringing -> Connected"""
        play_tone(440, 300) # Dial tone chirp
        self.append_transcript(f"[DIALING] Invoking telephony route to {self.phone_number}...")

        # Transition to Ringing after 1.2s
        self.after(1200, self._enter_ringing_state)

    def _enter_ringing_state(self):
        if not self.running or self.call_state == "ENDED":
            return
        self.call_state = "RINGING"
        self.badge_status.configure(
            text="🔔 RINGING RECIPIENT...",
            text_color=("#D97706", "#F59E0B"),
            fg_color=("#FEF3C7", "#78350F")
        )
        self.append_transcript("[RINGBACK] Network ringback signal acknowledged...")
        play_tone(480, 500) # Ringtone pulse

        # Transition to Connected after 2.0s
        self.after(2200, self._enter_connected_state)

    def _enter_connected_state(self):
        if not self.running or self.call_state == "ENDED":
            return
        self.call_state = "CONNECTED"
        self.start_time = time.time()
        self.badge_status.configure(
            text="● CALL CONNECTED // VOICE LIVE",
            text_color=("#047857", "#34D399"),
            fg_color=("#ECFDF5", "#064E3B")
        )
        play_tone(880, 250) # Connection chime
        self.append_transcript("[CALL ANSWERED] Audio channel established. Transmitting medical speech payload...")

        # Generate live emergency clinical announcement transcript
        p_name = self.alert_payload.get("patient_name", "Robert Jenkins")
        ward = self.alert_payload.get("ward", "Zone-B ICU")
        room = self.alert_payload.get("room_bed", "Room 402, Bed 03")
        bpm = self.alert_payload.get("bpm", 135)
        city = self.alert_payload.get("city", "Jamshedpur")
        lat = self.alert_payload.get("lat", 22.8028)
        lon = self.alert_payload.get("lon", 86.1855)

        self.after(800, lambda: self.append_transcript(f'🔊 OPERATOR: "Critical Emergency Alert from D.B.M.S. Smart Ward!"'))
        self.after(1600, lambda: self.append_transcript(f'🔊 OPERATOR: "Patient {p_name} in {ward}, {room} is experiencing critical distress."'))
        self.after(2400, lambda: self.append_transcript(f'🔊 OPERATOR: "Current Heart Rate is {bpm} BPM. Condition: CRITICAL TACHYCARDIA."'))
        self.after(3200, lambda: self.append_transcript(f'🔊 OPERATOR: "Location coordinates: Lat {lat:.4f} N, Lon {lon:.4f} E ({city}). Immediate response required!"'))

    def update_timer(self):
        if not self.running:
            return
        if self.call_state == "CONNECTED" and self.start_time:
            self.call_duration_seconds = int(time.time() - self.start_time)
            mins = self.call_duration_seconds // 60
            secs = self.call_duration_seconds % 60
            self.lbl_timer.configure(text=f"{mins:02d}:{secs:02d}")
        self.after(1000, self.update_timer)

    # --------------------------------------------------------------------------
    # ANIMATED AUDIO WAVEFORM
    # --------------------------------------------------------------------------
    def animate_audio_wave(self):
        if not self.running:
            return
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()

        if w > 20 and h > 20:
            self.wave_canvas.delete("all")
            mid_y = h / 2
            bars = 28
            spacing = w / bars

            self.anim_phase += 0.22

            for i in range(bars):
                x = (i * spacing) + (spacing / 2)
                if self.call_state == "CONNECTED":
                    # Lively speech audio spectrum
                    amplitude = (math.sin(self.anim_phase + (i * 0.45)) * 0.5 + 0.5) * (h * 0.42) + 4
                    bar_color = "#D97706" if not self.is_muted else "#9CA3AF"
                elif self.call_state == "RINGING":
                    # Gentle pulsing ringtone wave
                    amplitude = (math.sin(self.anim_phase * 1.5) * 0.5 + 0.5) * (h * 0.28) + 3
                    bar_color = "#38BDF8"
                elif self.call_state == "DIALING":
                    amplitude = 4 + (math.sin(self.anim_phase + i) * 3)
                    bar_color = "#94A3B8"
                else:
                    amplitude = 2
                    bar_color = "#E5E7EB"

                y1 = mid_y - amplitude
                y2 = mid_y + amplitude
                self.wave_canvas.create_line(x, y1, x, y2, fill=bar_color, width=3.5, capstyle="round")

        self.after(40, self.animate_audio_wave)

    # --------------------------------------------------------------------------
    # CONTROLS INTERACTION
    # --------------------------------------------------------------------------
    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.configure(text="🔇 Muted", fg_color=("#FEE2E2", "#7F1D1D"), text_color="#DC2626")
            self.append_transcript("[MICROPHONE MUTED]")
        else:
            self.btn_mute.configure(text="🎙️ Mute", fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
            self.append_transcript("[MICROPHONE UNMUTED]")

    def toggle_speaker(self):
        self.is_speaker = not self.is_speaker
        status_text = "🔊 Speaker: ON" if self.is_speaker else "🔈 Speaker: OFF"
        self.btn_speaker.configure(text=status_text)
        self.append_transcript(f"[{status_text.upper()}]")

    def redial(self):
        self.call_state = "DIALING"
        self.start_time = None
        self.lbl_timer.configure(text="00:00")
        self.badge_status.configure(
            text="● REDIALING RECIPIENT...",
            text_color=("#D97706", "#F59E0B"),
            fg_color=("#FEF3C7", "#78350F")
        )
        self.append_transcript("\n[REDIAL] Restarting call sequence...")
        self.start_call_lifecycle()

    def hang_up(self):
        self.call_state = "ENDED"
        self.badge_status.configure(
            text="✕ CALL TERMINATED",
            text_color=("#DC2626", "#F87171"),
            fg_color=("#FEF2F2", "#7F1D1D")
        )
        self.append_transcript("[CALL ENDED] Connection terminated by user.")
        play_tone(400, 200)

        if self.on_hangup:
            try:
                self.on_hangup(self.call_duration_seconds)
            except Exception:
                pass

        # Destroy window after a brief 0.5s pause so the user sees "CALL TERMINATED"
        self.after(500, self._safe_destroy)

    def _safe_destroy(self):
        self.running = False
        try:
            self.destroy()
        except Exception:
            pass
