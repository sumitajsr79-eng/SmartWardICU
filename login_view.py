"""
D.B.M.S. Smart Ward ICU - Clean & Friendly Authentication Console
Simple, modern, user-friendly interface with 1-click access for Home Care,
Patient Bedside, and Hospital Clinical Modes.
"""

import tkinter as tk
import customtkinter as ctk
import auth_system

# Modern Palette (Warm Alabaster Light / Deep Navy Slate Dark)
COLOR_BG_MAIN = ("#FAF9F5", "#0b0f19")
COLOR_BG_CARD = ("#FFFFFF", "#1e293b")
COLOR_BORDER = ("#E8E6DF", "#334155")
COLOR_TEXT_MAIN = ("#1C1917", "#F8FAFC")
COLOR_TEXT_MUTED = ("#57534E", "#94A3B8")
COLOR_TEXT_DIM = ("#78716C", "#64748B")
COLOR_CLAUDE_AMBER = ("#D97706", "#F59E0B")
COLOR_CLAUDE_HOVER = ("#B45309", "#D97706")
COLOR_STAT_BOX = ("#F5F4EF", "#0f172a")
COLOR_EMERALD = ("#059669", "#10B981")
COLOR_EMERALD_HOVER = ("#047857", "#059669")
COLOR_NORMAL_TXT = ("#047857", "#34D399")
COLOR_NORMAL_BG = ("#ECFDF5", "#064E3B")

class LoginSceneFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success, current_theme="light", initial_mode="home"):
        super().__init__(master, fg_color="transparent")
        self.on_login_success = on_login_success
        self.current_theme = current_theme
        self.auth_mgr = auth_system.AuthManager()

        self.selected_mode = tk.StringVar(value=initial_mode)
        self.show_advanced_key = tk.BooleanVar(value=(initial_mode == "hospital"))

        self.create_widgets()
        self.switch_mode(initial_mode)

    def create_widgets(self):
        # Center card container
        self.center_box = ctk.CTkFrame(
            self, 
            fg_color=COLOR_BG_CARD, 
            corner_radius=20, 
            border_width=1, 
            border_color=COLOR_BORDER,
            width=580
        )
        self.center_box.pack(expand=True, pady=30, padx=20)

        # 1. Header & Branding
        top_box = ctk.CTkFrame(self.center_box, fg_color="transparent")
        top_box.pack(fill="x", padx=28, pady=(26, 12))

        logo_lbl = ctk.CTkLabel(
            top_box,
            text="Ψ",
            font=ctk.CTkFont(family="Inter", size=30, weight="bold"),
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_STAT_BOX,
            corner_radius=22,
            width=48,
            height=48
        )
        logo_lbl.pack(pady=(0, 6))

        ctk.CTkLabel(
            top_box,
            text="Smart Ward & Home Health",
            font=ctk.CTkFont(family="Inter", size=22, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack()

        ctk.CTkLabel(
            top_box,
            text="Live Heart Telemetry, Vitals & Emergency SOS Network",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLOR_TEXT_MUTED
        ).pack(pady=(2, 0))

        # 2. Mode Selector Tabs (3 Big Friendly Buttons)
        mode_box = ctk.CTkFrame(self.center_box, fg_color=COLOR_STAT_BOX, corner_radius=12)
        mode_box.pack(fill="x", padx=28, pady=(10, 14))

        mode_header = ctk.CTkFrame(mode_box, fg_color="transparent")
        mode_header.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            mode_header,
            text="SELECT OPERATION MODE:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_DIM
        ).pack(side="left")

        mode_btn_row = ctk.CTkFrame(mode_box, fg_color="transparent")
        mode_btn_row.pack(fill="x", padx=12, pady=(0, 10))

        # Home Mode Button
        self.btn_mode_home = ctk.CTkButton(
            mode_btn_row,
            text="🏡 Home Care",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            text_color="#FFFFFF",
            hover_color=COLOR_CLAUDE_HOVER,
            border_width=1,
            border_color=COLOR_CLAUDE_AMBER,
            height=38,
            corner_radius=8,
            command=lambda: self.switch_mode("home")
        )
        self.btn_mode_home.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Bedside Patient Mode Button
        self.btn_mode_user = ctk.CTkButton(
            mode_btn_row,
            text="👤 Bedside",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_BG_CARD,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=38,
            corner_radius=8,
            command=lambda: self.switch_mode("user")
        )
        self.btn_mode_user.pack(side="left", fill="x", expand=True, padx=(4, 4))

        # Hospital Mode Button
        self.btn_mode_hospital = ctk.CTkButton(
            mode_btn_row,
            text="🏥 Hospital ICU",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=COLOR_BG_CARD,
            text_color=COLOR_TEXT_MAIN,
            hover_color=COLOR_BORDER,
            border_width=1,
            border_color=COLOR_BORDER,
            height=38,
            corner_radius=8,
            command=lambda: self.switch_mode("hospital")
        )
        self.btn_mode_hospital.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # 3. Active Mode Description & Profile Card
        self.info_card = ctk.CTkFrame(self.center_box, fg_color=COLOR_STAT_BOX, corner_radius=12)
        self.info_card.pack(fill="x", padx=28, pady=(0, 14))

        i_inner = ctk.CTkFrame(self.info_card, fg_color="transparent")
        i_inner.pack(fill="x", padx=16, pady=12)

        self.lbl_profile_pill = ctk.CTkLabel(
            i_inner,
            text="🏡 HOME HEALTHCARE PROFILE: Eleanor Vance",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_NORMAL_TXT,
            fg_color=COLOR_NORMAL_BG,
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.lbl_profile_pill.pack(anchor="w", pady=(0, 4))

        self.lbl_mode_desc = ctk.CTkLabel(
            i_inner,
            text="Calm domestic vitals tracking, resting heart rate, and 1-click caregiver emergency alert.",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="left",
            wraplength=480
        )
        self.lbl_mode_desc.pack(anchor="w")

        # 4. Error / Alert Box (Hidden initially)
        self.alert_frame = ctk.CTkFrame(self.center_box, fg_color=("#FEF2F2", "#7F1D1D"), corner_radius=8)
        self.lbl_alert = ctk.CTkLabel(
            self.alert_frame,
            text="⚠️ Invalid 10-Digit Code",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#DC2626"
        )
        self.lbl_alert.pack(padx=12, pady=6)

        # 5. Primary 1-Click Action Button (Large, Clean, Welcoming)
        self.btn_submit = ctk.CTkButton(
            self.center_box,
            text="✨ Open Home Health Dashboard →",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            command=self.submit_login
        )
        self.btn_submit.pack(fill="x", padx=28, pady=(4, 10))

        # 6. Advanced / Custom Key Drawer (Discreet & Expandable)
        self.key_drawer_container = ctk.CTkFrame(self.center_box, fg_color="transparent")
        self.key_drawer_container.pack(fill="x", padx=28, pady=(0, 18))

        self.btn_toggle_key = ctk.CTkButton(
            self.key_drawer_container,
            text="🔑 Security Key: 5050-8012-34  (Change Key ▾)",
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="transparent",
            text_color=COLOR_TEXT_DIM,
            hover_color=COLOR_STAT_BOX,
            height=24,
            corner_radius=6,
            command=self.toggle_key_drawer
        )
        self.btn_toggle_key.pack(anchor="center")

        # Hidden expandable input frame
        self.key_input_frame = ctk.CTkFrame(self.key_drawer_container, fg_color=COLOR_STAT_BOX, corner_radius=8)

        k_row = ctk.CTkFrame(self.key_input_frame, fg_color="transparent")
        k_row.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            k_row,
            text="10-Digit Key:",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(side="left", padx=(0, 8))

        self.code_entry = ctk.CTkEntry(
            k_row,
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            height=34,
            placeholder_text="XXXX-XXXX-XX",
            text_color=COLOR_CLAUDE_AMBER,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER
        )
        self.code_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.code_entry.bind("<KeyRelease>", self.on_code_typed)

        ctk.CTkButton(
            k_row,
            text="Apply",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER,
            hover_color=COLOR_CLAUDE_HOVER,
            width=65,
            height=34,
            corner_radius=6,
            command=self.submit_login
        ).pack(side="right")

    def toggle_key_drawer(self):
        is_visible = self.key_input_frame.winfo_viewable()
        if is_visible:
            self.key_input_frame.pack_forget()
            code = self.code_entry.get().strip()
            self.btn_toggle_key.configure(text=f"🔑 Security Key: {code}  (Change Key ▾)")
        else:
            self.key_input_frame.pack(fill="x", pady=(6, 0))
            self.btn_toggle_key.configure(text="🔑 Custom 10-Digit Security Key  (Close ▴)")

    def switch_mode(self, mode):
        self.selected_mode.set(mode)
        # Reset tab button styles
        for btn in (self.btn_mode_home, self.btn_mode_user, self.btn_mode_hospital):
            btn.configure(fg_color=COLOR_BG_CARD, text_color=COLOR_TEXT_MAIN, border_color=COLOR_BORDER)

        if mode == "home":
            self.btn_mode_home.configure(fg_color=COLOR_CLAUDE_AMBER, text_color="#FFFFFF", border_color=COLOR_CLAUDE_AMBER)
            self.lbl_profile_pill.configure(
                text="🏡 HOME HEALTHCARE: Eleanor Vance",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.lbl_mode_desc.configure(
                text="Daily wellness tracking, gentle resting ECG, and direct 1-click caregiver emergency calling."
            )
            self.btn_submit.configure(
                text="✨ Open Home Health Dashboard →",
                fg_color=COLOR_CLAUDE_AMBER,
                hover_color=COLOR_CLAUDE_HOVER
            )
            self.code_entry.delete(0, "end")
            self.code_entry.insert(0, "5050-8012-34")
            self.btn_toggle_key.configure(text="🔑 Security Key: 5050-8012-34  (Change Key ▾)")

        elif mode == "user":
            self.btn_mode_user.configure(fg_color=COLOR_CLAUDE_AMBER, text_color="#FFFFFF", border_color=COLOR_CLAUDE_AMBER)
            self.lbl_profile_pill.configure(
                text="👤 BEDSIDE PATIENT: Robert Jenkins (Room 402, Bed 03)",
                text_color=COLOR_NORMAL_TXT,
                fg_color=COLOR_NORMAL_BG
            )
            self.lbl_mode_desc.configure(
                text="Live bedside cardiac telemetry, P-Q-R-S-T wave monitor, and nurse call assistance."
            )
            self.btn_submit.configure(
                text="✨ Open Bedside Patient Console →",
                fg_color=COLOR_CLAUDE_AMBER,
                hover_color=COLOR_CLAUDE_HOVER
            )
            self.code_entry.delete(0, "end")
            self.code_entry.insert(0, "1010-8024-55")
            self.btn_toggle_key.configure(text="🔑 Security Key: 1010-8024-55  (Change Key ▾)")

        else: # hospital
            self.btn_mode_hospital.configure(fg_color=COLOR_CLAUDE_AMBER, text_color="#FFFFFF", border_color=COLOR_CLAUDE_AMBER)
            self.lbl_profile_pill.configure(
                text="🏥 ICU COMMAND: Dr. A. Vance, MD (Chief Director)",
                text_color=COLOR_CLAUDE_AMBER,
                fg_color=("#FEF3C7", "#78350F")
            )
            self.lbl_mode_desc.configure(
                text="Full clinical ICU telemetry command, automated dispatch gateways, softphone intercom & triage."
            )
            self.btn_submit.configure(
                text="✨ Open Hospital Command Console →",
                fg_color=COLOR_CLAUDE_AMBER,
                hover_color=COLOR_CLAUDE_HOVER
            )
            self.code_entry.delete(0, "end")
            self.code_entry.insert(0, "7070-2031-23")
            self.btn_toggle_key.configure(text="🔑 Security Key: 7070-2031-23  (Change Key ▾)")

        self.hide_error()

    def on_code_typed(self, event):
        val = self.code_entry.get()
        digits = auth_system.normalize_10_digit_code(val)
        if len(digits) > 10:
            digits = digits[:10]
        formatted = auth_system.format_10_digit_code(digits)
        if val != formatted:
            self.code_entry.delete(0, "end")
            self.code_entry.insert(0, formatted)

    def show_error(self, message):
        self.lbl_alert.configure(text=f"⚠️ {message}")
        self.alert_frame.pack(fill="x", padx=28, pady=(0, 10), before=self.btn_submit)

    def hide_error(self):
        if self.alert_frame.winfo_viewable():
            self.alert_frame.pack_forget()

    def submit_login(self):
        code = self.code_entry.get().strip()
        mode = self.selected_mode.get()
        try:
            session = self.auth_mgr.validate_and_authenticate(code, selected_mode=mode)
            self.hide_error()
            if self.on_login_success:
                self.on_login_success(session)
        except ValueError as err:
            self.show_error(str(err))

    def quick_one_click_access(self):
        self.submit_login()
