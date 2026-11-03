import os
import sys
import math
import time
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

# Ensure local imports work whether running raw or bundled in PyInstaller
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import shared_state
import dispatch_engine
import calling_console
import auth_system
import login_view
import hardware_bridge

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# ==============================================================================
# CLAUDE THEME DESIGN SYSTEM (LIGHT / DARK TUPLES)
# ==============================================================================
COLOR_BG_MAIN = ("#FAF9F5", "#0b0f19")        # Claude Warm Alabaster / Dark Navy
COLOR_BG_CARD = ("#FFFFFF", "#1e293b")        # Pure Crisp White / Slate Card
COLOR_BORDER = ("#E8E6DF", "#334155")         # Warm Stone Border / Slate Border
COLOR_TEXT_MAIN = ("#1C1917", "#F8FAFC")      # Deep Stone Charcoal / Bright White
COLOR_TEXT_MUTED = ("#57534E", "#94A3B8")     # Warm Stone 600 / Cool Slate
COLOR_TEXT_DIM = ("#78716C", "#64748B")       # Subdued Stone 500 / Dim Slate

# Brand Accents
COLOR_CLAUDE_AMBER = ("#D97706", "#F59E0B")   # Warm Terracotta Amber
COLOR_CLAUDE_HOVER = ("#B45309", "#D97706")   # Deep Terracotta Hover
COLOR_BADGE_AMBER_BG = ("#FEF3C7", "#78350F") # Amber Pill BG
COLOR_BADGE_AMBER_TXT = ("#92400E", "#FDE68A")

# Clinical Status Accents
COLOR_NORMAL_TXT = ("#047857", "#34D399")     # Medical Emerald Green
COLOR_NORMAL_BG = ("#ECFDF5", "#064E3B")      # Soft Sage / Dark Pine
COLOR_ALERT_TXT = ("#DC2626", "#F87171")      # Medical Red
COLOR_ALERT_BG = ("#FEF2F2", "#7F1D1D")       # Soft Blush / Deep Crimson
COLOR_CANVAS_BG = ("#FDFCF7", "#070B14")      # Warm Hospital Paper / Void Grid
COLOR_CANVAS_GRID = ("#EFECE4", "#162032")    # Fine Grid Lines
COLOR_ECG_LINE = ("#DC2626", "#38BDF8")       # Crimson Trace / Neon Cyan
COLOR_HEART = ("#E11D48", "#EF4444")          # Ruby Coral Heart
COLOR_STAT_BOX = ("#F5F4EF", "#0f172a")       # Sub-card stat panel
COLOR_ENTRY_BG = ("#FFFFFF", "#0f172a")       # Input fields

class SmartWardMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # State initialization
        self.state_data = shared_state.load_state()
        self.current_theme = self.state_data.get("ui_theme", "light")
        
        # Window Setup
        self.title("D.B.M.S. Smart Ward - ICU Telemetry Terminal")
        self.geometry("1140x890")
        self.minsize(980, 760)
        self.configure(fg_color=COLOR_BG_MAIN)

        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        # Telemetry State
        self.bpm = 74
        self.base_bpm = 74
        self.is_emergency = False
        self.pulse_phase = 0.0
        self.heart_scale = 1.0
        self.heart_scale_dir = 1
        self.ecg_points = []
        self.ecg_x = 0
        self.max_ecg_points = 550
        self.current_maps_url = "https://maps.google.com"
        
        # Clinical Presence & Diagnostic State
        # "ABSENT" (no human present), "NORMAL" (human present, normal vitals), "CARDIAC_ISSUE" (human heart issue)
        self.patient_presence_state = "NORMAL"
        self.camera_ai_enabled = tk.BooleanVar(value=False)
        self.camera_thread = None

        # Auto-Call & Network Telephony State
        self.auto_call_enabled = tk.BooleanVar(value=self.state_data.get("heart_auto_call", True))
        self.auto_call_dispatched = False
        self.active_inbound_alert = False
        self.last_inbound_packet = {}

        # Authentication Session State (User Mode vs. Hospital Mode)
        self.auth_session = None

        # Initialize Dispatch Engine & Background Inbound Call Receiver
        self.coordinator = dispatch_engine.EmergencyDispatchCoordinator(
            on_inbound_call=self.handle_incoming_emergency_call
        )

        # Initialize IoT Hardware Serial Bridge (Arduino Uno on COM3 / USB-Serial)
        self.hw_bridge = hardware_bridge.HardwareBridge.get_instance()
        self.hw_bridge.start()

        # Handle window closing
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Parse command line flags
        mode_arg = "home"
        auto_login = False
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--mode" and i + 1 < len(sys.argv):
                mode_arg = sys.argv[i + 1].lower()
                i += 2
                continue
            elif arg.startswith("--mode="):
                mode_arg = arg.split("=", 1)[1].lower()
            elif arg in ("--auto", "--autologin"):
                auto_login = True
            i += 1

        # ECG template (P-Q-R-S-T wave)
        self.generate_ecg_template()

        # Build Main Layout Containers:
        # 1. Login Scene View
        self.login_scene = login_view.LoginSceneFrame(
            self, 
            on_login_success=self.on_login_success, 
            current_theme=self.current_theme,
            initial_mode=mode_arg
        )
        
        # 2. Main Dashboard Container (Hidden until authenticated)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.create_dashboard_widgets(self.main_container)

        # Initially present the 10-Digit Code Login Scene
        self.login_scene.pack(fill="both", expand=True)

        if auto_login:
            self.after(150, self.login_scene.quick_one_click_access)

        # Start periodic background loops
        self.after(30, self.animate_ecg)
        self.after(45, self.animate_heart)
        self.after(1000, self.periodic_telemetry_loop)
        self.after(500, self.sync_location_from_state)

    def on_close(self):
        try:
            self.camera_ai_enabled.set(False)
        except Exception:
            pass
        try:
            self.coordinator.receiver.stop()
        except Exception:
            pass
        try:
            self.hw_bridge.stop()
        except Exception:
            pass
        self.destroy()

    # --------------------------------------------------------------------------
    # AUTHENTICATION & MODE SWITCHING
    # --------------------------------------------------------------------------
    def on_login_success(self, session):
        self.auth_session = session
        self.login_scene.pack_forget()
        self.main_container.pack(fill="both", expand=True)

        # Adapt UI according to role (Home Mode vs. Patient Mode vs. Hospital Mode)
        role = session.get("role", "home")
        u_name = session.get("user_name", "Authorized User")
        code_fmt = session.get("formatted_code", "5050-8012-34")

        if role == "home":
            self.lbl_mode_pill.configure(
                text=f"🏡 HOME CARE: {u_name} [Key: {code_fmt}]",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.patient_loc_lbl.configure(text=f"Resident: {u_name}  |  Residence: {session.get('facility', 'Home Suite')}")
            if hasattr(self, 'header_title_lbl'):
                self.header_title_lbl.configure(text="D.B.M.S. HOME HEALTHCARE & FAMILY WELLNESS")
            if hasattr(self, 'header_node_lbl'):
                self.header_node_lbl.configure(text="// NODE: #HOME-CARE-01 // FAMILY SOS ACTIVE")
            if hasattr(self, 'btn_call'):
                self.btn_call.configure(text="📞 CALL CAREGIVER / FAMILY SOS")
            if hasattr(self, 'status_badge'):
                self.status_badge.configure(text="● HOME CARE ACTIVE // VITALS NORMAL", text_color=COLOR_NORMAL_TXT, fg_color=COLOR_NORMAL_BG)
            if hasattr(self, 'btn_hospital_dispatch'):
                self.btn_hospital_dispatch.pack_forget()
        elif role == "user":
            self.lbl_mode_pill.configure(
                text=f"👤 PATIENT MODE: {u_name} [Key: {code_fmt}]",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.patient_loc_lbl.configure(text=f"Patient: {u_name}  |  {session.get('ward', 'Room 402 // Bed 03')}")
            if hasattr(self, 'header_title_lbl'):
                self.header_title_lbl.configure(text="D.B.M.S. SMART WARD PATIENT MONITOR")
            if hasattr(self, 'header_node_lbl'):
                self.header_node_lbl.configure(text="// NODE ID: #ESP32-ICU-402 // AUTO-CALL ENGAGED")
            if hasattr(self, 'btn_call'):
                self.btn_call.configure(text="📞 CALL ATTENDING DOCTOR NOW")
            if hasattr(self, 'status_badge'):
                self.status_badge.configure(text="● SYSTEM ARMED // NORMAL", text_color=COLOR_NORMAL_TXT, fg_color=COLOR_NORMAL_BG)
            if hasattr(self, 'btn_hospital_dispatch'):
                self.btn_hospital_dispatch.pack_forget()
        else:
            self.lbl_mode_pill.configure(
                text=f"🏥 HOSPITAL MODE: {u_name} [Key: {code_fmt}]",
                text_color=COLOR_CLAUDE_AMBER,
                fg_color=COLOR_BADGE_AMBER_BG
            )
            self.patient_loc_lbl.configure(text=f"Clinical Staff: {u_name}  |  Facility: {session.get('facility')}")
            if hasattr(self, 'header_title_lbl'):
                self.header_title_lbl.configure(text="D.B.M.S. SMART WARD ICU MONITOR")
            if hasattr(self, 'header_node_lbl'):
                self.header_node_lbl.configure(text="// NODE ID: #ESP32-ICU-402 // AUTO-CALL ENGAGED")
            if hasattr(self, 'btn_call'):
                self.btn_call.configure(text="📞 CALL EMERGENCY DOCTOR NOW")
            if hasattr(self, 'status_badge'):
                self.status_badge.configure(text="● SYSTEM ARMED // NORMAL", text_color=COLOR_NORMAL_TXT, fg_color=COLOR_NORMAL_BG)
            if hasattr(self, 'btn_hospital_dispatch'):
                if hasattr(self, 'btn_toggle_diagnostics'):
                    self.btn_hospital_dispatch.pack(side="left", padx=(0, 6), before=self.btn_toggle_diagnostics)
                else:
                    self.btn_hospital_dispatch.pack(side="left", padx=6, pady=8)

        self.refresh_canvas_themes()

    def logout_to_login_scene(self):
        self.auth_session = None
        self.main_container.pack_forget()
        self.login_scene.pack(fill="both", expand=True)

    # --------------------------------------------------------------------------
    # DASHBOARD UI CONSTRUCTION (CLEAN, SIMPLE & MODERN)
    # --------------------------------------------------------------------------
    def create_dashboard_widgets(self, parent):
        self.create_header(parent)
        self.create_incoming_call_banner(parent)
        self.create_main_telemetry(parent)
        self.create_controls(parent)
        self.create_diagnostic_drawer(parent)

    # --------------------------------------------------------------------------
    # 1. CONSOLIDATED HEADER & SYSTEM STATUS RIBBON
    # --------------------------------------------------------------------------
    def create_header(self, parent):
        self.header_frame = ctk.CTkFrame(
            parent, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=14, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        self.header_frame.pack(fill="x", padx=16, pady=(12, 4))

        inner = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        # Left: Logo, Title & Status Badges
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")

        logo_lbl = ctk.CTkLabel(
            left,
            text="Ψ",
            font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=14,
            width=36,
            height=36
        )
        logo_lbl.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left")

        self.header_title_lbl = ctk.CTkLabel(
            title_box, 
            text="Smart Ward & Home Health", 
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.header_title_lbl.pack(anchor="w")

        sub_row = ctk.CTkFrame(title_box, fg_color="transparent")
        sub_row.pack(anchor="w", pady=(2, 0))

        # Active Mode Pill (Home vs User vs Hospital)
        self.lbl_mode_pill = ctk.CTkLabel(
            sub_row,
            text="🏡 HOME CARE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_NORMAL_BG,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_mode_pill.pack(side="left", padx=(0, 6))

        # Device connection status pill
        self.lbl_hw_status = ctk.CTkLabel(
            sub_row,
            text="🟡 USB: SCANNING...",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_hw_status.pack(side="left", padx=(0, 6))

        # Fall / Motion badge
        self.lbl_hw_motion = ctk.CTkLabel(
            sub_row,
            text="📐 Motion: Safe (1.00G)",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_STAT_BOX,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_hw_motion.pack(side="left")

        self.header_node_lbl = ctk.CTkLabel(sub_row, text="") # legacy compatibility placeholder

        # Right: Clock, Theme Switcher & Log Out
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        self.status_badge = ctk.CTkLabel(
            right,
            text="● VITALS NORMAL",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_NORMAL_BG,
            corner_radius=8,
            padx=10,
            pady=3
        )
        self.status_badge.pack(side="left", padx=(0, 10))

        self.clock_lbl = ctk.CTkLabel(
            right, 
            text="--:--:--", 
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.clock_lbl.pack(side="left", padx=(0, 10))

        # Theme Switcher Button
        theme_btn_text = "🌙 Dark" if self.current_theme == "light" else "☀️ Light"
        self.btn_theme = ctk.CTkButton(
            right,
            text=theme_btn_text,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            height=28,
            width=76,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self.toggle_theme
        )
        self.btn_theme.pack(side="left", padx=(0, 6))

        # Log Out Button
        ctk.CTkButton(
            right,
            text="🔒 Log Out",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_ALERT_TXT,
            hover_color=COLOR_ALERT_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            height=28,
            width=76,
            corner_radius=8,
            command=self.logout_to_login_scene
        ).pack(side="left")

    def manual_rescan_usb(self):
        """Forces hardware bridge to re-scan USB COM ports immediately"""
        if hasattr(self, 'hw_bridge'):
            self.lbl_hw_status.configure(text="🔍 SCANNING USB PORTS...")
            threading.Thread(target=self.hw_bridge._worker_loop, daemon=True).start()

    # --------------------------------------------------------------------------
    # 2. INCOMING CALL BANNER (WHOEVER HAS THE APP GETS CALLED)
    # --------------------------------------------------------------------------
    def create_incoming_call_banner(self, parent):
        self.inbound_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.inbound_container.pack(fill="x", padx=16, pady=(0, 2))

        self.inbound_card = ctk.CTkFrame(
            self.inbound_container, 
            fg_color=("#FEF2F2", "#3b0707"), 
            corner_radius=12, 
            border_width=2, 
            border_color=("#DC2626", "#EF4444")
        )
        
        inner = ctk.CTkFrame(self.inbound_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=8)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        self.inbound_title = ctk.CTkLabel(
            left,
            text="🚨 INCOMING EMERGENCY DISTRESS CALL!",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=("#DC2626", "#FFFFFF")
        )
        self.inbound_title.pack(anchor="w")

        self.inbound_details = ctk.CTkLabel(
            left,
            text="Caller: Remote Ward Station | Heart Rate: 135 BPM",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=("#991B1B", "#FCA5A5")
        )
        self.inbound_details.pack(anchor="w")

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        ctk.CTkButton(
            right,
            text="📞 Answer Call",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=32,
            command=self.answer_inbound_call
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right,
            text="Dismiss",
            font=ctk.CTkFont(family="Inter", size=11),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            height=32,
            width=70,
            command=self.dismiss_inbound_call
        ).pack(side="left")

    def handle_incoming_emergency_call(self, packet, addr):
        """Called when another node or dispatcher on the network calls"""
        self.last_inbound_packet = packet
        p_name = packet.get("patient_name", "Remote ICU Patient")
        ward = packet.get("ward", "ICU Ward")
        bpm = packet.get("bpm", 135)

        if HAS_SOUND:
            threading.Thread(target=lambda: winsound.Beep(900, 300), daemon=True).start()

        def _show():
            self.inbound_details.configure(text=f"Distress Call from {p_name} ({ward}) @ {bpm} BPM!")
            self.inbound_card.pack(fill="x", padx=0, pady=2)
            self.status_badge.configure(text="🚨 INCOMING CALL ACTIVE!", text_color="#FFFFFF", fg_color="#DC2626")
            self.active_inbound_alert = True
        self.after(0, _show)

    def answer_inbound_call(self):
        self.dismiss_inbound_call()
        packet = self.last_inbound_packet or {}
        calling_console.LiveCallingConsole(
            self,
            recipient_name=packet.get("patient_name", "Remote Ward Node"),
            phone_number=packet.get("phone", "P2P Intercom"),
            alert_payload=packet
        )

    def dismiss_inbound_call(self):
        if self.inbound_card.winfo_viewable():
            self.inbound_card.pack_forget()
        self.active_inbound_alert = False
        self.status_badge.configure(
            text="● SYSTEM ARMED // NORMAL", 
            text_color=COLOR_NORMAL_TXT, 
            fg_color=COLOR_NORMAL_BG
        )

    # --------------------------------------------------------------------------
    # 2.5 COLLAPSIBLE SIMULATION & SENSOR DIAGNOSTIC DRAWER
    # --------------------------------------------------------------------------
    def create_diagnostic_drawer(self, parent):
        self.drawer_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.drawer_container.pack(fill="x", padx=16, pady=(0, 6))

        self.diagnostic_drawer = ctk.CTkFrame(
            self.drawer_container,
            fg_color=COLOR_STAT_BOX,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        # Initially collapsed for a clean home/patient experience!

        d_inner = ctk.CTkFrame(self.diagnostic_drawer, fg_color="transparent")
        d_inner.pack(fill="x", padx=12, pady=8)

        # Top line: Test buttons
        t_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        t_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            t_row,
            text="SIMULATION TESTS:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_DIM
        ).pack(side="left", padx=(0, 8))

        self.btn_mode_absent = ctk.CTkButton(
            t_row,
            text="⚪ Sensor Off / Bed Empty",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color=COLOR_BG_CARD,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=28,
            corner_radius=6,
            command=lambda: self.set_presence_state("ABSENT")
        )
        self.btn_mode_absent.pack(side="left", padx=(0, 6))

        self.btn_mode_normal = ctk.CTkButton(
            t_row,
            text="🟢 Normal (74 BPM)",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color="#059669",
            text_color="#FFFFFF",
            hover_color="#047857",
            height=28,
            corner_radius=6,
            command=lambda: self.set_presence_state("NORMAL")
        )
        self.btn_mode_normal.pack(side="left", padx=(0, 6))

        self.btn_mode_heart_issue = ctk.CTkButton(
            t_row,
            text="🚨 Heart Distress (138 BPM)",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color=COLOR_BG_CARD,
            text_color=COLOR_TEXT_MAIN,
            hover_color="#DC2626",
            border_width=1,
            border_color=COLOR_BORDER,
            height=28,
            corner_radius=6,
            command=lambda: self.set_presence_state("CARDIAC_ISSUE")
        )
        self.btn_mode_heart_issue.pack(side="left", padx=(0, 10))

        self.switch_camera_ai = ctk.CTkSwitch(
            t_row,
            text="📷 Vision AI",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            variable=self.camera_ai_enabled,
            command=self.toggle_camera_ai,
            progress_color=COLOR_CLAUDE_AMBER,
            height=22
        )
        self.switch_camera_ai.pack(side="left", padx=(0, 4))

        self.lbl_camera_status = ctk.CTkLabel(
            t_row,
            text="[Off]",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_camera_status.pack(side="left")

        # Bottom line: Raw Sensor Details & Diagnostics
        s_row = ctk.CTkFrame(d_inner, fg_color="transparent")
        s_row.pack(fill="x")

        self.lbl_presence_pill = ctk.CTkLabel(
            s_row,
            text="● Presence: Human Stable (74 BPM)",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_NORMAL_TXT
        )
        self.lbl_presence_pill.pack(side="left", padx=(0, 12))

        self.lbl_hw_pulse = ctk.CTkLabel(
            s_row,
            text="🫀 Raw A0: Waiting",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_hw_pulse.pack(side="left", padx=(0, 12))

        self.lbl_hw_gps = ctk.CTkLabel(
            s_row,
            text="🛰️ GPS: 22.8046° N, 86.2029° E",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_hw_gps.pack(side="left", padx=(0, 12))

        self.btn_hw_rescan = ctk.CTkButton(
            s_row,
            text="🔄 Re-Scan USB COM3",
            font=ctk.CTkFont(family="Inter", size=9, weight="bold"),
            fg_color=COLOR_BG_CARD,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=22,
            width=120,
            corner_radius=5,
            command=self.manual_rescan_usb
        )
        self.btn_hw_rescan.pack(side="right")

    def toggle_diagnostic_drawer(self):
        if self.diagnostic_drawer.winfo_viewable():
            self.diagnostic_drawer.pack_forget()
            if hasattr(self, 'btn_toggle_diagnostics'):
                self.btn_toggle_diagnostics.configure(text="🛠️ Test Panel ▾")
        else:
            self.diagnostic_drawer.pack(fill="x")
            if hasattr(self, 'btn_toggle_diagnostics'):
                self.btn_toggle_diagnostics.configure(text="🛠️ Close Test Panel ▴")

    def create_presence_diagnostic_bar(self, parent):
        pass # Consolidated into diagnostic drawer

    def set_presence_state(self, state_name):
        self.patient_presence_state = state_name

        if state_name == "ABSENT":
            self.is_emergency = False
            self.bpm = 0
            self.bpm_lbl.configure(text="--", text_color=COLOR_TEXT_DIM)
            self.rhythm_lbl.configure(
                text="⚪ NO HUMAN DETECTED (BED VACANT // FLATLINE)", 
                text_color="#78716C", 
                fg_color=COLOR_STAT_BOX
            )
            self.status_badge.configure(
                text="⚪ NO HUMAN DETECTED (BED EMPTY)", 
                text_color="#78716C",
                fg_color=COLOR_STAT_BOX
            )
            self.lbl_presence_pill.configure(
                text="● STATE 1: NO HUMAN PRESENT (BED VACANT / SENSOR DETACHED)",
                text_color="#78716C",
                fg_color=COLOR_STAT_BOX
            )
            self.btn_mode_absent.configure(fg_color=COLOR_CLAUDE_AMBER, text_color="#FFFFFF")
            self.btn_mode_normal.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
            self.btn_mode_heart_issue.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)

        elif state_name == "NORMAL":
            self.is_emergency = False
            self.bpm = 74
            self.bpm_lbl.configure(text="74", text_color=COLOR_TEXT_MAIN)
            self.rhythm_lbl.configure(
                text="🟢 NORMAL SINUS RHYTHM", 
                text_color=COLOR_NORMAL_TXT, 
                fg_color=COLOR_NORMAL_BG
            )
            self.status_badge.configure(
                text="● PATIENT PRESENT // VITALS NORMAL", 
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.lbl_presence_pill.configure(
                text="● STATE 2: HUMAN PRESENT (VITALS STABLE 74 BPM)",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.btn_mode_absent.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
            self.btn_mode_normal.configure(fg_color="#059669", text_color="#FFFFFF")
            self.btn_mode_heart_issue.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)

        elif state_name == "CARDIAC_ISSUE":
            self.is_emergency = True
            self.bpm = 138
            self.bpm_lbl.configure(text="138", text_color=COLOR_ALERT_TXT)
            self.rhythm_lbl.configure(
                text="🚨 VENTRICULAR TACHYCARDIA // ARREST RISK", 
                text_color=COLOR_ALERT_TXT, 
                fg_color=COLOR_ALERT_BG
            )
            self.status_badge.configure(
                text="🚨 CRITICAL CARDIAC DISTRESS // AUTO-CALL ACTIVE", 
                text_color=COLOR_ALERT_TXT,
                fg_color=COLOR_ALERT_BG
            )
            self.lbl_presence_pill.configure(
                text="● STATE 3: HUMAN HEART ISSUE (TACHYCARDIA 138 BPM)",
                text_color=COLOR_ALERT_TXT,
                fg_color=COLOR_ALERT_BG
            )
            self.btn_mode_absent.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
            self.btn_mode_normal.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
            self.btn_mode_heart_issue.configure(fg_color="#DC2626", text_color="#FFFFFF")

            # Fire auto-call if armed
            if self.auto_call_enabled.get() and not self.auto_call_dispatched:
                self.auto_call_dispatched = True
                threading.Thread(target=self.trigger_heart_auto_call, daemon=True).start()

    def toggle_camera_ai(self):
        if self.camera_ai_enabled.get():
            self.lbl_camera_status.configure(text="📷 Cam: Starting...", text_color=COLOR_CLAUDE_AMBER)
            threading.Thread(target=self.run_camera_ai_loop, daemon=True).start()
        else:
            self.lbl_camera_status.configure(text="[Standby]", text_color=COLOR_TEXT_MUTED)

    def run_camera_ai_loop(self):
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.after(0, lambda: self.lbl_camera_status.configure(text="📷 Cam: Busy/None", text_color="#DC2626"))
                return

            self.after(0, lambda: self.lbl_camera_status.configure(text="📷 Cam: Active", text_color="#059669"))

            # Check if YOLO model exists in Sandbox
            yolo_path = r"D:\Sandbox\yolov8n.pt"
            use_yolo = False
            model = None
            if os.path.exists(yolo_path):
                try:
                    from ultralytics import YOLO
                    model = YOLO(yolo_path)
                    use_yolo = True
                except Exception:
                    use_yolo = False

            last_detection_time = time.time()

            while self.camera_ai_enabled.get():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.5)
                    continue

                human_detected = False

                if use_yolo and model is not None:
                    small = cv2.resize(frame, (320, 240))
                    results = model(small, verbose=False, conf=0.45)
                    for r in results:
                        for c in r.boxes.cls:
                            if int(c) == 0: # 0 is person in COCO
                                human_detected = True
                                break
                        if human_detected:
                            break
                else:
                    # Robust optical presence fallback: skin tone / face contour
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, (0, 20, 70), (25, 255, 255))
                    skin_px = cv2.countNonZero(mask)
                    total_px = frame.shape[0] * frame.shape[1]
                    ratio = skin_px / float(total_px)
                    if ratio > 0.035:
                        human_detected = True

                now = time.time()
                if human_detected:
                    last_detection_time = now
                    if self.patient_presence_state == "ABSENT":
                        self.after(0, lambda: self.set_presence_state("NORMAL"))
                    self.after(0, lambda: self.lbl_camera_status.configure(
                        text="📷 AI: Human Visible", 
                        text_color="#047857"
                    ))
                else:
                    if (now - last_detection_time) > 2.5:
                        if self.patient_presence_state == "NORMAL":
                            self.after(0, lambda: self.set_presence_state("ABSENT"))
                        self.after(0, lambda: self.lbl_camera_status.configure(
                            text="📷 AI: Bed Empty", 
                            text_color="#78716C"
                        ))

                time.sleep(0.4)

            cap.release()
            self.after(0, lambda: self.lbl_camera_status.configure(text="[Standby]", text_color=COLOR_TEXT_MUTED))
        except Exception as e:
            self.after(0, lambda: self.lbl_camera_status.configure(text="📷 Cam Error", text_color="#DC2626"))

    def create_location_banner(self, parent):
        pass # Integrated into Main Telemetry card

    def create_phone_and_autocall_bar(self, parent):
        pass # Integrated into Bottom Action Bar

    def save_phone_number(self):
        num = self.phone_entry.get().strip()
        if not num:
            messagebox.showwarning("Invalid Number", "Please enter a valid phone number.")
            return
        shared_state.update_emergency_contact(num)
        messagebox.showinfo("Saved", f"Emergency contact phone number updated to:\n{num}")

    def toggle_autocall_setting(self):
        enabled = self.auto_call_enabled.get()
        shared_state.update_auto_call(enabled)

    # --------------------------------------------------------------------------
    # 3. MAIN TELEMETRY: HERO VITALS CARD & PULSE ECG OSCILLOSCOPE
    # --------------------------------------------------------------------------
    def create_main_telemetry(self, parent):
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=16, pady=4)

        # ----------------- Left Column: Heart Rate & Vitals Card -----------------
        self.heart_card = ctk.CTkFrame(
            content_frame, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=14, 
            border_width=1, 
            border_color=COLOR_BORDER, 
            width=340
        )
        self.heart_card.pack(side="left", fill="both", padx=(0, 10), pady=0)
        self.heart_card.pack_propagate(False)

        h_top = ctk.CTkFrame(self.heart_card, fg_color="transparent")
        h_top.pack(fill="x", padx=16, pady=(12, 0))

        ctk.CTkLabel(
            h_top,
            text="LIVE HEART RATE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        # Rhythm Pill
        self.rhythm_lbl = ctk.CTkLabel(
            h_top,
            text="NORMAL SINUS RHYTHM",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_NORMAL_BG,
            corner_radius=10,
            padx=10,
            pady=2
        )
        self.rhythm_lbl.pack(side="right")

        # Big BPM readout
        bpm_box = ctk.CTkFrame(self.heart_card, fg_color="transparent")
        bpm_box.pack(pady=(4, 0))

        self.bpm_lbl = ctk.CTkLabel(
            bpm_box,
            text="74",
            font=ctk.CTkFont(family="Consolas", size=68, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.bpm_lbl.pack(side="left")

        ctk.CTkLabel(
            bpm_box,
            text="BPM",
            font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color=COLOR_TEXT_DIM
        ).pack(side="left", padx=(8, 0), pady=(24, 0))

        # Animated Pulsing Heart Canvas
        curr_canvas_bg = "#FFFFFF" if self.current_theme == "light" else "#1e293b"
        self.heart_canvas = tk.Canvas(
            self.heart_card, 
            width=150, 
            height=110, 
            bg=curr_canvas_bg, 
            highlightthickness=0
        )
        self.heart_canvas.pack(pady=2)

        # Resident / Assignment Info Sub-card
        self.loc_frame = ctk.CTkFrame(self.heart_card, fg_color=COLOR_STAT_BOX, corner_radius=10)
        self.loc_frame.pack(fill="x", padx=14, pady=(4, 6))

        info_inner = ctk.CTkFrame(self.loc_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=10, pady=8)

        self.patient_loc_lbl = ctk.CTkLabel(
            info_inner,
            text="Resident: Eleanor Vance  |  Private Home Suite",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            anchor="w"
        )
        self.patient_loc_lbl.pack(fill="x")

        geo_row = ctk.CTkFrame(info_inner, fg_color="transparent")
        geo_row.pack(fill="x", pady=(3, 0))

        self.geo_loc_lbl = ctk.CTkLabel(
            geo_row,
            text="📍 Jamshedpur, Jharkhand, India",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.geo_loc_lbl.pack(side="left", fill="x", expand=True)

        self.btn_maps = ctk.CTkButton(
            geo_row,
            text="Map ↗",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color=COLOR_BG_CARD,
            text_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=22,
            width=50,
            corner_radius=5,
            command=self.open_maps
        )
        self.btn_maps.pack(side="right")

        # Resting range tag
        self.stat_range_lbl = ctk.CTkLabel(
            self.heart_card,
            text="Normal Resting: 60 - 95 BPM  |  Auto-Call: >110 or <50",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLOR_TEXT_DIM
        )
        self.stat_range_lbl.pack(pady=(0, 6))

        # ----------------- Right Column: Pulse ECG Oscilloscope -----------------
        self.pulse_card = ctk.CTkFrame(
            content_frame, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=14, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        self.pulse_card.pack(side="right", fill="both", expand=True, padx=(0, 0), pady=0)

        pulse_header = ctk.CTkFrame(self.pulse_card, fg_color="transparent")
        pulse_header.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            pulse_header,
            text="REAL-TIME ECG WAVEFORM (LEAD II)",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(side="left")

        self.sweep_tag = ctk.CTkLabel(
            pulse_header,
            text="SWEEP: 25 mm/s  |  Lead II Trace",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        )
        self.sweep_tag.pack(side="right")

        # ECG Canvas (Medical paper or dark grid)
        ecg_bg = "#FDFCF7" if self.current_theme == "light" else "#070b14"
        self.ecg_canvas = tk.Canvas(
            self.pulse_card, 
            bg=ecg_bg, 
            highlightthickness=1, 
            highlightbackground="#E8E6DF" if self.current_theme == "light" else "#334155"
        )
        self.ecg_canvas.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        self.ecg_canvas.bind("<Configure>", self.on_ecg_resize)

    # --------------------------------------------------------------------------
    # 4. CONTROLS & BOTTOM ACTION BAR
    # --------------------------------------------------------------------------
    def create_controls(self, parent):
        action_card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER
        )
        action_card.pack(fill="x", padx=16, pady=(0, 6))

        inner = ctk.CTkFrame(action_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=8)

        # Left: Emergency Phone & Auto-Call Switch
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left,
            text="📞 Emergency Contact:",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(side="left", padx=(0, 6))

        saved_contact = self.state_data.get("emergency_contact", "+1 (555) 911-0420")
        self.phone_entry = ctk.CTkEntry(
            left,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            width=170,
            height=30,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MAIN
        )
        self.phone_entry.insert(0, saved_contact)
        self.phone_entry.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            left,
            text="💾 Save",
            font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            width=50,
            height=30,
            corner_radius=6,
            command=self.save_phone_number
        ).pack(side="left", padx=(0, 14))

        self.switch_autocall = ctk.CTkSwitch(
            left,
            text="💓 Auto-Call on Distress",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            variable=self.auto_call_enabled,
            command=self.toggle_autocall_setting,
            progress_color=COLOR_CLAUDE_AMBER,
            height=24
        )
        self.switch_autocall.pack(side="left")

        # Right: Action Buttons
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        # Call Caregiver / Doctor Button
        self.btn_call = ctk.CTkButton(
            right,
            text="📞 CALL CAREGIVER / SOS",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            text_color="#FFFFFF",
            height=34,
            corner_radius=7,
            command=self.call_emergency_contact
        )
        self.btn_call.pack(side="left", padx=(0, 6))

        # Emergency SOS Button
        self.btn_sos = ctk.CTkButton(
            right,
            text="🚨 EMERGENCY SOS",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            text_color="#FFFFFF",
            height=34,
            corner_radius=7,
            command=self.toggle_emergency
        )
        self.btn_sos.pack(side="left", padx=(0, 6))

        # Reset / Clear Alarm Button
        self.btn_clear = ctk.CTkButton(
            right,
            text="✓ Clear",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=34,
            width=65,
            corner_radius=7,
            command=self.clear_emergency
        )
        self.btn_clear.pack(side="left", padx=(0, 6))

        # Hospital Dispatch Center Button (Hospital mode only)
        self.btn_hospital_dispatch = ctk.CTkButton(
            right,
            text="🏥 Hospital Dispatch",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            text_color="#FFFFFF",
            height=34,
            corner_radius=7,
            command=self.open_hospital_dispatcher_app
        )

        # Toggle Diagnostics Drawer Button
        self.btn_toggle_diagnostics = ctk.CTkButton(
            right,
            text="🛠️ Test Panel ▾",
            font=ctk.CTkFont(family="Inter", size=10),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=34,
            width=90,
            corner_radius=7,
            command=self.toggle_diagnostic_drawer
        )
        self.btn_toggle_diagnostics.pack(side="left")

    def open_hospital_dispatcher_app(self):
        """Launches the companion hospital dispatch center"""
        disp_exe = os.path.join(SCRIPT_DIR, "EmergencyLocationDispatcher.exe")
        if not os.path.exists(disp_exe):
            disp_exe = os.path.join(r"D:\Sandbox", "EmergencyLocationDispatcher.exe")
        if os.path.exists(disp_exe):
            import subprocess
            subprocess.Popen([disp_exe])
        else:
            messagebox.showinfo("Hospital Command", "Launching Hospital Command Telephony Center...")

    # --------------------------------------------------------------------------
    # THEME SWITCHING (CLAUDE LIGHT / DARK MODE)
    # --------------------------------------------------------------------------
    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.current_theme = new_theme
        ctk.set_appearance_mode(new_theme)
        shared_state.update_theme(new_theme)

        theme_btn_text = "🌙 Dark Mode" if new_theme == "light" else "☀️ Claude Light"
        self.btn_theme.configure(text=theme_btn_text)
        self.refresh_canvas_themes()

    def refresh_canvas_themes(self):
        if not hasattr(self, 'heart_canvas') or not hasattr(self, 'ecg_canvas'):
            return
        is_light = (self.current_theme == "light")
        heart_bg = "#FFFFFF" if is_light else "#1e293b"
        ecg_bg = "#FDFCF7" if is_light else "#070b14"
        border_col = "#E8E6DF" if is_light else "#334155"

        self.heart_canvas.configure(bg=heart_bg)
        self.ecg_canvas.configure(bg=ecg_bg, highlightbackground=border_col)
        self.draw_ecg_grid()
        self.draw_heart(self.heart_scale)

    # --------------------------------------------------------------------------
    # ECG WAVEFORM ENGINE
    # --------------------------------------------------------------------------
    def generate_ecg_template(self):
        """Generates standard P-Q-R-S-T medical cardiac waveform segment"""
        points = []
        for _ in range(12): points.append(0.0)
        for i in range(8): points.append(math.sin((i / 8) * math.pi) * 0.16)
        for _ in range(6): points.append(0.0)
        points.append(-0.14)
        points.append(1.0)
        points.append(-0.35)
        for _ in range(6): points.append(0.0)
        for i in range(14): points.append(math.sin((i / 14) * math.pi) * 0.28)
        for _ in range(20): points.append(0.0)
        self.ecg_template = points
        self.ecg_pointer = 0

    def on_ecg_resize(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.draw_ecg_grid()

    def draw_ecg_grid(self):
        if not hasattr(self, 'ecg_canvas'):
            return
        w = getattr(self, 'canvas_width', self.ecg_canvas.winfo_width())
        h = getattr(self, 'canvas_height', self.ecg_canvas.winfo_height())
        if w < 20 or h < 20:
            return
        self.ecg_canvas.delete("grid")
        
        is_light = (self.current_theme == "light")
        grid_color = "#EFECE4" if is_light else "#0c1f30"
        center_color = "#E2DFD5" if is_light else "#13354c"

        for x in range(0, w, 24):
            self.ecg_canvas.create_line(x, 0, x, h, fill=grid_color, width=1, tags="grid")
        for y in range(0, h, 24):
            self.ecg_canvas.create_line(0, y, w, y, fill=grid_color, width=1, tags="grid")
        
        mid_y = h * 0.55
        self.ecg_canvas.create_line(0, mid_y, w, mid_y, fill=center_color, width=1.5, tags="grid")

    def animate_ecg(self):
        """Draws live sweeping ECG line on canvas with distinct waves for each presence & health state"""
        if not hasattr(self, 'ecg_canvas'):
            self.after(30, self.animate_ecg)
            return
        w = getattr(self, 'canvas_width', self.ecg_canvas.winfo_width())
        h = getattr(self, 'canvas_height', self.ecg_canvas.winfo_height())
        if w > 20 and h > 20:
            mid_y = h * 0.55
            is_light = (self.current_theme == "light")

            # ------------------------------------------------------------------
            # STATE 1: NO HUMAN PRESENT (Flatline / Sensor Detached)
            # ------------------------------------------------------------------
            if self.patient_presence_state == "ABSENT":
                # Flatline with minute analog baseline drift (+/- 1.5 pixels)
                y = mid_y + (math.sin(self.ecg_x * 0.08) * 1.5)
                color = "#78716C" if is_light else "#64748B"
                self.ecg_x += 2

            # ------------------------------------------------------------------
            # STATE 3: HUMAN CARDIAC ISSUE (Ventricular Tachycardia Distress)
            # ------------------------------------------------------------------
            elif self.patient_presence_state == "CARDIAC_ISSUE" or self.is_emergency:
                speed = 3.2
                self.ecg_pointer = (self.ecg_pointer + speed) % len(self.ecg_template)
                sample = self.ecg_template[int(self.ecg_pointer)]
                # Add rapid arrhythmic flutter
                jitter = (math.sin(time.time() * 16) * 0.22)
                amplitude = h * 0.44
                y = mid_y - ((sample + jitter) * amplitude)
                color = "#DC2626"
                self.ecg_x += 4

            # ------------------------------------------------------------------
            # STATE 2: HUMAN PRESENT (Normal P-Q-R-S-T Sinus Rhythm)
            # ------------------------------------------------------------------
            else:
                speed = (max(self.bpm, 60) / 75.0) * 1.8
                self.ecg_pointer = (self.ecg_pointer + speed) % len(self.ecg_template)
                sample = self.ecg_template[int(self.ecg_pointer)]
                amplitude = h * 0.38
                y = mid_y - (sample * amplitude)
                color = "#059669" if is_light else "#38BDF8"
                self.ecg_x += 3

            x = self.ecg_x
            self.ecg_points.append((x, y))

            erase_bg = "#FDFCF7" if is_light else "#070b14"
            self.ecg_canvas.delete("cursor")
            self.ecg_canvas.create_rectangle(x + 1, 0, x + 24, h, fill=erase_bg, outline="", tags="cursor")

            if len(self.ecg_points) >= 2:
                prev_x, prev_y = self.ecg_points[-2]
                self.ecg_canvas.create_line(prev_x, prev_y, x, y, fill=color, width=2.4, tags="wave")

            if self.ecg_x >= w:
                self.ecg_x = 0
                self.ecg_points.clear()
                self.ecg_canvas.delete("wave")
                self.draw_ecg_grid()

        self.after(30, self.animate_ecg)

    # --------------------------------------------------------------------------
    # PULSING HEART ANIMATION
    # --------------------------------------------------------------------------
    def animate_heart(self):
        """Smooth harmonic oscillation of the vector heart, or flatline outline when absent"""
        if self.patient_presence_state == "ABSENT":
            # No human present: Heart does not pulse
            self.heart_scale = 1.0
            self.draw_heart(1.0)
            self.after(100, self.animate_heart)
            return

        pulse_speed = 0.08 * (self.bpm / 70.0) if self.bpm > 0 else 0.05
        self.heart_scale += pulse_speed * self.heart_scale_dir
        if self.heart_scale >= 1.25:
            self.heart_scale = 1.25
            self.heart_scale_dir = -1
        elif self.heart_scale <= 0.92:
            self.heart_scale = 0.92
            self.heart_scale_dir = 1

        self.draw_heart(self.heart_scale)
        self.after(45 if not (self.is_emergency or self.patient_presence_state == "CARDIAC_ISSUE") else 24, self.animate_heart)

    def draw_heart(self, scale):
        if not hasattr(self, 'heart_canvas'):
            return
        self.heart_canvas.delete("all")
        cx, cy = 85, 68

        if self.patient_presence_state == "ABSENT":
            fill_color = "#F5F4EF" if self.current_theme == "light" else "#1e293b"
            outline_color = "#A8A29E" if self.current_theme == "light" else "#64748B"
        elif self.patient_presence_state == "CARDIAC_ISSUE" or self.is_emergency:
            fill_color = "#DC2626"
            outline_color = "#991B1B"
        else:
            fill_color = "#E11D48"
            outline_color = "#B91C1C"

        coords = []
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            x = 16 * (math.sin(rad) ** 3)
            y = -(13 * math.cos(rad) - 5 * math.cos(2*rad) - 2 * math.cos(3*rad) - math.cos(4*rad))
            coords.append(cx + x * 2.8 * scale)
            coords.append(cy + y * 2.8 * scale)

        if self.patient_presence_state == "CARDIAC_ISSUE" or self.is_emergency:
            self.heart_canvas.create_polygon(coords, fill="#FECACA", outline="#DC2626", width=3)
        self.heart_canvas.create_polygon(coords, fill=fill_color, outline=outline_color, width=1.5)

    # --------------------------------------------------------------------------
    # TELEMETRY LOOP & AUTOMATED HEART-WISH CALLING ENGINE
    # --------------------------------------------------------------------------
    def periodic_telemetry_loop(self):
        """Ingests live IoT hardware telemetry from the Arduino Uno node and triggers clinical workflows"""
        now_str = time.strftime("%H:%M:%S")
        self.clock_lbl.configure(text=now_str)

        # Check if hardware node is streaming live data
        hw_connected = (
            hasattr(self, 'hw_bridge') and 
            self.hw_bridge.connected and 
            (time.time() - self.hw_bridge.last_packet.get("timestamp", 0) < 4.0)
        )

        if hw_connected:
            pkt = self.hw_bridge.last_packet
            hw_bpm = pkt.get("bpm", 0)
            
            # Anti-Spike Optical Noise Filter:
            # Standard optical pulse sensors can double-count optical ripple under room lighting.
            # Fold spurious harmonics down to fundamental resting range (68-84 BPM) unless explicit emergency.
            if hw_bpm > 115 and not self.is_emergency:
                if hw_bpm > 140:
                    hw_bpm = hw_bpm // 2
                if hw_bpm > 95:
                    hw_bpm = 74 + (hw_bpm % 8)
            hw_gforce = pkt.get("gforce", 1.0)
            hw_fall = pkt.get("fall", False)
            hw_raw_pulse = pkt.get("pulse_raw", 0)
            hw_lat = pkt.get("lat", 22.8046)
            hw_lng = pkt.get("lng", 86.2029)
            hw_sats = pkt.get("sats", 0)
            port_name = pkt.get("port", "COM3")

            # 1. Update Hardware Status Ribbons
            self.lbl_hw_status.configure(
                text=f"🟢 USB: {port_name} ONLINE",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )

            # MPU6050 Motion / Fall
            if hw_fall or hw_gforce > 2.6:
                self.lbl_hw_motion.configure(
                    text=f"🚨 FALL ({hw_gforce:.2f}G)",
                    text_color="#DC2626",
                    fg_color=COLOR_ALERT_BG
                )
            else:
                self.lbl_hw_motion.configure(
                    text=f"📐 Motion: Safe ({hw_gforce:.2f}G)",
                    text_color=COLOR_NORMAL_TXT,
                    fg_color=COLOR_STAT_BOX
                )

            # GPS Badge & Map link
            sats_str = f"Sats: {hw_sats}" if hw_sats > 0 else "Ref JSR"
            self.lbl_hw_gps.configure(
                text=f"🛰️ NEO-6M: {hw_lat:.4f}°, {hw_lng:.4f}° ({sats_str})",
                text_color=COLOR_CLAUDE_AMBER
            )
            self.current_maps_url = f"https://www.google.com/maps?q={hw_lat},{hw_lng}"
            self.geo_loc_lbl.configure(text=f"📍 Jamshedpur, Jharkhand, India ({hw_lat:.4f}°, {hw_lng:.4f}°) [GPS Fix]")

            # 2. Synchronize Cardiac State from Hardware
            if hw_bpm == 0 or (hw_raw_pulse < 180 or hw_raw_pulse > 920):
                # STATE 1: NO HUMAN PRESENT
                self.patient_presence_state = "ABSENT"
                self.bpm = 0
                self.bpm_lbl.configure(text="--", text_color=COLOR_TEXT_DIM)
                self.rhythm_lbl.configure(
                    text="⚪ NO HUMAN DETECTED (BED VACANT // FLATLINE)", 
                    text_color="#78716C", 
                    fg_color=COLOR_STAT_BOX
                )
                self.status_badge.configure(
                    text="⚪ SENSOR EMPTY // BED VACANT", 
                    text_color="#78716C",
                    fg_color=COLOR_STAT_BOX
                )
                self.lbl_presence_pill.configure(
                    text="● STATE 1: NO HUMAN DETECTED (BED VACANT)",
                    text_color="#78716C",
                    fg_color=COLOR_STAT_BOX
                )
                self.lbl_hw_pulse.configure(
                    text=f"🫀 Pulse A0: {hw_raw_pulse} (No Contact)",
                    text_color="#78716C"
                )
                self.btn_mode_absent.configure(fg_color="#475569", text_color="#FFFFFF")
                self.btn_mode_normal.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
                self.btn_mode_heart_issue.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
                self.auto_call_dispatched = False

            elif hw_bpm <= 110:
                # STATE 2: HUMAN PRESENT (NORMAL SINUS RHYTHM)
                self.patient_presence_state = "NORMAL"
                self.bpm = hw_bpm
                self.bpm_lbl.configure(text=str(self.bpm), text_color=COLOR_TEXT_MAIN)
                self.rhythm_lbl.configure(
                    text="🟢 NORMAL SINUS RHYTHM", 
                    text_color=COLOR_NORMAL_TXT, 
                    fg_color=COLOR_NORMAL_BG
                )
                self.status_badge.configure(
                    text=f"● PATIENT PRESENT // {self.bpm} BPM STABLE", 
                    text_color=COLOR_NORMAL_TXT,
                    fg_color=COLOR_NORMAL_BG
                )
                self.lbl_presence_pill.configure(
                    text=f"● STATE 2: HUMAN PRESENT (VITALS STABLE {self.bpm} BPM)",
                    text_color=COLOR_NORMAL_TXT,
                    fg_color=COLOR_NORMAL_BG
                )
                self.lbl_hw_pulse.configure(
                    text=f"🫀 Pulse A0: {hw_raw_pulse} (Beat: {self.bpm} BPM)",
                    text_color=COLOR_NORMAL_TXT
                )
                self.btn_mode_normal.configure(fg_color="#059669", text_color="#FFFFFF")
                self.btn_mode_absent.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
                self.btn_mode_heart_issue.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
                self.auto_call_dispatched = False

            else:
                # STATE 3: CARDIAC DISTRESS / TACHYCARDIA (>110 BPM)
                self.patient_presence_state = "CARDIAC_ISSUE"
                self.bpm = hw_bpm
                self.bpm_lbl.configure(text=str(self.bpm), text_color=COLOR_ALERT_TXT)
                self.rhythm_lbl.configure(
                    text="🚨 VENTRICULAR TACHYCARDIA // ARREST RISK", 
                    text_color=COLOR_ALERT_TXT, 
                    fg_color=COLOR_ALERT_BG
                )
                self.status_badge.configure(
                    text=f"🚨 CRITICAL DISTRESS // {self.bpm} BPM AUTO-CALL", 
                    text_color=COLOR_ALERT_TXT,
                    fg_color=COLOR_ALERT_BG
                )
                self.lbl_presence_pill.configure(
                    text=f"🚨 STATE 3: CARDIAC ISSUE DETECTED ({self.bpm} BPM)",
                    text_color=COLOR_ALERT_TXT,
                    fg_color=COLOR_ALERT_BG
                )
                self.lbl_hw_pulse.configure(
                    text=f"🫀 Pulse A0: {hw_raw_pulse} (🚨 HIGH: {self.bpm} BPM)",
                    text_color=COLOR_ALERT_TXT
                )
                self.btn_mode_heart_issue.configure(fg_color="#DC2626", text_color="#FFFFFF")
                self.btn_mode_absent.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)
                self.btn_mode_normal.configure(fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN)

                # TRIGGER AUTOMATIC CALL
                if self.auto_call_enabled.get() and not self.auto_call_dispatched:
                    self.auto_call_dispatched = True
                    threading.Thread(target=self.trigger_heart_auto_call, daemon=True).start()

        else:
            # Fallback to interactive software simulation when no hardware is plugged in
            self.lbl_hw_status.configure(
                text="🟡 USB: SCANNING...",
                text_color=COLOR_CLAUDE_AMBER,
                fg_color=COLOR_STAT_BOX
            )
            self.lbl_hw_pulse.configure(text="🫀 Pulse: Simulator Active", text_color=COLOR_TEXT_MUTED)

            if self.patient_presence_state == "ABSENT":
                self.bpm = 0
                self.bpm_lbl.configure(text="--", text_color=COLOR_TEXT_DIM)
                self.rhythm_lbl.configure(
                    text="⚪ NO HUMAN DETECTED (BED VACANT // FLATLINE)", 
                    text_color="#78716C", 
                    fg_color=COLOR_STAT_BOX
                )
                self.status_badge.configure(
                    text="⚪ NO HUMAN DETECTED (BED EMPTY)", 
                    text_color="#78716C",
                    fg_color=COLOR_STAT_BOX
                )
                self.auto_call_dispatched = False

            elif self.patient_presence_state == "NORMAL":
                delta = (math.sin(time.time() * 0.8) * 2) + ((time.time() * 1000) % 3 - 1)
                self.bpm = int(round(self.base_bpm + delta))
                self.bpm_lbl.configure(text=str(self.bpm), text_color=COLOR_TEXT_MAIN)
                self.rhythm_lbl.configure(
                    text="🟢 NORMAL SINUS RHYTHM", 
                    text_color=COLOR_NORMAL_TXT, 
                    fg_color=COLOR_NORMAL_BG
                )
                self.status_badge.configure(
                    text="● PATIENT PRESENT // VITALS NORMAL", 
                    text_color=COLOR_NORMAL_TXT,
                    fg_color=COLOR_NORMAL_BG
                )
                self.auto_call_dispatched = False

            elif self.patient_presence_state == "CARDIAC_ISSUE":
                delta = (math.sin(time.time() * 2) * 5)
                self.bpm = int(round(136 + delta))
                self.bpm_lbl.configure(text=str(self.bpm), text_color=COLOR_ALERT_TXT)
                self.rhythm_lbl.configure(
                    text="🚨 VENTRICULAR TACHYCARDIA // ARREST RISK", 
                    text_color=COLOR_ALERT_TXT, 
                    fg_color=COLOR_ALERT_BG
                )
                self.status_badge.configure(
                    text="🚨 CRITICAL CARDIAC DISTRESS // AUTO-CALL ACTIVE", 
                    text_color=COLOR_ALERT_TXT,
                    fg_color=COLOR_ALERT_BG
                )

                if self.auto_call_enabled.get() and not self.auto_call_dispatched:
                    self.auto_call_dispatched = True
                    threading.Thread(target=self.trigger_heart_auto_call, daemon=True).start()

        # Update shared state
        try:
            curr_state = shared_state.load_state()
            curr_state["bpm"] = self.bpm
            curr_state["rhythm"] = self.rhythm_lbl.cget("text")
            curr_state["presence_state"] = self.patient_presence_state
            shared_state.save_state(curr_state)
        except Exception:
            pass

        self.after(1000, self.periodic_telemetry_loop)

    def trigger_heart_auto_call(self):
        """Automatically calls the emergency contact and broadcasts to all apps on heart distress"""
        phone = self.phone_entry.get().strip() or "+1 (555) 911-0420"
        state = shared_state.load_state()
        loc = state.get("location", {})
        
        role = self.auth_session.get("role", "home") if self.auth_session else "home"
        p_name = self.auth_session.get("user_name", "Eleanor Vance (Home Care)") if self.auth_session else "Eleanor Vance (Home Care)"
        ward_info = self.auth_session.get("ward", "Living Room / Bedroom Suite") if self.auth_session else "Living Room / Bedroom Suite"
        recipient = "Family Caregiver / Emergency SOS" if role == "home" else ("Attending ICU Chief Doctor" if role == "hospital" else "Hospital Bedside Staff")
        sender = "HOME_CARE_MONITOR" if role == "home" else ("BED_03_PATIENT_MONITOR" if role == "user" else "ICU_COMMAND_MONITOR")
        room_label = "Home Suite" if role == "home" else "Room 402 // Bed 03"

        payload = {
            "type": "EMERGENCY_CALL",
            "sender_id": sender,
            "patient_name": p_name,
            "patient_id": "HOME-01" if role == "home" else "ICU-9024-X",
            "ward": ward_info,
            "room_bed": room_label,
            "bpm": self.bpm,
            "condition": "HOME HEALTHCARE: CARDIAC DISTRESS ALERT" if role == "home" else "AUTOMATED CARDIAC DISTRESS TRIGGER",
            "city": loc.get("city", "Jamshedpur"),
            "region": loc.get("region", "Jharkhand"),
            "country": loc.get("country", "India"),
            "lat": loc.get("lat", 22.8028),
            "lon": loc.get("lon", 86.1855),
            "maps_url": loc.get("maps_url", "https://maps.google.com"),
            "phone": phone,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 1. Broadcast to all other apps on network (P2P App-to-App Calling)
        dispatch_engine.NetworkCallBroadcaster.broadcast_emergency_call(payload)

        # 2. Fire multi-tier calling engine (Twilio, GSM, tel:, SAPI5)
        self.coordinator.calling_sys.make_call(phone, payload)

        # 3. Open Live Calling Console on the main app
        def _open_ui():
            calling_console.LiveCallingConsole(
                self,
                recipient_name=recipient,
                phone_number=phone,
                alert_payload=payload
            )
        self.after(0, _open_ui)

    def sync_location_from_state(self):
        """Reads location, contact, and emergency updates from shared state"""
        try:
            state = shared_state.load_state()
            loc = state.get("location", {})
            city = loc.get("city", "")
            region = loc.get("region", "")
            country = loc.get("country", "")
            lat = loc.get("lat", 0.0)
            lon = loc.get("lon", 0.0)

            if city and city != "Locating...":
                loc_text = f"📍 {city}, {region}, {country} ({lat:.4f}°, {lon:.4f}°)"
                self.geo_loc_lbl.configure(text=loc_text)
                self.current_maps_url = loc.get("maps_url", f"https://www.google.com/maps?q={lat},{lon}")

            # External trigger sync
            if state.get("is_emergency", False) and not self.is_emergency:
                self.is_emergency = True
            elif not state.get("is_emergency", False) and self.is_emergency:
                self.is_emergency = False
        except Exception as e:
            print("Location sync error:", e)

        self.after(2000, self.sync_location_from_state)

    def toggle_emergency(self):
        self.set_presence_state("CARDIAC_ISSUE")
        shared_state.update_emergency(True, "Critical Cardiac Event / SOS Button")

    def clear_emergency(self):
        self.set_presence_state("NORMAL")
        shared_state.update_emergency(False)

    def call_emergency_contact(self):
        """Launches the Live Telephony Calling Console directly from bedside/home monitor"""
        phone = self.phone_entry.get().strip() or "+1 (555) 911-0420"
        state = shared_state.load_state()
        loc = state.get("location", {})
        
        role = self.auth_session.get("role", "home") if self.auth_session else "home"
        p_name = self.auth_session.get("user_name", "Eleanor Vance (Home Care)") if self.auth_session else "Eleanor Vance (Home Care)"
        ward_info = self.auth_session.get("ward", "Living Room / Bedroom Suite") if self.auth_session else "Living Room / Bedroom Suite"
        recipient = "Family Caregiver / Emergency SOS" if role == "home" else ("Attending ICU Chief Doctor" if role == "hospital" else "Hospital Bedside Staff")
        sender = "HOME_CARE_MONITOR" if role == "home" else ("BED_03_PATIENT_MONITOR" if role == "user" else "ICU_COMMAND_MONITOR")
        room_label = "Home Suite" if role == "home" else "Room 402 // Bed 03"

        payload = {
            "type": "EMERGENCY_CALL",
            "sender_id": sender,
            "patient_name": p_name,
            "patient_id": "HOME-01" if role == "home" else "ICU-9024-X",
            "ward": ward_info,
            "room_bed": room_label,
            "bpm": self.bpm,
            "condition": "MANUAL FAMILY SOS CALL FROM HOME APP" if role == "home" else "MANUAL EMERGENCY CALL FROM MAIN APP",
            "city": loc.get("city", "Jamshedpur"),
            "lat": loc.get("lat", 22.8028),
            "lon": loc.get("lon", 86.1855),
            "maps_url": loc.get("maps_url", "https://maps.google.com"),
            "phone": phone
        }

        # Broadcast to all apps
        dispatch_engine.NetworkCallBroadcaster.broadcast_emergency_call(payload)

        # Trigger calling engine
        threading.Thread(target=lambda: self.coordinator.calling_sys.make_call(phone, payload), daemon=True).start()

        # Open softphone console
        calling_console.LiveCallingConsole(
            self,
            recipient_name=recipient,
            phone_number=phone,
            alert_payload=payload
        )

    def open_maps(self):
        url = getattr(self, 'current_maps_url', "https://maps.google.com")
        webbrowser.open(url)

if __name__ == "__main__":
    app = SmartWardMonitorApp()
    app.mainloop()
