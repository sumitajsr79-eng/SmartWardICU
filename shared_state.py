import os
import json
import time
from pathlib import Path

# Common state path in local AppData
APPDATA_DIR = Path(os.environ.get('LOCALAPPDATA', '.')) / 'SmartWardICU'
APPDATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = APPDATA_DIR / 'ward_state.json'
TMP_STATE_FILE = APPDATA_DIR / 'ward_state.json.tmp'

DEFAULT_STATE = {
    "bpm": 74,
    "rhythm": "NORMAL SINUS",
    "is_emergency": False,
    "emergency_cause": "",
    "emergency_timestamp": "",
    "emergency_contact": "+1 (555) 911-0420",
    "patient_name": "Robert Jenkins",
    "patient_id": "ICU-9024-X",
    "ward_info": "Zone-B // Post-Operative ICU",
    "room_bed": "Room 402 // Bed 03",
    "ui_theme": "light",
    "heart_auto_call": True,
    "last_network_call": {},
    "location": {
        "city": "Locating...",
        "region": "",
        "country": "",
        "lat": 0.0,
        "lon": 0.0,
        "postal": "",
        "maps_url": "",
        "last_updated": ""
    },
    "dispatch_status": {
        "call_sent": False,
        "text_sent": False,
        "last_dispatch_time": "",
        "last_log": "System initialized"
    },
    "hardware": {
        "connected": False,
        "port": "None",
        "bpm": 0,
        "gforce": 1.0,
        "fall": False,
        "lat": 22.8046,
        "lng": 86.2029,
        "sats": 0,
        "pulse_raw": 0,
        "last_sync": ""
    }
}

def get_state_path():
    return str(STATE_FILE)

def load_state():
    """Thread-safe and process-safe state loader with automatic fallback"""
    if STATE_FILE.exists():
        for _ in range(5):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        merged = dict(DEFAULT_STATE)
                        merged.update(data)
                        return merged
            except Exception:
                time.sleep(0.02)
    # Default fallback
    save_state(DEFAULT_STATE)
    return dict(DEFAULT_STATE)

def save_state(state):
    """Atomic state saver using tempfile + os.replace to prevent read collisions"""
    try:
        with open(TMP_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(TMP_STATE_FILE, STATE_FILE)
    except Exception as e:
        print(f"Error saving state: {e}")

def update_emergency(is_emergency, cause="Manual SOS"):
    state = load_state()
    state["is_emergency"] = is_emergency
    state["emergency_cause"] = cause if is_emergency else ""
    state["emergency_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S") if is_emergency else ""
    if not is_emergency:
        state["dispatch_status"]["call_sent"] = False
        state["dispatch_status"]["text_sent"] = False
    save_state(state)
    return state

def update_emergency_contact(phone_number):
    state = load_state()
    state["emergency_contact"] = phone_number.strip()
    save_state(state)
    return state

def update_location(loc_dict):
    state = load_state()
    state["location"].update(loc_dict)
    state["location"]["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)
    return state

def update_theme(theme_name):
    state = load_state()
    state["ui_theme"] = theme_name
    save_state(state)
    return state

def update_auto_call(enabled):
    state = load_state()
    state["heart_auto_call"] = bool(enabled)
    save_state(state)
    return state

def record_network_call(packet):
    state = load_state()
    state["last_network_call"] = {
        "packet": packet,
        "timestamp": time.time(),
        "acknowledged": False
    }
    save_state(state)
    return state

def clear_network_call():
    state = load_state()
    state["last_network_call"] = {}
    save_state(state)
    return state

def update_hardware_telemetry(hw_dict):
    state = load_state()
    if "hardware" not in state:
        state["hardware"] = dict(DEFAULT_STATE["hardware"])
    state["hardware"].update(hw_dict)
    state["hardware"]["last_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)
    return state
