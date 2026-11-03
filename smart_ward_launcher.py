"""
================================================================================
D.B.M.S. SMART WARD ICU - MASTER SUITE LAUNCHER
================================================================================
Central Command Launcher for:
1. D.B.M.S. Smart Ward ICU Monitor (Bedside Patient Telemetry & Vision AI)
2. Emergency Location & Automated Dispatch Center (Hospital Softphone & Calling)
3. Unified Dual-Screen Launch (Side-by-Side Command Center)
4. Hardware IoT Diagnostics & Arduino Firmware Hub
================================================================================
"""

import os
import sys
import time
import json
import webbrowser
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import shared_state
import hardware_bridge

# ==============================================================================
# CLAUDE THEME DESIGN SYSTEM (LIGHT / DARK TUPLES)
# ==============================================================================
COLOR_BG_MAIN = ("#FAF9F5", "#0b0f19")        # Claude Warm Alabaster / Dark Navy
COLOR_BG_CARD = ("#FFFFFF", "#1e293b")        # Pure Crisp White / Slate Card
COLOR_BORDER = ("#E8E6DF", "#334155")         # Warm Stone Border / Slate Border
COLOR_TEXT_MAIN = ("#1C1917", "#F8FAFC")      # Deep Stone Charcoal / Bright White
COLOR_TEXT_MUTED = ("#57534E", "#94A3B8")     # Warm Stone 600 / Cool Slate
COLOR_TEXT_DIM = ("#78716C", "#64748B")       # Subdued Stone 500 / Dim Slate
COLOR_CLAUDE_AMBER = ("#D97706", "#F59E0B")   # Warm Terracotta Amber
COLOR_CLAUDE_HOVER = ("#B45309", "#D97706")   # Deep Terracotta Hover
COLOR_BADGE_AMBER_BG = ("#FEF3C7", "#78350F") # Amber Pill BG
COLOR_STAT_BOX = ("#F5F4EF", "#0f172a")       # Sub-card stat panel
COLOR_NORMAL_TXT = ("#047857", "#34D399")     # Medical Emerald Green
COLOR_NORMAL_BG = ("#ECFDF5", "#064E3B")      # Soft Sage / Dark Pine
COLOR_ALERT_TXT = ("#DC2626", "#F87171")      # Medical Red
COLOR_ALERT_BG = ("#FEF2F2", "#7F1D1D")       # Soft Blush / Deep Crimson

class SuiteLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.state_data = shared_state.load_state()
        self.current_theme = self.state_data.get("ui_theme", "light")

        self.title("D.B.M.S. Smart Ward ICU - Master Suite Launcher")
        self.geometry("980x760")
        self.minsize(880, 680)
        self.configure(fg_color=COLOR_BG_MAIN)

        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        # Set Window Icon if present
        ico_path = os.path.join(SCRIPT_DIR, "SmartWardLauncher.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # Start IoT Hardware Bridge in background to monitor COM3
        self.hw_bridge = hardware_bridge.HardwareBridge.get_instance()
        self.hw_bridge.start()

        # Build UI Layout
        self.create_header()
        self.create_live_status_ribbon()
        self.create_main_launcher_grid()
        self.create_tools_and_credentials_bar()

        # Start background polling loop
        self.after(800, self.periodic_status_poll)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        try:
            self.hw_bridge.stop()
        except Exception:
            pass
        self.destroy()

    # --------------------------------------------------------------------------
    # 1. HEADER SECTION
    # --------------------------------------------------------------------------
    def create_header(self):
        header_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER
        )
        header_card.pack(fill="x", padx=18, pady=(16, 6))

        inner = ctk.CTkFrame(header_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        # Left: Logo & Branding
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")

        logo_lbl = ctk.CTkLabel(
            left,
            text="Ψ",
            font=ctk.CTkFont(family="Inter", size=26, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=18,
            width=44,
            height=44
        )
        logo_lbl.pack(side="left", padx=(0, 12))

        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="D.B.M.S. SMART WARD ICU SUITE",
            font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Autonomous Patient Telemetry, Emergency Dispatch & Softphone Hub",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # Right: Theme Switcher & Clock
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        self.clock_lbl = ctk.CTkLabel(
            right,
            text="--:--:--",
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.clock_lbl.pack(side="left", padx=(0, 10))

        theme_text = "🌙 Dark Mode" if self.current_theme == "light" else "☀️ Claude Light"
        self.btn_theme = ctk.CTkButton(
            right,
            text=theme_text,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            height=30,
            width=100,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self.toggle_theme
        )
        self.btn_theme.pack(side="left")

    # --------------------------------------------------------------------------
    # 2. LIVE SYSTEM TELEMETRY RIBBON
    # --------------------------------------------------------------------------
    def create_live_status_ribbon(self):
        ribbon = ctk.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        ribbon.pack(fill="x", padx=18, pady=(0, 10))

        row = ctk.CTkFrame(ribbon, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=6)

        # Hardware connection badge
        self.badge_hw = ctk.CTkLabel(
            row,
            text="🟡 ARDUINO NODE: SCANNING USB...",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.badge_hw.pack(side="left", padx=(0, 8))

        # Vitals Pill
        self.badge_vitals = ctk.CTkLabel(
            row,
            text="🫀 Vitals: 74 BPM (Normal)",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_STAT_BOX,
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.badge_vitals.pack(side="left", padx=(0, 8))

        # Motion & Fall Pill
        self.badge_motion = ctk.CTkLabel(
            row,
            text="📐 MPU6050: 1.02G [STABLE]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_STAT_BOX,
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.badge_motion.pack(side="left", padx=(0, 8))

        # Home Base GPS
        self.badge_gps = ctk.CTkLabel(
            row,
            text="📍 Jamshedpur, IN [22.8046° N, 86.2029° E]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.badge_gps.pack(side="right")

    # --------------------------------------------------------------------------
    # 3. CORE SUITE APPLICATIONS GRID
    # --------------------------------------------------------------------------
    def create_main_launcher_grid(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=18, pady=0)

        # 3.1 Dual Launch Master Banner (Top Priority)
        unified_box = ctk.CTkFrame(
            container,
            fg_color=COLOR_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER
        )
        unified_box.pack(fill="x", pady=(0, 10))

        u_inner = ctk.CTkFrame(unified_box, fg_color="transparent")
        u_inner.pack(fill="x", padx=16, pady=12)

        u_left = ctk.CTkFrame(u_inner, fg_color="transparent")
        u_left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            u_left,
            text="⚡ UNIFIED DUAL COMMAND LAUNCH (RECOMMENDED)",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(anchor="w")

        ctk.CTkLabel(
            u_left,
            text="Launches both the Bedside ICU Monitor and the Hospital Dispatch Center side-by-side on your screen.",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        top_btn_row = ctk.CTkFrame(u_inner, fg_color="transparent")
        top_btn_row.pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            top_btn_row,
            text="🏡 1-Click Home Care Mode",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            text_color="#FFFFFF",
            height=36,
            corner_radius=8,
            command=lambda: self.launch_monitor(mode="home")
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top_btn_row,
            text="⚡ Dual Command Suite →",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            text_color="#FFFFFF",
            height=36,
            corner_radius=8,
            command=self.launch_both_apps
        ).pack(side="left")

        # 3.2 Individual App Cards (2-Column Grid)
        grid_frame = ctk.CTkFrame(container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        # --- LEFT CARD: Smart Ward ICU Monitor ---
        card_monitor = ctk.CTkFrame(
            grid_frame,
            fg_color=COLOR_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER
        )
        card_monitor.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        m_inner = ctk.CTkFrame(card_monitor, fg_color="transparent")
        m_inner.pack(fill="both", expand=True, padx=16, pady=14)

        # Header
        m_top = ctk.CTkFrame(m_inner, fg_color="transparent")
        m_top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            m_top,
            text="🫀",
            font=ctk.CTkFont(size=22),
            fg_color=COLOR_STAT_BOX,
            corner_radius=8,
            width=36,
            height=36
        ).pack(side="left", padx=(0, 8))

        m_title_box = ctk.CTkFrame(m_top, fg_color="transparent")
        m_title_box.pack(side="left")

        ctk.CTkLabel(
            m_title_box,
            text="Smart Ward ICU Monitor",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        ctk.CTkLabel(
            m_title_box,
            text="Bedside Patient Telemetry Terminal",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

        # Feature bullet points
        m_feats = ctk.CTkFrame(m_inner, fg_color=COLOR_STAT_BOX, corner_radius=8)
        m_feats.pack(fill="both", expand=True, pady=(4, 10))

        features_m = [
            "• Live Sinusoidal P-Q-R-S-T ECG Waveform Canvas",
            "• Optical Pulse Sensor (A0) with anti-bounce filtering",
            "• MPU6050 Accelerometer Fall & Impact detection",
            "• Camera Vision AI presence recognition",
            "• Automated Calling Engine (triggers on cardiac distress)"
        ]
        for f in features_m:
            ctk.CTkLabel(
                m_feats,
                text=f,
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=COLOR_TEXT_MAIN,
                justify="left"
            ).pack(anchor="w", padx=10, pady=2)

        # Action Buttons
        ctk.CTkButton(
            m_inner,
            text="🏡 Launch in Home Usage Mode (Key: 5050-8012-34)",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            text_color="#FFFFFF",
            hover_color=COLOR_CLAUDE_HOVER,
            height=34,
            corner_radius=7,
            command=lambda: self.launch_monitor(mode="home")
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            m_inner,
            text="👤 Launch in Bedside Patient Mode (Key: 1010-8024-55)",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=32,
            corner_radius=7,
            command=lambda: self.launch_monitor(mode="user")
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            m_inner,
            text="🏥 Launch in Hospital Command Mode (Key: 7070-2031-23)",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=32,
            corner_radius=7,
            command=lambda: self.launch_monitor(mode="hospital")
        ).pack(fill="x")

        # --- RIGHT CARD: Emergency Location Dispatcher ---
        card_dispatch = ctk.CTkFrame(
            grid_frame,
            fg_color=COLOR_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER
        )
        card_dispatch.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        d_inner = ctk.CTkFrame(card_dispatch, fg_color="transparent")
        d_inner.pack(fill="both", expand=True, padx=16, pady=14)

        # Header
        d_top = ctk.CTkFrame(d_inner, fg_color="transparent")
        d_top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            d_top,
            text="🚨",
            font=ctk.CTkFont(size=22),
            fg_color=COLOR_STAT_BOX,
            corner_radius=8,
            width=36,
            height=36
        ).pack(side="left", padx=(0, 8))

        d_title_box = ctk.CTkFrame(d_top, fg_color="transparent")
        d_title_box.pack(side="left")

        ctk.CTkLabel(
            d_title_box,
            text="Emergency Location Dispatcher",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        ctk.CTkLabel(
            d_title_box,
            text="Hospital Command & Softphone Console",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

        # Feature bullet points
        d_feats = ctk.CTkFrame(d_inner, fg_color=COLOR_STAT_BOX, corner_radius=8)
        d_feats.pack(fill="both", expand=True, pady=(4, 10))

        features_d = [
            "• Interactive Softphone Console with Live Audio/Voice",
            "• Multi-Tier Automated Voice Calling (Twilio / SIP)",
            "• Hardware Cellular GSM Modem Dialing & SMS Alerts",
            "• NEO-6M Real-time GPS Geofencing & Maps Pinning",
            "• Zero-Configuration Local UDP Intercom on Port 8765"
        ]
        for f in features_d:
            ctk.CTkLabel(
                d_feats,
                text=f,
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=COLOR_TEXT_MAIN,
                justify="left"
            ).pack(anchor="w", padx=10, pady=2)

        # Action Button
        ctk.CTkButton(
            d_inner,
            text="🚨 Launch Dispatch Command Center",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#DC2626",
            text_color="#FFFFFF",
            hover_color="#B91C1C",
            height=36,
            corner_radius=7,
            command=self.launch_dispatcher
        ).pack(fill="x", pady=(10, 0))

    # --------------------------------------------------------------------------
    # 4. TOOLS, CREDENTIALS & HARDWARE SHORTCUTS BAR
    # --------------------------------------------------------------------------
    def create_tools_and_credentials_bar(self):
        bottom_box = ctk.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER
        )
        bottom_box.pack(fill="x", padx=18, pady=(10, 16))

        inner = ctk.CTkFrame(bottom_box, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        # Left: Quick Credentials Cheat-Sheet
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left,
            text="🔑 10-DIGIT SECURITY KEYS CHEAT-SHEET:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(anchor="w")

        cred_text = "🏡 Home Care: 5050-8012-34   |   👤 Patient Bed: 1010-8024-55   |   🏥 Hospital Master: 7070-2031-23   |   COM3 @ 115200"
        ctk.CTkLabel(
            left,
            text=cred_text,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # Right: Quick Utilities Buttons
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        # Open Google Maps
        ctk.CTkButton(
            right,
            text="🌐 Maps Pin",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=30,
            width=90,
            corner_radius=7,
            command=self.open_google_maps
        ).pack(side="left", padx=4)

        # Open Arduino Sketchbook
        ctk.CTkButton(
            right,
            text="📂 Arduino Sketch",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=30,
            width=120,
            corner_radius=7,
            command=self.open_arduino_sketch
        ).pack(side="left", padx=4)

        # Reset Emergency State
        ctk.CTkButton(
            right,
            text="🔄 Reset Alarms",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color="#DC2626",
            hover_color=COLOR_ALERT_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            height=30,
            width=100,
            corner_radius=7,
            command=self.reset_emergency_state
        ).pack(side="left", padx=4)

    # --------------------------------------------------------------------------
    # 5. EXECUTION & PROCESS LAUNCHERS
    # --------------------------------------------------------------------------
    def _execute_app(self, py_script: str, exe_name: str, args=None):
        """Intelligently launches .exe if compiled, or python script via sys.executable"""
        args = args or []
        desktop_exe = os.path.join(os.path.expanduser(r"~\Desktop"), exe_name)
        root_exe = os.path.join(r"D:\Sandbox", exe_name)
        dist_exe = os.path.join(SCRIPT_DIR, "dist", exe_name)
        script_path = os.path.join(SCRIPT_DIR, py_script)

        # If running from python
        if os.path.exists(desktop_exe):
            subprocess.Popen([desktop_exe] + args)
        elif os.path.exists(root_exe):
            subprocess.Popen([root_exe] + args)
        elif os.path.exists(dist_exe):
            subprocess.Popen([dist_exe] + args)
        elif os.path.exists(script_path):
            subprocess.Popen([sys.executable, script_path] + args)
        else:
            messagebox.showerror("Execution Error", f"Could not locate {exe_name} or {py_script}!")

    def launch_monitor(self, mode="home"):
        self._execute_app("smart_ward_monitor.py", "SmartWardMonitor.exe", args=["--mode", mode])

    def launch_dispatcher(self):
        self._execute_app("emergency_location_dispatcher.py", "EmergencyLocationDispatcher.exe")

    def launch_both_apps(self):
        """Launches both applications side-by-side"""
        threading.Thread(target=lambda: (
            self.launch_monitor(mode="hospital"),
            time.sleep(0.6),
            self.launch_dispatcher()
        ), daemon=True).start()

    def open_google_maps(self):
        state = shared_state.load_state()
        loc = state.get("location", {})
        lat = loc.get("lat", 22.8046)
        lng = loc.get("lon", 86.2029)
        url = loc.get("maps_url", f"https://www.google.com/maps?q={lat},{lng}")
        webbrowser.open(url)

    def open_arduino_sketch(self):
        sketch_path = r"C:\Users\Baba\Documents\Arduino\SmartWard_Uno_Telemetry\SmartWard_Uno_Telemetry.ino"
        alt_path = os.path.join(SCRIPT_DIR, "firmware", "SmartWard_Uno_Telemetry", "SmartWard_Uno_Telemetry.ino")
        target = sketch_path if os.path.exists(sketch_path) else alt_path
        if os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                messagebox.showinfo("Arduino Sketch", f"Sketch file located at:\n{target}")
        else:
            messagebox.showinfo("Arduino Sketch", f"Sketch file path:\n{target}")

    def reset_emergency_state(self):
        shared_state.update_emergency(False)
        messagebox.showinfo("Alarms Reset", "All active emergency flags and alarms have been reset to Normal Standby.")

    # --------------------------------------------------------------------------
    # 6. LIVE STATUS BACKGROUND POLLING
    # --------------------------------------------------------------------------
    def periodic_status_poll(self):
        now_str = time.strftime("%H:%M:%S")
        self.clock_lbl.configure(text=now_str)

        # 1. Hardware Bridge Status
        hw_connected = (
            hasattr(self, 'hw_bridge') and
            self.hw_bridge.connected and
            (time.time() - self.hw_bridge.last_packet.get("timestamp", 0) < 4.0)
        )

        if hw_connected:
            pkt = self.hw_bridge.last_packet
            port = pkt.get("port", "COM3")
            bpm = pkt.get("bpm", 0)
            gforce = pkt.get("gforce", 1.0)
            fall = pkt.get("fall", False)
            lat = pkt.get("lat", 22.8046)
            lng = pkt.get("lng", 86.2029)

            self.badge_hw.configure(
                text=f"🟢 ARDUINO NODE: ONLINE ({port} @ 115200)",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.badge_vitals.configure(
                text=f"🫀 Live BPM: {bpm if bpm > 0 else '--'} ({'Normal' if bpm <= 110 else 'Alert'})",
                text_color=COLOR_NORMAL_TXT if bpm <= 110 else "#DC2626"
            )
            self.badge_motion.configure(
                text=f"📐 MPU6050: {gforce:.2f}G [{'FALL!' if fall else 'STABLE'}]",
                text_color="#DC2626" if fall else COLOR_NORMAL_TXT
            )
            self.badge_gps.configure(
                text=f"📍 GPS: {lat:.4f}° N, {lng:.4f}° E"
            )
        else:
            self.badge_hw.configure(
                text="🟡 ARDUINO NODE: SCANNING USB...",
                text_color=COLOR_CLAUDE_AMBER,
                fg_color=COLOR_STAT_BOX
            )

        # 2. Shared State Check
        state = shared_state.load_state()
        if state.get("is_emergency", False):
            self.badge_vitals.configure(
                text=f"🚨 EMERGENCY: {state.get('bpm', 135)} BPM",
                text_color="#DC2626",
                fg_color=COLOR_ALERT_BG
            )

        self.after(1000, self.periodic_status_poll)

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.current_theme = new_theme
        ctk.set_appearance_mode(new_theme)
        shared_state.update_theme(new_theme)

        theme_text = "🌙 Dark Mode" if new_theme == "light" else "☀️ Claude Light"
        self.btn_theme.configure(text=theme_text)

if __name__ == "__main__":
    app = SuiteLauncherApp()
    app.mainloop()
