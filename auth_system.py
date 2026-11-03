"""
D.B.M.S. Smart Ward ICU - Authentication & Mode Authorization Manager
Supports 10-digit security keys, role-based access control (User Mode vs. Hospital Mode),
and session management.
"""

import re
import json
import time
from pathlib import Path

# Pre-seeded official 10-digit authorization codes
OFFICIAL_KEYS = {
    # Home & Family Care Mode Keys
    "5050801234": {
        "code": "5050801234",
        "formatted": "5050-8012-34",
        "role": "home",
        "role_label": "Home Healthcare & Family Caregiver",
        "user_name": "Eleanor Vance (Home Care)",
        "facility": "Private Residence - Family Suite",
        "ward": "Living Room / Bedroom Suite"
    },
    "2020519288": {
        "code": "2020519288",
        "formatted": "2020-5192-88",
        "role": "home",
        "role_label": "Home Telehealth Caregiver",
        "user_name": "Sarah Connor (Family Care)",
        "facility": "Private Residence - Master Bedroom",
        "ward": "Home Telehealth Area"
    },
    # Hospital / Clinical Command Mode Keys
    "7070203123": {
        "code": "7070203123",
        "formatted": "7070-2031-23",
        "role": "hospital",
        "role_label": "Hospital ICU Command & Chief Director",
        "user_name": "Dr. A. Vance, MD (ICU Chief)",
        "facility": "D.B.M.S. Central Medical Command",
        "ward": "Zone-B Critical Care ICU"
    },
    "9090402112": {
        "code": "9090402112",
        "formatted": "9090-4021-12",
        "role": "hospital",
        "role_label": "Senior Attending Trauma Physician",
        "user_name": "Dr. Sarah Lin, MD (Trauma Team)",
        "facility": "D.B.M.S. Trauma Emergency Center",
        "ward": "ICU Acute Ward Alpha"
    },
    # User / Bedside Patient Mode Keys
    "1010802455": {
        "code": "1010802455",
        "formatted": "1010-8024-55",
        "role": "user",
        "role_label": "Bedside Patient Telemetry",
        "user_name": "Robert Jenkins",
        "facility": "Patient Ward - Bed 03",
        "ward": "Zone-B ICU // Room 402, Bed 03"
    }
}

def normalize_10_digit_code(raw_code: str) -> str:
    """Strips all non-digit characters to return clean 10-digit string"""
    if not raw_code:
        return ""
    digits = re.sub(r'\D', '', str(raw_code))
    return digits

def format_10_digit_code(digits: str) -> str:
    """Formats digits into XXXX-XXXX-XX pattern"""
    digits = normalize_10_digit_code(digits)
    if len(digits) <= 4:
        return digits
    elif len(digits) <= 8:
        return f"{digits[:4]}-{digits[4:]}"
    else:
        return f"{digits[:4]}-{digits[4:8]}-{digits[8:10]}"

class AuthManager:
    def __init__(self):
        self.keys = dict(OFFICIAL_KEYS)
        self.current_session = None

    def validate_and_authenticate(self, code_input: str, selected_mode: str = "home") -> dict:
        """
        Validates 10-digit authorization key and authenticates into Home, User, or Hospital mode.
        Accepts pre-seeded official keys or any valid 10-digit key.
        """
        clean_code = normalize_10_digit_code(code_input)
        
        if len(clean_code) != 10:
            raise ValueError(f"Authorization key must be exactly 10 digits. Current: {len(clean_code)} digits.")

        # Check official database
        if clean_code in self.keys:
            entry = dict(self.keys[clean_code])
            # If the user explicitly chose a mode, adapt the role
            if selected_mode in ["home", "user", "hospital"]:
                entry["role"] = selected_mode
        else:
            # Custom 10-digit key registration on the fly
            if selected_mode == "home":
                entry = {
                    "code": clean_code,
                    "formatted": format_10_digit_code(clean_code),
                    "role": "home",
                    "role_label": "Home Healthcare & Family Caregiver",
                    "user_name": "Family Member / Caregiver",
                    "facility": "Private Residence",
                    "ward": "Living Room / Bedroom Suite"
                }
            elif selected_mode == "user":
                entry = {
                    "code": clean_code,
                    "formatted": format_10_digit_code(clean_code),
                    "role": "user",
                    "role_label": "Bedside Patient Telemetry",
                    "user_name": "Patient / Bedside User",
                    "facility": "D.B.M.S. Medical Hospital",
                    "ward": "Room 402 // Bed 03"
                }
            else: # hospital
                entry = {
                    "code": clean_code,
                    "formatted": format_10_digit_code(clean_code),
                    "role": "hospital",
                    "role_label": "Clinical Staff / Doctor",
                    "user_name": "Authorized Medical Officer",
                    "facility": "D.B.M.S. Medical Hospital",
                    "ward": "Zone-B ICU"
                }
            self.keys[clean_code] = entry

        self.current_session = {
            "is_authenticated": True,
            "login_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "role": entry["role"],
            "role_label": entry["role_label"],
            "user_name": entry["user_name"],
            "facility": entry["facility"],
            "ward": entry["ward"],
            "code": entry["code"],
            "formatted_code": entry["formatted"]
        }
        return self.current_session

    def get_session(self):
        return self.current_session

    def logout(self):
        self.current_session = None
