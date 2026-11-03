import os
import sys
import time
import json
import webbrowser
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Ensure local directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import shared_state
import dispatch_engine
import calling_console
import auth_system
import login_view

# ==============================================================================
# CLAUDE THEME DESIGN SYSTEM (LIGHT / DARK TUPLES)
# ==============================================================================
COLOR_BG_MAIN = ("#FAF9F5", "#0b0f19")        # Claude Warm Alabaster / Dark Navy
COLOR_BG_CARD = ("#FFFFFF", "#1e293b")        # Pure Crisp White / Slate Card
COLOR_BORDER = ("#E8E6DF", "#334155")         # Warm Stone Border / Slate Border
COLOR_TEXT_MAIN = ("#1C1917", "#F8FAFC")      # Deep Stone Charcoal / Bright White
COLOR_TEXT_MUTED = ("#57534E", "#94A3B8")     # Warm Stone 600 / Cool Slate
COLOR_TEXT_DIM = ("#78716C", "#64748B")       # Subdued Stone 500 / Dim Slate

# Brand & Clinical Accents
COLOR_CLAUDE_AMBER = ("#D97706", "#F59E0B")   # Warm Terracotta Amber
COLOR_CLAUDE_HOVER = ("#B45309", "#D97706")   # Deep Terracotta Hover
COLOR_NORMAL_TXT = ("#047857", "#34D399")     # Medical Emerald Green
COLOR_NORMAL_BG = ("#ECFDF5", "#064E3B")      # Soft Sage / Dark Pine
COLOR_ALERT_TXT = ("#DC2626", "#F87171")      # Medical Red
COLOR_ALERT_BG = ("#FEF2F2", "#7F1D1D")       # Soft Blush / Deep Crimson
COLOR_STAT_BOX = ("#F5F4EF", "#0f172a")       # Sub-card panel
COLOR_ENTRY_BG = ("#FFFFFF", "#0f172a")       # Input fields
COLOR_CONSOLE_BG = ("#FDFCF7", "#070b14")     # Log console paper

class EmergencyDispatcherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # State initialization
        self.state_data = shared_state.load_state()
        self.current_theme = self.state_data.get("ui_theme", "light")

        # Window Setup
        self.title("D.B.M.S. Emergency Location & Automated Dispatch Center")
        self.geometry("1140x920")
        self.minsize(980, 780)
        self.configure(fg_color=COLOR_BG_MAIN)

        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        # Authentication Session State (User Mode vs. Hospital Mode)
        self.auth_session = None

        # Initialize Dispatch Engine with Inbound Call Listener
        self.coordinator = dispatch_engine.EmergencyDispatchCoordinator(
            on_inbound_call=self.handle_incoming_emergency_call
        )
        self.current_location = self.coordinator.location_sys.cached_location
        self.active_inbound_alert = False
        self.last_inbound_packet = {}

        # Build Main Layout Containers:
        # 1. Login Scene View (10-Digit Code Authentication Gate)
        self.login_scene = login_view.LoginSceneFrame(
            self,
            on_login_success=self.on_login_success,
            current_theme=self.current_theme
        )

        # 2. Main Dashboard Container (Hidden until authenticated)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.create_dashboard_widgets(self.main_container)

        # Initially present the 10-Digit Code Login Scene
        self.login_scene.pack(fill="both", expand=True)

        # Window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Load saved data & start background tasks
        self.load_configuration()
        threading.Thread(target=self.refresh_location_task, daemon=True).start()
        self.after(1000, self.automation_listener_poll)

    def create_dashboard_widgets(self, parent):
        self.create_header(parent)
        self.create_incoming_call_banner(parent)
        self.create_phone_number_section(parent)
        self.create_channels_configuration_section(parent)
        self.create_location_section(parent)
        self.create_dispatch_actions_section(parent)
        self.create_console_section(parent)

    def on_login_success(self, session):
        self.auth_session = session
        self.login_scene.pack_forget()
        self.main_container.pack(fill="both", expand=True)

        role = session.get("role", "hospital")
        u_name = session.get("user_name", "Authorized User")
        code_fmt = session.get("formatted_code", "7070-2031-23")

        if role == "user":
            self.lbl_mode_pill.configure(
                text=f"👤 PATIENT MODE: {u_name} [{code_fmt}]",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.lbl_header_title.configure(text="👤 PATIENT EMERGENCY DISPATCH & CALL CONSOLE")
            self.log("AUTH", f"User logged in as Bedside Patient: {u_name} (Code: {code_fmt})")
        else:
            self.lbl_mode_pill.configure(
                text=f"🏥 HOSPITAL COMMAND: {u_name} [{code_fmt}]",
                text_color=COLOR_CLAUDE_AMBER,
                fg_color=COLOR_STAT_BOX
            )
            self.lbl_header_title.configure(text="🚨 EMERGENCY LOCATION & AUTOMATED DISPATCH CENTER")
            self.log("AUTH", f"User logged in as Hospital Command: {u_name} (Code: {code_fmt})")

    def log_out(self):
        self.log("AUTH", "User session ended. Logging out to authentication scene...")
        self.auth_session = None
        self.main_container.pack_forget()
        self.login_scene.pack(fill="both", expand=True)

    def on_close(self):
        try:
            self.coordinator.receiver.stop()
        except Exception:
            pass
        self.destroy()

    def log(self, tag, message):
        """Thread-safe logging into console textbox"""
        def _append():
            ts = time.strftime("%H:%M:%S")
            self.console_text.configure(state="normal")
            self.console_text.insert("end", f"[{ts}] [{tag}] {message}\n")
            self.console_text.see("end")
            self.console_text.configure(state="disabled")
        self.after(0, _append)

    # --------------------------------------------------------------------------
    # 1. HEADER SECTION
    # --------------------------------------------------------------------------
    def create_header(self, parent=None):
        parent = parent or self
        header = ctk.CTkFrame(
            parent, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=14, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        header.pack(fill="x", padx=16, pady=(16, 5))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=16, pady=10)

        self.lbl_header_title = ctk.CTkLabel(
            left, 
            text="🚨 EMERGENCY LOCATION & AUTOMATED DISPATCH CENTER", 
            font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_header_title.pack(anchor="w")

        self.lbl_header_sub = ctk.CTkLabel(
            left, 
            text="LIVE SOFTPHONE CONSOLE // MULTI-TIER CALLING // REAL-TIME SMS & MAPS // P2P INTERCOM", 
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        )
        self.lbl_header_sub.pack(anchor="w")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=16, pady=10)

        top_right = ctk.CTkFrame(right, fg_color="transparent")
        top_right.pack(anchor="e")

        # Theme Switcher Button
        theme_btn_text = "🌙 Dark Mode" if self.current_theme == "light" else "☀️ Claude Light"
        self.btn_theme = ctk.CTkButton(
            top_right,
            text=theme_btn_text,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            height=28,
            width=115,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self.toggle_theme
        )
        self.btn_theme.pack(side="right", padx=(6, 0))

        # Logout Button
        self.btn_logout = ctk.CTkButton(
            top_right,
            text="🔒 Log Out",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_BORDER,
            height=28,
            width=85,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            command=self.log_out
        )
        self.btn_logout.pack(side="right")

        bottom_right = ctk.CTkFrame(right, fg_color="transparent")
        bottom_right.pack(anchor="e", pady=(4, 0))

        # Mode Indicator Pill
        self.lbl_mode_pill = ctk.CTkLabel(
            bottom_right,
            text="🏥 HOSPITAL DISPATCH MODE [Key: 7070-2031-23]",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=8,
            padx=10,
            pady=3
        )
        self.lbl_mode_pill.pack(side="right", padx=(8, 0))

        self.status_badge = ctk.CTkLabel(
            bottom_right,
            text="● AUTOMATION ENGINE: ARMED",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_NORMAL_BG,
            corner_radius=8,
            padx=10,
            pady=3
        )
        self.status_badge.pack(side="right")

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.current_theme = new_theme
        ctk.set_appearance_mode(new_theme)
        shared_state.update_theme(new_theme)

        theme_btn_text = "🌙 Dark Mode" if new_theme == "light" else "☀️ Claude Light"
        self.btn_theme.configure(text=theme_btn_text)

        is_light = (new_theme == "light")
        console_bg = "#FDFCF7" if is_light else "#070b14"
        console_fg = "#1C1917" if is_light else "#E2E8F0"
        self.console_text.configure(fg_color=console_bg, text_color=console_fg)

    # --------------------------------------------------------------------------
    # 2. INCOMING EMERGENCY DISTRESS CALL MODAL CONTAINER
    # --------------------------------------------------------------------------
    def create_incoming_call_banner(self, parent=None):
        self.inbound_container = ctk.CTkFrame(parent or self, fg_color="transparent")
        self.inbound_container.pack(fill="x", padx=16, pady=(0, 2))

        self.inbound_card = ctk.CTkFrame(
            self.inbound_container, 
            fg_color=("#FEF2F2", "#3b0707"), 
            corner_radius=12, 
            border_width=2, 
            border_color=("#DC2626", "#EF4444")
        )
        # Initially hidden until an emergency call packet arrives
        
        inner = ctk.CTkFrame(self.inbound_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        self.inbound_title = ctk.CTkLabel(
            left,
            text="🚨 INCOMING EMERGENCY CALL: CRITICAL PATIENT DISTRESS!",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=("#DC2626", "#FFFFFF")
        )
        self.inbound_title.pack(anchor="w")

        self.inbound_details = ctk.CTkLabel(
            left,
            text="Caller: Patient Robert Jenkins (#ICU-9024-X)  |  Zone-B ICU (Room 402, Bed 03)  |  BPM: 135",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=("#991B1B", "#FCA5A5")
        )
        self.inbound_details.pack(anchor="w")

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        self.btn_answer_call = ctk.CTkButton(
            right,
            text="📞 Answer / Open Audio Channel",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            command=self.answer_inbound_call
        )
        self.btn_answer_call.pack(side="left", padx=(0, 8))

        self.btn_view_inbound_map = ctk.CTkButton(
            right,
            text="🌐 View Location",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            height=34,
            command=self.open_google_maps
        )
        self.btn_view_inbound_map.pack(side="left")

    # --------------------------------------------------------------------------
    # 3. PHONE NUMBER & SOFTPHONE CALLING SECTION
    # --------------------------------------------------------------------------
    def create_phone_number_section(self, parent=None):
        sec = ctk.CTkFrame(
            parent or self, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=12, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        sec.pack(fill="x", padx=16, pady=4)

        top_info = ctk.CTkFrame(sec, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(8, 4))

        ctk.CTkLabel(
            top_info,
            text="EMERGENCY CONTACT PHONE NUMBER & LIVE SOFTPHONE CALLING CONSOLE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(side="left")

        # Direct Softphone Launch Button
        ctk.CTkButton(
            top_info,
            text="📞 Open Softphone Call Console",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            text_color="#FFFFFF",
            height=26,
            corner_radius=6,
            command=self.open_live_calling_console
        ).pack(side="right")

        row = ctk.CTkFrame(sec, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(2, 6))

        ctk.CTkLabel(
            row,
            text="Emergency Phone No:",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(side="left", padx=(0, 8))

        self.phone_entry = ctk.CTkEntry(
            row,
            placeholder_text="+1 (555) 911-0420 or +91 9876543210",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            width=240,
            height=34,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MAIN
        )
        self.phone_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            row,
            text="Contact Name / Role:",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left", padx=(4, 6))

        self.recipient_entry = ctk.CTkEntry(
            row,
            placeholder_text="Primary Attending Doctor",
            font=ctk.CTkFont(family="Inter", size=13),
            width=220,
            height=34,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MAIN
        )
        self.recipient_entry.insert(0, "Dr. A. Vance, MD (ICU Chief)")
        self.recipient_entry.pack(side="left", padx=(0, 10))

        btn_save = ctk.CTkButton(
            row,
            text="💾 Save Number",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            text_color="#FFFFFF",
            height=34,
            width=115,
            corner_radius=8,
            command=self.save_phone_number
        )
        btn_save.pack(side="left")

        # Speed Dial Presets Row
        preset_row = ctk.CTkFrame(sec, fg_color="transparent")
        preset_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            preset_row,
            text="Speed Dial Presets:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left", padx=(0, 8))

        presets = [
            ("Dr. Vance (ICU Chief)", "+1 (555) 911-0420"),
            ("Rapid Response Trauma", "+1 (555) 911-0421"),
            ("Code Blue Crash Team", "+1 (555) 911-0422"),
            ("Emergency Services (911)", "911")
        ]
        for name, num in presets:
            ctk.CTkButton(
                preset_row,
                text=name,
                font=ctk.CTkFont(family="Inter", size=10),
                fg_color=COLOR_STAT_BOX,
                text_color=COLOR_TEXT_MAIN,
                hover_color=COLOR_BORDER,
                border_width=1,
                border_color=COLOR_BORDER,
                height=24,
                corner_radius=5,
                command=lambda n=name, nu=num: self.set_preset_contact(n, nu)
            ).pack(side="left", padx=3)

    def set_preset_contact(self, name, phone):
        self.recipient_entry.delete(0, "end")
        self.recipient_entry.insert(0, name)
        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, phone)
        shared_state.update_emergency_contact(phone)
        self.log("SPEED-DIAL", f"Selected preset contact: {name} ({phone})")

    def open_live_calling_console(self, custom_phone=None, custom_name=None):
        phone = custom_phone or self.phone_entry.get().strip() or "+1 (555) 911-0420"
        recipient = custom_name or self.recipient_entry.get().strip() or "Attending Doctor"
        
        state = shared_state.load_state()
        state.update(self.current_location)
        
        self.log("CALL-SYS", f"Opening Live Telephony Calling Console to {phone} ({recipient})...")

        # Fire multi-tier audio dispatch in parallel
        cfg = self.get_gateways_dict()
        threading.Thread(
            target=lambda: self.coordinator.calling_sys.make_call(phone, state, cfg, self.log),
            daemon=True
        ).start()

        # Instantiate the new calling console window
        calling_console.LiveCallingConsole(
            self,
            recipient_name=recipient,
            phone_number=phone,
            alert_payload=state,
            on_hangup=lambda dur: self.log("CALL-END", f"Call to {phone} completed. Duration: {dur}s")
        )

    # --------------------------------------------------------------------------
    # 4. CHANNELS CONFIGURATION SECTION
    # --------------------------------------------------------------------------
    def create_channels_configuration_section(self, parent=None):
        self.chan_card = ctk.CTkFrame(
            parent or self, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=12, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        self.chan_card.pack(fill="x", padx=16, pady=4)

        top_row = ctk.CTkFrame(self.chan_card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(8, 4))

        ctk.CTkLabel(
            top_row,
            text="MULTI-TIER DISPATCH CHANNELS (CLOUD & HARDWARE GATEWAYS)",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(side="left")

        self.btn_toggle_cfg = ctk.CTkButton(
            top_row,
            text="⚙️ Advanced Channel Settings ▼",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=24,
            corner_radius=6,
            command=self.toggle_advanced_config
        )
        self.btn_toggle_cfg.pack(side="right")

        self.cfg_content = ctk.CTkFrame(self.chan_card, fg_color=COLOR_STAT_BOX, corner_radius=10)
        self.cfg_content.pack(fill="x", padx=16, pady=(0, 8))

        g = ctk.CTkFrame(self.cfg_content, fg_color="transparent")
        g.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(g, text="Twilio Account SID (Optional):", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.twilio_sid_entry = ctk.CTkEntry(g, placeholder_text="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", width=250, height=28, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN)
        self.twilio_sid_entry.grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ctk.CTkLabel(g, text="Twilio Auth Token:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).grid(row=0, column=2, sticky="w", padx=(14, 4), pady=2)
        self.twilio_token_entry = ctk.CTkEntry(g, placeholder_text="Auth Token", show="•", width=180, height=28, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN)
        self.twilio_token_entry.grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ctk.CTkLabel(g, text="Twilio From Phone No:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.twilio_from_entry = ctk.CTkEntry(g, placeholder_text="+1234567890", width=250, height=28, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN)
        self.twilio_from_entry.grid(row=1, column=1, sticky="w", padx=4, pady=3)

        ctk.CTkLabel(g, text="GSM Cellular Port:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).grid(row=1, column=2, sticky="w", padx=(14, 4), pady=3)
        self.gsm_port_entry = ctk.CTkEntry(g, placeholder_text="e.g. COM3 or COM4", width=180, height=28, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN)
        self.gsm_port_entry.grid(row=1, column=3, sticky="w", padx=4, pady=3)

        ctk.CTkLabel(g, text="Hospital EMR Webhook:", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.webhook_entry = ctk.CTkEntry(g, placeholder_text="https://hospital-emr.internal/api/icu-alert", width=420, height=28, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN)
        self.webhook_entry.grid(row=2, column=1, columnspan=2, sticky="w", padx=4, pady=2)

        btn_save_cfg = ctk.CTkButton(
            g,
            text="Save Gateways",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=28,
            corner_radius=6,
            command=self.save_gateways_config
        )
        btn_save_cfg.grid(row=2, column=3, sticky="e", padx=4, pady=2)

    def toggle_advanced_config(self):
        if self.cfg_content.winfo_viewable():
            self.cfg_content.pack_forget()
            self.btn_toggle_cfg.configure(text="⚙️ Advanced Channel Settings ▶")
        else:
            self.cfg_content.pack(fill="x", padx=16, pady=(0, 8))
            self.btn_toggle_cfg.configure(text="⚙️ Advanced Channel Settings ▼")

    # --------------------------------------------------------------------------
    # 5. LOCATION SECTION
    # --------------------------------------------------------------------------
    def create_location_section(self, parent=None):
        loc_card = ctk.CTkFrame(
            parent or self, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=12, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        loc_card.pack(fill="x", padx=16, pady=4)

        loc_top = ctk.CTkFrame(loc_card, fg_color="transparent")
        loc_top.pack(fill="x", padx=16, pady=(8, 2))

        ctk.CTkLabel(
            loc_top,
            text="REAL-TIME LOCATION RESOLUTION & POSITIONING ENGINE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(side="left")

        self.loc_tier_badge = ctk.CTkLabel(
            loc_top,
            text="HYBRID GPS / NETWORK FIX: ACTIVE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_NORMAL_TXT
        )
        self.loc_tier_badge.pack(side="right")

        details_box = ctk.CTkFrame(loc_card, fg_color=COLOR_STAT_BOX, corner_radius=10)
        details_box.pack(fill="x", padx=16, pady=(4, 8))

        self.lbl_addr = ctk.CTkLabel(
            details_box,
            text="📍 Location: Resolving geographic telemetry...",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_addr.pack(anchor="w", padx=14, pady=(6, 2))

        self.lbl_coords = ctk.CTkLabel(
            details_box,
            text="GPS Coordinates: Lat --.----°, Lon --.----°  |  Postal Code: ------",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLOR_CLAUDE_AMBER
        )
        self.lbl_coords.pack(anchor="w", padx=14, pady=(0, 6))

        btn_box = ctk.CTkFrame(loc_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            btn_box,
            text="🔄 Refresh Location Now",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=30,
            corner_radius=6,
            command=lambda: threading.Thread(target=self.refresh_location_task, daemon=True).start()
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_box,
            text="🌐 Open Google Maps",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            text_color="#FFFFFF",
            height=30,
            corner_radius=6,
            command=self.open_google_maps
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_box,
            text="🗺️ Open OpenStreetMap",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=30,
            corner_radius=6,
            command=self.open_osm_maps
        ).pack(side="left")

    # --------------------------------------------------------------------------
    # 6. DISPATCH ACTIONS & AUTOMATION TRIGGERS
    # --------------------------------------------------------------------------
    def create_dispatch_actions_section(self, parent=None):
        act_card = ctk.CTkFrame(
            parent or self, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=12, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        act_card.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            act_card,
            text="EMERGENCY DISPATCH ACTIONS & AUTOMATION TRIGGERS",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER
        ).pack(anchor="w", padx=16, pady=(8, 4))

        btn_row = ctk.CTkFrame(act_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 10))

        # Main SOS Button
        ctk.CTkButton(
            btn_row,
            text="🚨 TRIGGER FULL EMERGENCY DISPATCH (CALL + TEXT + BROADCAST)",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=40,
            corner_radius=8,
            command=lambda: threading.Thread(target=self.run_full_dispatch, daemon=True).start()
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            btn_row,
            text="📞 Live Emergency Call",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=40,
            width=160,
            corner_radius=8,
            command=self.run_test_call
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="💬 Send SMS Text",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            text_color="#FFFFFF",
            height=40,
            width=130,
            corner_radius=8,
            command=lambda: threading.Thread(target=self.run_test_text, daemon=True).start()
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="✓ Clear Alarm",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=40,
            width=110,
            corner_radius=8,
            command=self.clear_alarm
        ).pack(side="left")

    # --------------------------------------------------------------------------
    # 7. CONSOLE AUDIT LOG
    # --------------------------------------------------------------------------
    def create_console_section(self, parent=None):
        log_frame = ctk.CTkFrame(
            parent or self, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=12, 
            border_width=1, 
            border_color=COLOR_BORDER
        )
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 14))

        top = ctk.CTkFrame(log_frame, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(6, 2))

        ctk.CTkLabel(
            top,
            text="REAL-TIME TELEMETRY & DISPATCH AUDIT LOG",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        ctk.CTkButton(
            top,
            text="Clear",
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=COLOR_STAT_BOX,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=22,
            width=60,
            corner_radius=6,
            command=self.clear_console
        ).pack(side="right")

        is_light = (self.current_theme == "light")
        console_bg = "#FDFCF7" if is_light else "#070b14"
        console_fg = "#1C1917" if is_light else "#E2E8F0"

        self.console_text = ctk.CTkTextbox(
            log_frame,
            fg_color=console_bg,
            text_color=console_fg,
            font=ctk.CTkFont(family="Consolas", size=11),
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.console_text.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.console_text.configure(state="disabled")

    def clear_console(self):
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")

    # --------------------------------------------------------------------------
    # INCOMING EMERGENCY CALL HANDLING (WHOEVER HAS THE APP GETS CALLED)
    # --------------------------------------------------------------------------
    def handle_incoming_emergency_call(self, packet, addr):
        """Invoked when another person/node on the network triggers an emergency call"""
        self.last_inbound_packet = packet
        patient = packet.get("patient_name", "Unknown Patient")
        pid = packet.get("patient_id", "")
        ward = packet.get("ward", "ICU Ward")
        room = packet.get("room_bed", "Bed")
        bpm = packet.get("bpm", 135)
        city = packet.get("city", "")
        lat = packet.get("lat", 0.0)
        lon = packet.get("lon", 0.0)

        self.log("INBOUND-CALL", f"🚨 INCOMING EMERGENCY CALL from {addr[0]}: {patient} ({ward}, {room}) @ {bpm} BPM!")

        def _show_inbound():
            self.inbound_details.configure(
                text=f"Caller: {patient} (#{pid}) | {ward} ({room}) | Heart Rate: {bpm} BPM | Loc: {city} ({lat:.4f}, {lon:.4f})"
            )
            self.inbound_card.pack(fill="x", padx=0, pady=4)
            self.status_badge.configure(text="🚨 INCOMING CALL ACTIVE!", text_color="#FFFFFF", fg_color="#DC2626")
            self.active_inbound_alert = True

        self.after(0, _show_inbound)

    def answer_inbound_call(self):
        self.inbound_card.pack_forget()
        self.active_inbound_alert = False
        self.status_badge.configure(
            text="● AUTOMATION ENGINE: ARMED", 
            text_color=COLOR_NORMAL_TXT, 
            fg_color=COLOR_NORMAL_BG
        )
        self.log("ACK", "Inbound Emergency Call answered. Connecting two-way voice channel...")
        
        # Launch Softphone Calling Console for the inbound caller
        packet = self.last_inbound_packet or {}
        caller_name = packet.get("patient_name", "ICU Bed Distress Node")
        ward = packet.get("ward", "Zone-B ICU")
        
        calling_console.LiveCallingConsole(
            self,
            recipient_name=f"{caller_name} ({ward})",
            phone_number=packet.get("phone", "P2P Net Intercom"),
            alert_payload=packet,
            on_hangup=lambda dur: self.log("CALL-END", f"Inbound call concluded. Duration: {dur}s")
        )

    # --------------------------------------------------------------------------
    # BUSINESS LOGIC & AUTOMATION
    # --------------------------------------------------------------------------
    def load_configuration(self):
        state = shared_state.load_state()
        contact = state.get("emergency_contact", "+1 (555) 911-0420")
        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, contact)

        gateways = state.get("gateways", {})
        self.twilio_sid_entry.insert(0, gateways.get("twilio_sid", ""))
        self.twilio_token_entry.insert(0, gateways.get("twilio_token", ""))
        self.twilio_from_entry.insert(0, gateways.get("twilio_from", ""))
        self.gsm_port_entry.insert(0, gateways.get("gsm_port", ""))
        self.webhook_entry.insert(0, gateways.get("webhook_url", ""))

        self.log("INIT", f"Loaded emergency recipient: {contact}")
        self.log("INIT", "New Calling System, Softphone Console, Messaging, Location, and P2P Intercom armed on port 8765.")

    def get_gateways_dict(self):
        return {
            "twilio_sid": self.twilio_sid_entry.get().strip(),
            "twilio_token": self.twilio_token_entry.get().strip(),
            "twilio_from": self.twilio_from_entry.get().strip(),
            "gsm_port": self.gsm_port_entry.get().strip(),
            "webhook_url": self.webhook_entry.get().strip()
        }

    def save_phone_number(self):
        num = self.phone_entry.get().strip()
        if not num:
            messagebox.showwarning("Invalid Input", "Please enter a valid phone number.")
            return
        shared_state.update_emergency_contact(num)
        self.log("CONFIG", f"Emergency contact phone number updated: {num}")
        messagebox.showinfo("Saved", f"Emergency Contact updated:\n{num}")

    def save_gateways_config(self):
        state = shared_state.load_state()
        state["gateways"] = self.get_gateways_dict()
        shared_state.save_state(state)
        self.log("CONFIG", "Multi-tier gateway configuration saved.")
        messagebox.showinfo("Saved", "Gateway settings saved successfully.")

    def refresh_location_task(self):
        self.log("GEO", "Pinging Location Engine across GPS / Wi-Fi / IP Positioning tiers...")
        loc = self.coordinator.location_sys.resolve_location()
        self.current_location = loc
        shared_state.update_location(loc)

        def _update():
            self.lbl_addr.configure(text=f"📍 Location: {loc['city']}, {loc['region']}, {loc['country']}")
            self.lbl_coords.configure(text=f"GPS Coordinates: Lat {loc['lat']:.4f} N, Lon {loc['lon']:.4f} E  |  Postal Code: {loc['postal']}")
        self.after(0, _update)
        self.log("GEO-OK", f"Position Locked: {loc['lat']:.4f} N, {loc['lon']:.4f} E ({loc['city']}, {loc['region']})")

    def open_google_maps(self):
        url = self.current_location.get("maps_url", f"https://maps.google.com/?q={self.current_location.get('lat', 0)},{self.current_location.get('lon', 0)}")
        self.log("BROWSER", f"Opening Google Maps: {url}")
        webbrowser.open(url)

    def open_osm_maps(self):
        url = self.current_location.get("osm_url", f"https://www.openstreetmap.org/?mlat={self.current_location.get('lat', 0)}&mlon={self.current_location.get('lon', 0)}")
        self.log("BROWSER", f"Opening OpenStreetMap: {url}")
        webbrowser.open(url)

    def run_full_dispatch(self):
        phone = self.phone_entry.get().strip() or "+1 (555) 911-0420"
        recipient = self.recipient_entry.get().strip() or "Dr. A. Vance, MD (ICU Chief)"
        self.status_badge.configure(text="🚨 DISPATCHING EMERGENCY CALL & TEXT!", text_color="#FFFFFF", fg_color="#DC2626")
        shared_state.update_emergency(True, "Emergency Dispatch Center Activation")

        cfg = self.get_gateways_dict()
        state = shared_state.load_state()

        # Open Live Calling Console in GUI
        self.after(0, lambda: self.open_live_calling_console(custom_phone=phone, custom_name=recipient))

        self.coordinator.execute_complete_emergency_dispatch(
            phone=phone,
            patient_state=state,
            config=cfg,
            log_cb=self.log
        )

    def run_test_call(self):
        phone = self.phone_entry.get().strip() or "+1 (555) 911-0420"
        recipient = self.recipient_entry.get().strip() or "Dr. A. Vance, MD (ICU Chief)"
        self.open_live_calling_console(custom_phone=phone, custom_name=recipient)

    def run_test_text(self):
        phone = self.phone_entry.get().strip() or "+1 (555) 911-0420"
        cfg = self.get_gateways_dict()
        state = shared_state.load_state()
        state.update(self.current_location)
        self.log("TEST-SMS", f"Executing Test SMS payload to {phone}...")
        self.coordinator.messaging_sys.send_message(phone, state, cfg, self.log)

    def clear_alarm(self):
        shared_state.update_emergency(False)
        self.status_badge.configure(
            text="● AUTOMATION ENGINE: ARMED", 
            text_color=COLOR_NORMAL_TXT, 
            fg_color=COLOR_NORMAL_BG
        )
        if self.inbound_card.winfo_viewable():
            self.inbound_card.pack_forget()
        self.log("STANDBY", "Emergency alarm cleared. Returned to normal monitoring state.")

    def automation_listener_poll(self):
        """Monitors shared_state to automatically trigger dispatch if App 1 enters emergency"""
        try:
            state = shared_state.load_state()
            is_emerg = state.get("is_emergency", False)
            dispatch = state.get("dispatch_status", {})

            if is_emerg and not dispatch.get("call_sent", False):
                self.log("INTERLINK-ALERT", f"Incoming Emergency Trigger from ICU Monitor! Cause: {state.get('emergency_cause', 'Threshold Breach')}")
                state["dispatch_status"]["call_sent"] = True
                state["dispatch_status"]["text_sent"] = True
                state["dispatch_status"]["last_dispatch_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                shared_state.save_state(state)

                threading.Thread(target=self.run_full_dispatch, daemon=True).start()
            elif not is_emerg:
                if not self.active_inbound_alert and self.status_badge.cget("text") != "● AUTOMATION ENGINE: ARMED":
                    self.status_badge.configure(
                        text="● AUTOMATION ENGINE: ARMED", 
                        text_color=COLOR_NORMAL_TXT, 
                        fg_color=COLOR_NORMAL_BG
                    )
        except Exception as e:
            print("Poll error:", e)

        self.after(1000, self.automation_listener_poll)

if __name__ == "__main__":
    app = EmergencyDispatcherApp()
    app.mainloop()
