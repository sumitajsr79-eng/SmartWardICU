"""
D.B.M.S. Smart Ward ICU - Hardware IoT Bridge
Continuously auto-detects and connects to the Arduino Uno telemetry node
via USB Serial (CH340 / COM3 / COM4) at 115200 BAUD.
Parses live JSON telemetry:
  {"bpm": 74, "gforce": 1.02, "fall": false, "lat": 22.8046, "lng": 86.2029, "sats": 0, "pulse_raw": 342}
Updates shared state and notifies dashboard UI components.
"""

import time
import json
import re
import threading
from typing import Callable, Optional, Dict, Any

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

import shared_state

class HardwareBridge:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.running = False
        self.connected = False
        self.current_port = None
        self.baudrate = 115200
        self.last_packet: Dict[str, Any] = {
            "bpm": 0,
            "gforce": 1.0,
            "fall": False,
            "lat": 22.8046,
            "lng": 86.2029,
            "sats": 0,
            "pulse_raw": 0,
            "timestamp": 0
        }
        self.callbacks = []
        self._thread: Optional[threading.Thread] = None

    def register_callback(self, cb: Callable[[Dict[str, Any]], None]):
        if cb not in self.callbacks:
            self.callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[Dict[str, Any]], None]):
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="HardwareBridgeWorker")
        self._thread.start()

    def stop(self):
        self.running = False

    def _find_target_port(self) -> Optional[str]:
        if not HAS_SERIAL:
            return None
        ports = list(serial.tools.list_ports.comports())
        # First priority: CH340 or Arduino Uno or USB-SERIAL
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if "ch340" in desc or "arduino" in desc or "usb-serial" in desc or "1a86:7523" in hwid:
                return p.device
        # Second priority: COM3 or COM4 if available
        for p in ports:
            if p.device in ["COM3", "COM4"]:
                return p.device
        # Fallback to any USB serial port (exclude bluetooth incoming/outgoing)
        for p in ports:
            desc = (p.description or "").lower()
            if "bluetooth" not in desc and "bt" not in desc:
                return p.device
        return None

    def _worker_loop(self):
        while self.running:
            port_name = self._find_target_port()
            if not port_name:
                self.connected = False
                self.current_port = None
                time.sleep(1.5)
                continue

            try:
                ser = serial.Serial(port_name, self.baudrate, timeout=1.2)
                # Toggle DTR/RTS carefully so we don't hold the board in reset
                ser.dtr = False
                ser.rts = False
                self.connected = True
                self.current_port = port_name
                
                # Update shared state connection
                shared_state.update_hardware_telemetry({
                    "connected": True,
                    "port": port_name
                })

                while self.running and ser.is_open:
                    raw_line = ser.readline()
                    if not raw_line:
                        continue
                    try:
                        line = raw_line.decode('utf-8', errors='ignore').strip()
                    except Exception:
                        continue

                    if not line:
                        continue

                    packet = self._parse_telemetry_line(line)
                    if packet:
                        packet["timestamp"] = time.time()
                        packet["port"] = port_name
                        self.last_packet = packet
                        
                        # Sync into shared state
                        shared_state.update_hardware_telemetry({
                            "connected": True,
                            "port": port_name,
                            "bpm": packet.get("bpm", 0),
                            "gforce": packet.get("gforce", 1.0),
                            "fall": packet.get("fall", False),
                            "lat": packet.get("lat", 22.8046),
                            "lng": packet.get("lng", 86.2029),
                            "sats": packet.get("sats", 0),
                            "pulse_raw": packet.get("pulse_raw", 0)
                        })

                        # Trigger registered listeners
                        for cb in list(self.callbacks):
                            try:
                                cb(packet)
                            except Exception as e:
                                pass

                ser.close()
            except Exception as ex:
                self.connected = False
                self.current_port = None
                shared_state.update_hardware_telemetry({"connected": False, "port": "None"})
                time.sleep(1.5)

    def _parse_telemetry_line(self, line: str) -> Optional[Dict[str, Any]]:
        # 1. JSON format: {"bpm":74,"gforce":1.02,"fall":false,"lat":22.8046,"lng":86.2029,"sats":0,"pulse_raw":342}
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                if "bpm" in data or "gforce" in data:
                    return {
                        "bpm": int(data.get("bpm", 0)),
                        "gforce": float(data.get("gforce", 1.0)),
                        "fall": bool(data.get("fall", False)),
                        "lat": float(data.get("lat", 22.8046)),
                        "lng": float(data.get("lng", 86.2029)),
                        "sats": int(data.get("sats", 0)),
                        "pulse_raw": int(data.get("pulse_raw", 0))
                    }
            except Exception:
                pass

        # 2. Text fallback: [TELEMETRY] HR: 74 BPM | G: 1.02G | Fall: STABLE | GPS: 22.8046, 86.2029 (Sats: 0, Bytes: 71) | A0: 342
        if "[TELEMETRY]" in line:
            try:
                bpm = 0
                if "HR: --" not in line and "HR:" in line:
                    m_hr = re.search(r"HR:\s*(\d+)", line)
                    if m_hr:
                        bpm = int(m_hr.group(1))

                gforce = 1.0
                m_g = re.search(r"G:\s*([\d\.]+)", line)
                if m_g:
                    gforce = float(m_g.group(1))

                fall = "Fall: ALERT" in line

                lat = 22.8046
                lng = 86.2029
                m_gps = re.search(r"GPS:\s*([\d\.-]+),\s*([\d\.-]+)", line)
                if m_gps:
                    lat = float(m_gps.group(1))
                    lng = float(m_gps.group(2))

                sats = 0
                m_sats = re.search(r"Sats:\s*(\d+)", line)
                if m_sats:
                    sats = int(m_sats.group(1))

                pulse_raw = 0
                m_a0 = re.search(r"A0:\s*(\d+)", line)
                if m_a0:
                    pulse_raw = int(m_a0.group(1))

                return {
                    "bpm": bpm,
                    "gforce": gforce,
                    "fall": fall,
                    "lat": lat,
                    "lng": lng,
                    "sats": sats,
                    "pulse_raw": pulse_raw
                }
            except Exception:
                pass

        return None
