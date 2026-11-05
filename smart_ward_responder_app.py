"""
D.B.M.S. Smart Ward ICU - Caregiver & Doctor Emergency Calling System App
A lightweight standalone mobile/desktop companion app that connects to the
Smart Ward ICU Admin Station, displays live registration, receives instant
emergency calls with loud ringtones, voice announcements, and live softphone intercom.
"""

import os
import sys
import time
import json
import socket
import threading
import webbrowser
import tkinter as tk
import customtkinter as ctk

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

try:
    import pyttsx3
    import pythoncom
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

import responder_registry
import calling_console

# Theme Color Palette (Claude Theme)
COLOR_BG_MAIN = ("#FAF9F5", "#0b0f19")
COLOR_BG_CARD = ("#FFFFFF", "#1e293b")
COLOR_BORDER = ("#E8E6DF", "#334155")
COLOR_TEXT_MAIN = ("#1C1917", "#F8FAFC")
COLOR_TEXT_MUTED = ("#57534E", "#94A3B8")
COLOR_TEXT_DIM = ("#78716C", "#64748B")
COLOR_CLAUDE_AMBER = ("#D97706", "#F59E0B")
COLOR_NORMAL_TXT = ("#059669", "#10B981")
COLOR_NORMAL_BG = ("#ECFDF5", "#064E3B")
COLOR_ALERT_TXT = ("#DC2626", "#EF4444")
COLOR_ALERT_BG = ("#FEF2F2", "#7F1D1D")
COLOR_STAT_BOX = ("#F5F4EF", "#0f172a")

class SmartWardResponderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("Smart Ward ICU - Emergency Calling Companion")
        self.geometry("480x720")
        self.minsize(440, 640)
        self.configure(fg_color=COLOR_BG_MAIN)

        # Set App Icon if present
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "EmergencyDispatcher.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # Load or initialize saved profile
        self.profile_file = os.path.join(os.path.expanduser("~"), ".smart_ward_responder_profile.json")
        self.profile = self.load_profile()

        # Initialize Responder Client Engine
        self.client = responder_registry.ResponderClient(
            device_name=self.profile.get("name", "Caregiver User"),
            role=self.profile.get("role", "Family Caregiver"),
            phone=self.profile.get("phone", "+91 98765 43210")
        )
        self.client.on_call_received = self.handle_incoming_call
        self.client.on_admin_discovered = self.handle_admin_discovered

        self.active_call_dialog = None
        self.ringing_active = False

        # Build UI
        self.create_header_ribbon()
        self.create_profile_card()
        self.create_connection_card()
        self.create_hotline_actions()
        self.create_event_audit_log()

        # Start Client Background Engine
        self.client.start()

        # Periodic UI Refresh (update status pills)
        self.after(1000, self.periodic_ui_refresh)

    # --------------------------------------------------------------------------
    # PROFILE MANAGEMENT
    # --------------------------------------------------------------------------
    def load_profile(self):
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "name": f"Caregiver {socket.gethostname()[:8]}",
            "role": "Family Caregiver",
            "phone": "+91 98765 43210",
            "admin_ip": ""
        }

    def save_profile(self):
        try:
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(self.profile, f, indent=2)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # UI CONSTRUCTION
    # --------------------------------------------------------------------------
    def create_header_ribbon(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        header.pack(fill="x", padx=16, pady=(16, 8))

        row = ctk.CTkFrame(header, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        icon_box = ctk.CTkLabel(
            row, text="📱", font=ctk.CTkFont(size=26), 
            fg_color=COLOR_STAT_BOX, corner_radius=18, width=42, height=42
        )
        icon_box.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(row, fg_color="transparent")
        title_box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            title_box, text="D.B.M.S. RESPONDER FLEET", 
            font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box, text="Emergency Telephony & Caregiver Hotline App", 
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

        self.status_pill = ctk.CTkLabel(
            row, text="🟡 SEARCHING...", 
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_DIM,
            corner_radius=10, padx=10, pady=4
        )
        self.status_pill.pack(side="right")

    def create_profile_card(self):
        card = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            card, text="👤 MY RESPONDER IDENTITY", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=14, pady=(10, 4))

        # Name Entry
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row1, text="Name:", width=60, anchor="w", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.name_entry = ctk.CTkEntry(row1, height=28, font=ctk.CTkFont(size=11))
        self.name_entry.insert(0, self.profile.get("name", "Caregiver Priya"))
        self.name_entry.pack(side="left", fill="x", expand=True)

        # Role Selector
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row2, text="Role:", width=60, anchor="w", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.role_menu = ctk.CTkOptionMenu(
            row2, 
            values=["Family Caregiver", "Attending Doctor", "ICU Specialist", "Bedside Nurse", "Emergency EMT"],
            height=28, font=ctk.CTkFont(size=11),
            fg_color=COLOR_CLAUDE_AMBER, button_color=COLOR_CLAUDE_AMBER
        )
        self.role_menu.set(self.profile.get("role", "Family Caregiver"))
        self.role_menu.pack(side="left", fill="x", expand=True)

        # Phone Entry
        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row3, text="Phone:", width=60, anchor="w", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.phone_entry = ctk.CTkEntry(row3, height=28, font=ctk.CTkFont(size=11))
        self.phone_entry.insert(0, self.profile.get("phone", "+91 98765 43210"))
        self.phone_entry.pack(side="left", fill="x", expand=True)

        btn_save = ctk.CTkButton(
            card, text="💾 Update & Sync My Profile", 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN, hover_color="#E2E8F0",
            height=26, command=self.apply_profile_update
        )
        btn_save.pack(fill="x", padx=14, pady=(6, 10))

    def create_connection_card(self):
        card = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="x", padx=16, pady=6)

        header_box = ctk.CTkFrame(card, fg_color="transparent")
        header_box.pack(fill="x", padx=14, pady=(10, 4))
        
        ctk.CTkLabel(
            header_box, text="🌐 SMART WARD ADMIN LINK", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).pack(side="left")

        self.ip_info_lbl = ctk.CTkLabel(
            header_box, text=f"My IP: {responder_registry.get_local_ip()}:{self.client.call_port}",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_DIM
        )
        self.ip_info_lbl.pack(side="right")

        self.conn_details_lbl = ctk.CTkLabel(
            card, text="Scanning LAN & UDP broadcast for Admin Smart Ward Station...",
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED, anchor="w"
        )
        self.conn_details_lbl.pack(fill="x", padx=14, pady=(2, 6))

        # Manual IP override row if testing across isolated subnets
        override_box = ctk.CTkFrame(card, fg_color="transparent")
        override_box.pack(fill="x", padx=14, pady=(0, 10))
        
        self.admin_ip_entry = ctk.CTkEntry(
            override_box, placeholder_text="Admin IP (Auto-Discovered)", height=26, font=ctk.CTkFont(size=11)
        )
        self.admin_ip_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_connect = ctk.CTkButton(
            override_box, text="Connect", width=70, height=26,
            fg_color=COLOR_CLAUDE_AMBER, font=ctk.CTkFont(size=11, weight="bold"),
            command=self.manual_admin_connect
        )
        btn_connect.pack(side="right")

    def create_hotline_actions(self):
        card = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            card, text="⚡ DIRECT EMERGENCY CONTROLS", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=14, pady=(10, 6))

        # Button to call the ICU Admin Station
        self.btn_call_ward = ctk.CTkButton(
            card, 
            text="📞 Call Smart Ward ICU Station", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_NORMAL_TXT, hover_color="#047857",
            height=38, corner_radius=8,
            command=self.call_ward_station
        )
        self.btn_call_ward.pack(fill="x", padx=14, pady=4)

        # Test Ringtone Button
        btn_test = ctk.CTkButton(
            card, 
            text="🔔 Test Loud Ringtone & Audio Tone", 
            font=ctk.CTkFont(size=11),
            fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN, hover_color="#E2E8F0",
            height=28, corner_radius=6,
            command=self.test_ringtone_audio
        )
        btn_test.pack(fill="x", padx=14, pady=(4, 10))

    def create_event_audit_log(self):
        card = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=(6, 16))

        ctk.CTkLabel(
            card, text="📋 EMERGENCY CALLS & EVENT LOG", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.log_box = ctk.CTkTextbox(
            card, font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN,
            corner_radius=8
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.log_box.configure(state="disabled")

        self.log_event("SYSTEM", "Caregiver Emergency Calling Companion Initialized.")

    def log_event(self, tag: str, msg: str):
        t_str = time.strftime("%H:%M:%S")
        entry = f"[{t_str}] [{tag}] {msg}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", entry)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # --------------------------------------------------------------------------
    # CLIENT ENGINE HANDLERS
    # --------------------------------------------------------------------------
    def apply_profile_update(self):
        name = self.name_entry.get().strip() or "Caregiver User"
        role = self.role_menu.get()
        phone = self.phone_entry.get().strip() or "+91 98765 43210"

        self.profile["name"] = name
        self.profile["role"] = role
        self.profile["phone"] = phone
        self.save_profile()

        self.client.device_name = name
        self.client.role = role
        self.client.phone = phone
        self.log_event("PROFILE", f"Updated profile to {name} ({role})")

    def manual_admin_connect(self):
        ip = self.admin_ip_entry.get().strip()
        if ip:
            self.client.admin_ip = ip
            self.log_event("CONNECT", f"Manually targeting Admin Station IP: {ip}")
            self.conn_details_lbl.configure(text=f"Connecting to Admin Station at {ip}...")

    def safe_after(self, fn):
        try:
            self.after(0, fn)
        except Exception:
            pass

    def handle_admin_discovered(self, admin_ip: str, admin_port: int):
        self.safe_after(lambda: self._update_admin_ui_link(admin_ip, admin_port))

    def _update_admin_ui_link(self, admin_ip: str, admin_port: int):
        self.status_pill.configure(
            text="🟢 ONLINE (FLEET SYNCED)", 
            fg_color=COLOR_NORMAL_BG, text_color=COLOR_NORMAL_TXT
        )
        self.conn_details_lbl.configure(
            text=f"🟢 Synced with Smart Ward Admin Station @ {admin_ip}:{admin_port}"
        )
        self.admin_ip_entry.delete(0, "end")
        self.admin_ip_entry.insert(0, admin_ip)
        self.log_event("LINK-OK", f"Auto-discovered and registered with Admin at {admin_ip}:{admin_port}")

    def periodic_ui_refresh(self):
        """Checks if admin link is alive and updates UI"""
        if self.client.admin_ip:
            self.status_pill.configure(
                text="🟢 ONLINE (FLEET SYNCED)", 
                fg_color=COLOR_NORMAL_BG, text_color=COLOR_NORMAL_TXT
            )
        else:
            self.status_pill.configure(
                text="🟡 SCANNING LAN...", 
                fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_DIM
            )
        self.after(2000, self.periodic_ui_refresh)

    def test_ringtone_audio(self):
        self.log_event("TEST", "Triggering test audio tone sequence...")
        def _play():
            if HAS_SOUND:
                for freq in [880, 1174, 880, 1174, 1318]:
                    winsound.Beep(freq, 120)
                    time.sleep(0.04)
        threading.Thread(target=_play, daemon=True).start()

    def call_ward_station(self):
        if not self.client.admin_ip:
            self.log_event("CALL-ERR", "Cannot call ward: Admin station not yet discovered.")
            return
        self.log_event("CALL-OUT", f"Placing audio call to Smart Ward ICU at {self.client.admin_ip}...")
        success = self.client.call_admin_ward_station("Caregiver Calling Ward Station")
        if success:
            self.log_event("CALL-OK", "Smart Ward ICU station is ringing!")
            # Open softphone console
            calling_console.LiveCallingConsole(
                self,
                recipient_name="Smart Ward ICU Command Station",
                phone_number=self.client.phone,
                alert_payload={"patient_name": "Ward Admin Station", "bpm": 74}
            )
        else:
            self.log_event("CALL-FAIL", "Could not reach Ward Station.")

    # --------------------------------------------------------------------------
    # INCOMING EMERGENCY CALL DIALOG (THE HERO FEATURE)
    # --------------------------------------------------------------------------
    def handle_incoming_call(self, envelope: dict):
        """Thread-safe handler when an incoming emergency call arrives from Admin"""
        self.safe_after(lambda: self._show_incoming_call_popup(envelope))

    def _show_incoming_call_popup(self, envelope: dict):
        if self.active_call_dialog and self.active_call_dialog.winfo_exists():
            return # Already showing

        self.log_event("🚨 CALL", "INCOMING HIGH-PRIORITY EMERGENCY CALL FROM SMART WARD ICU!")
        self.active_call_dialog = IncomingCallAlert(self, envelope, on_accept=self.on_call_accepted)

    def on_call_accepted(self, envelope: dict):
        """When caregiver clicks 'Accept Call', connect to live softphone visualizer"""
        alert = envelope.get("alert", {})
        p_name = alert.get("patient_name", "Eleanor Vance")
        bpm = alert.get("bpm", 138)
        
        self.log_event("CALL-ACTIVE", f"Connected with {p_name} line. Voice channel active.")
        calling_console.LiveCallingConsole(
            self,
            recipient_name=f"Smart Ward ICU ({p_name})",
            phone_number=self.client.phone,
            alert_payload=alert
        )


class IncomingCallAlert(ctk.CTkToplevel):
    """Full-featured high-priority incoming call dialog with ringing audio and TTS readout"""
    def __init__(self, master: SmartWardResponderApp, envelope: dict, on_accept=None):
        super().__init__(master)

        self.app_master = master
        self.envelope = envelope
        self.alert = envelope.get("alert", {})
        self.on_accept = on_accept
        self.ringing = True

        self.title("🚨 INCOMING EMERGENCY CALL")
        self.geometry("460x580")
        self.configure(fg_color=COLOR_BG_MAIN)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.decline_call)

        self.create_ui()

        # Start ringing sound & emergency voice announcement
        threading.Thread(target=self._play_ringing_tones, daemon=True).start()
        threading.Thread(target=self._speak_emergency_announcement, daemon=True).start()

    def create_ui(self):
        container = ctk.CTkFrame(self, fg_color=COLOR_BG_CARD, corner_radius=16, border_width=2, border_color="#DC2626")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Alarm Header Banner
        banner = ctk.CTkLabel(
            container, text="🚨 HIGH-PRIORITY EMERGENCY CALL", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            fg_color=COLOR_ALERT_BG, text_color=COLOR_ALERT_TXT,
            corner_radius=8, pady=8
        )
        banner.pack(fill="x", padx=14, pady=(14, 10))

        # Big Animated Phone Ring Icon
        self.ring_icon = ctk.CTkLabel(
            container, text="📞", font=ctk.CTkFont(size=54),
            fg_color=COLOR_STAT_BOX, corner_radius=40, width=80, height=80
        )
        self.ring_icon.pack(pady=10)

        # Patient & Vitals Display
        p_name = self.alert.get("patient_name", "Eleanor Vance")
        ward = self.alert.get("ward", "Zone-B ICU // Room 402 Bed 03")
        bpm = self.alert.get("bpm", 138)
        city = self.alert.get("city", "Jamshedpur")
        lat = self.alert.get("lat", 22.8028)
        lon = self.alert.get("lon", 86.1855)

        ctk.CTkLabel(
            container, text=p_name, 
            font=ctk.CTkFont(size=20, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).pack()

        ctk.CTkLabel(
            container, text=ward, 
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED
        ).pack(pady=(2, 8))

        # Hero BPM Readout
        bpm_box = ctk.CTkFrame(container, fg_color=COLOR_STAT_BOX, corner_radius=10)
        bpm_box.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(
            bpm_box, text=f"🫀 HEART RATE: {bpm} BPM", 
            font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_ALERT_TXT
        ).pack(pady=6)

        # Location details
        loc_text = f"📍 {city} ({lat:.4f}°, {lon:.4f}°)"
        ctk.CTkLabel(
            container, text=loc_text, 
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_DIM
        ).pack(pady=2)

        maps_url = self.alert.get("maps_url", f"https://www.google.com/maps?q={lat},{lon}")
        btn_map = ctk.CTkButton(
            container, text="🗺️ Open Live GPS Location in Google Maps", 
            font=ctk.CTkFont(size=11), fg_color=COLOR_STAT_BOX, text_color=COLOR_TEXT_MAIN,
            height=26, hover_color="#E2E8F0",
            command=lambda: webbrowser.open(maps_url)
        )
        btn_map.pack(fill="x", padx=14, pady=6)

        # Call Action Buttons (ACCEPT vs ACKNOWLEDGE)
        action_row = ctk.CTkFrame(container, fg_color="transparent")
        action_row.pack(fill="x", padx=14, pady=(16, 12))

        btn_accept = ctk.CTkButton(
            action_row, text="✅ ACCEPT CALL", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_NORMAL_TXT, hover_color="#047857",
            height=44, corner_radius=8,
            command=self.accept_call
        )
        btn_accept.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_ack = ctk.CTkButton(
            action_row, text="🚨 EN-ROUTE", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_CLAUDE_AMBER, hover_color="#B45309",
            height=44, corner_radius=8,
            command=self.acknowledge_en_route
        )
        btn_ack.pack(side="right", fill="x", expand=True, padx=(6, 0))

    def _play_ringing_tones(self):
        """Repeated loud emergency ringing tones"""
        while self.ringing:
            if HAS_SOUND:
                try:
                    winsound.Beep(880, 250)
                    time.sleep(0.08)
                    winsound.Beep(1174, 300)
                    time.sleep(0.8)
                except Exception:
                    time.sleep(1.0)
            else:
                time.sleep(1.0)

    def _speak_emergency_announcement(self):
        """Voice synthesis announcement"""
        if not HAS_TTS:
            return
        pythoncom.CoInitialize()
        try:
            p_name = self.alert.get("patient_name", "Eleanor Vance")
            bpm = self.alert.get("bpm", 138)
            city = self.alert.get("city", "Jamshedpur")
            speech = f"Emergency Alert! Patient {p_name} is experiencing cardiac distress at {bpm} beats per minute in {city}. Response required immediately!"
            engine = pyttsx3.init()
            engine.setProperty('rate', 155)
            engine.say(speech)
            engine.runAndWait()
        except Exception:
            pass
        finally:
            pythoncom.CoUninitialize()

    def accept_call(self):
        self.ringing = False
        # Send Acknowledgment back to Admin
        self.app_master.client.acknowledge_emergency_call(self.alert, "Call Accepted - Live Audio Connected")
        self.destroy()
        if self.on_accept:
            self.on_accept(self.envelope)

    def acknowledge_en_route(self):
        self.ringing = False
        self.app_master.client.acknowledge_emergency_call(self.alert, "Acknowledge Received - Responder Dispatched En-Route")
        self.app_master.log_event("ACK", "Sent confirmation to Admin Station: Responder En-Route!")
        self.destroy()

    def decline_call(self):
        self.ringing = False
        self.destroy()

if __name__ == "__main__":
    app = SmartWardResponderApp()
    app.mainloop()
