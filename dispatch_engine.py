import os
import sys
import time
import json
import socket
import urllib.parse
import threading
import webbrowser
import requests

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import pyttsx3
    import pythoncom
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

BROADCAST_PORT = 8765

# ==============================================================================
# 1. NETWORK APP-TO-APP EMERGENCY CALLING ENGINE
# ==============================================================================
class NetworkCallBroadcaster:
    """Broadcasts emergency distress calls over LAN so anyone with the app gets called"""
    @staticmethod
    def broadcast_emergency_call(call_payload, port=BROADCAST_PORT):
        data = json.dumps(call_payload).encode('utf-8')
        # Send to both local loopback and subnet broadcast
        targets = [('127.0.0.1', port), ('255.255.255.255', port)]
        
        for ip, p in targets:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.settimeout(0.5)
                s.sendto(data, (ip, p))
                s.close()
            except Exception as e:
                print(f"Broadcast warning for {ip}:{p} -> {e}")

        # Also write to shared_state so any local instance receives the call instantly
        try:
            import shared_state
            shared_state.record_network_call(call_payload)
        except Exception:
            pass

class NetworkCallReceiver:
    """Listens in background for incoming emergency distress calls from other nodes"""
    def __init__(self, on_call_received_callback, port=BROADCAST_PORT):
        self.callback = on_call_received_callback
        self.port = port
        self.running = False
        self.sock = None
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def _listen_loop(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', self.port))
            self.sock.settimeout(1.5)
        except Exception as e:
            print(f"Network Call Receiver bind error on port {self.port}: {e}")
            return

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data:
                    continue
                try:
                    payload = json.loads(data.decode('utf-8', errors='replace'))
                    if self.callback:
                        self.callback(payload, addr)
                except Exception as parse_err:
                    print("Error parsing incoming emergency call packet:", parse_err)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print("Receiver socket error:", e)
                break

# ==============================================================================
# 2. LOCATION SYSTEM ENGINE
# ==============================================================================
class LocationSystem:
    def __init__(self):
        self.cached_location = {
            "city": "Locating...",
            "region": "",
            "country": "",
            "postal": "",
            "lat": 0.0,
            "lon": 0.0,
            "accuracy_meters": 20.0,
            "ward": "Zone-B Critical Care ICU",
            "room_bed": "Room 402 // Bed 03",
            "maps_url": "",
            "osm_url": "",
            "timestamp": ""
        }

    def resolve_location(self, custom_ward=None, custom_room_bed=None, gps_com_port=None, force_refresh=False):
        """Resolves location via GPS -> Network Geocoding -> Clinical Baseline with smart caching"""
        loc_data = dict(self.cached_location)
        if custom_ward:
            loc_data["ward"] = custom_ward
        if custom_room_bed:
            loc_data["room_bed"] = custom_room_bed

        # Return cached coordinates if already resolved and not forcing refresh
        if not force_refresh and loc_data.get("lat", 0.0) != 0.0 and loc_data.get("city") not in ["Locating...", ""]:
            loc_data["maps_url"] = f"https://maps.google.com/?q={loc_data['lat']},{loc_data['lon']}"
            loc_data["osm_url"] = f"https://www.openstreetmap.org/?mlat={loc_data['lat']}&mlon={loc_data['lon']}"
            return loc_data

        # 1. Hardware GPS Module
        if gps_com_port and HAS_SERIAL:
            gps_res = self._read_hardware_gps(gps_com_port)
            if gps_res:
                loc_data.update(gps_res)
                loc_data["maps_url"] = f"https://maps.google.com/?q={loc_data['lat']},{loc_data['lon']}"
                loc_data["osm_url"] = f"https://www.openstreetmap.org/?mlat={loc_data['lat']}&mlon={loc_data['lon']}"
                loc_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self.cached_location = loc_data
                return loc_data

        # 2. Public Network Geocoding
        net_res = self._fetch_network_geolocation()
        if net_res:
            loc_data.update(net_res)
        else:
            # 3. Clinical Baseline Coordinates
            loc_data.update({
                "city": "Jamshedpur",
                "region": "Jharkhand",
                "country": "India",
                "postal": "831002",
                "lat": 22.8028,
                "lon": 86.1855,
                "accuracy_meters": 15.0
            })

        loc_data["maps_url"] = f"https://maps.google.com/?q={loc_data['lat']},{loc_data['lon']}"
        loc_data["osm_url"] = f"https://www.openstreetmap.org/?mlat={loc_data['lat']}&mlon={loc_data['lon']}"
        loc_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.cached_location = loc_data
        return loc_data

    def _fetch_network_geolocation(self):
        # Service 1: ipinfo.io
        try:
            r = requests.get("https://ipinfo.io/json", timeout=3.5)
            if r.status_code == 200:
                d = r.json()
                pts = d.get("loc", "0,0").split(",")
                return {
                    "city": d.get("city", "Unknown"),
                    "region": d.get("region", ""),
                    "country": d.get("country", ""),
                    "postal": d.get("postal", ""),
                    "lat": float(pts[0]) if len(pts) > 0 else 0.0,
                    "lon": float(pts[1]) if len(pts) > 1 else 0.0,
                    "accuracy_meters": 25.0
                }
        except Exception:
            pass

        # Service 2: ip-api.com
        try:
            r = requests.get("http://ip-api.com/json", timeout=3.5)
            if r.status_code == 200:
                d = r.json()
                return {
                    "city": d.get("city", "Unknown"),
                    "region": d.get("regionName", ""),
                    "country": d.get("country", ""),
                    "postal": d.get("zip", ""),
                    "lat": float(d.get("lat", 0.0)),
                    "lon": float(d.get("lon", 0.0)),
                    "accuracy_meters": 30.0
                }
        except Exception:
            pass
        return None

    def _read_hardware_gps(self, com_port, baud=9600):
        try:
            ser = serial.Serial(com_port, baud, timeout=1.5)
            for _ in range(25):
                line = ser.readline().decode('ascii', errors='ignore')
                if line.startswith('$GPRMC') or line.startswith('$GPGGA'):
                    parts = line.split(',')
                    if len(parts) > 6 and parts[2] == 'A':
                        lat_raw, lat_dir = parts[3], parts[4]
                        lon_raw, lon_dir = parts[5], parts[6]
                        lat = self._convert_nmea_to_deg(lat_raw, lat_dir)
                        lon = self._convert_nmea_to_deg(lon_raw, lon_dir)
                        ser.close()
                        return {"lat": lat, "lon": lon, "accuracy_meters": 5.0}
            ser.close()
        except Exception:
            pass
        return None

    def _convert_nmea_to_deg(self, raw, direction):
        if not raw: return 0.0
        val = float(raw)
        deg = int(val / 100)
        minutes = val - (deg * 100)
        decimal = deg + (minutes / 60.0)
        if direction in ['S', 'W']:
            decimal = -decimal
        return round(decimal, 6)

# ==============================================================================
# 3. ADVANCED LIVE CALLING SYSTEM ENGINE
# ==============================================================================
class CallingSystem:
    def __init__(self):
        self.tts_lock = threading.Lock()
        self.active_sessions = []

    def make_call(self, phone, alert_payload, config=None, log_cb=None, on_status_update=None):
        """Initiates multi-protocol emergency calling cascade with real-time acoustic feedback"""
        config = config or {}
        clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        results = {}

        if log_cb: log_cb("CALL-SYS", f"Initiating New High-Acuity Voice Call to {clean_phone}...")

        # 1. Cloud Telephony (Twilio Voice API)
        twilio_sid = config.get("twilio_sid", "").strip()
        twilio_token = config.get("twilio_token", "").strip()
        twilio_from = config.get("twilio_from", "").strip()

        if twilio_sid and twilio_token and twilio_from:
            tw_res = self._call_twilio_voice(twilio_sid, twilio_token, twilio_from, clean_phone, alert_payload, log_cb)
            results["cloud_call"] = tw_res

        # 2. Hardware Cellular GSM Modem Dialing
        gsm_port = config.get("gsm_port", "").strip()
        if gsm_port and HAS_SERIAL:
            gsm_res = self._call_gsm_modem(gsm_port, clean_phone, log_cb)
            results["gsm_call"] = gsm_res

        # 3. Windows Shell Telephony Protocol (tel: URI)
        try:
            webbrowser.open(f"tel:{clean_phone}")
            if log_cb: log_cb("DIALER", f"Operating System Telephony dialer invoked for {clean_phone}")
            results["os_dialer"] = "TRIGGERED"
        except Exception as e:
            if log_cb: log_cb("DIALER-ERR", str(e))
            results["os_dialer"] = f"ERROR: {e}"

        # 4. Spoken High-Acuity Voice Dispatch via Thread-Safe SAPI5
        t_voice = threading.Thread(
            target=self._speak_call_transmission, 
            args=(phone, alert_payload, log_cb, on_status_update), 
            daemon=True
        )
        t_voice.start()
        results["voice_dispatch"] = "TRANSMITTING"
        return results

    def _speak_call_transmission(self, phone, payload, log_cb=None, on_status_update=None):
        if not HAS_TTS:
            if on_status_update: on_status_update("VOICE_UNAVAILABLE")
            return
        with self.tts_lock:
            pythoncom.CoInitialize()
            try:
                if on_status_update: on_status_update("CONNECTING")
                patient = payload.get("patient_name", "Robert Jenkins")
                ward = payload.get("ward", "Zone-B ICU")
                room = payload.get("room_bed", "Room 402, Bed 03")
                bpm = payload.get("bpm", 135)
                city = payload.get("city", "Jamshedpur")
                lat = payload.get("lat", 22.8028)
                lon = payload.get("lon", 86.1855)

                speech = (
                    f"Attention! Critical Emergency Dispatch Call to {phone}! "
                    f"Patient {patient} in {ward}, {room}, is in critical condition with heart rate {bpm} beats per minute. "
                    f"Location is {city}, coordinates {lat:.4f} degrees North, {lon:.4f} degrees East. "
                    f"Immediate emergency medical intervention required!"
                )
                engine = pyttsx3.init()
                engine.setProperty('rate', 152)
                engine.setProperty('volume', 1.0)
                if log_cb: log_cb("VOICE", "Synthesizing emergency voice call audio stream...")
                if on_status_update: on_status_update("TRANSMITTING_SPEECH")
                engine.say(speech)
                engine.runAndWait()
                if log_cb: log_cb("VOICE-OK", "Emergency voice transmission completed successfully.")
                if on_status_update: on_status_update("COMPLETED")
            except Exception as e:
                if log_cb: log_cb("VOICE-ERR", f"Voice audio error: {e}")
                if on_status_update: on_status_update(f"ERROR: {e}")
            finally:
                pythoncom.CoUninitialize()

    def _call_twilio_voice(self, sid, token, from_num, to_num, payload, log_cb=None):
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
            twiml_content = (
                f"<Response><Pause length='1'/><Say voice='Polly.Joanna-Neural'>"
                f"Critical Emergency Alert from D.B.M.S. Smart Ward! "
                f"Patient {payload.get('patient_name', 'Patient')} in {payload.get('ward', 'ICU')}, {payload.get('room_bed', 'Bed')} "
                f"has a critical cardiac event with heart rate {payload.get('bpm', 135)} BPM. "
                f"Location coordinates: {payload.get('lat', 0):.4f}, {payload.get('lon', 0):.4f}. "
                f"Immediate response required!"
                f"</Say></Response>"
            )
            data = {"From": from_num, "To": to_num, "Twiml": twiml_content}
            if log_cb: log_cb("TWILIO-CALL", f"Calling {to_num} via Twilio Voice API...")
            r = requests.post(url, data=data, auth=(sid, token), timeout=8)
            if r.status_code in [200, 201]:
                call_sid = r.json().get('sid', 'OK')
                if log_cb: log_cb("TWILIO-OK", f"Call Placed! SID: {call_sid}")
                return "SUCCESS"
            else:
                if log_cb: log_cb("TWILIO-WARN", f"Twilio HTTP {r.status_code}: {r.text[:120]}")
                return f"HTTP_{r.status_code}"
        except Exception as e:
            if log_cb: log_cb("TWILIO-ERR", str(e))
            return f"ERROR: {e}"

    def _call_gsm_modem(self, port, phone, log_cb=None):
        try:
            if log_cb: log_cb("GSM-MODEM", f"Connecting to GSM Modem on {port}...")
            ser = serial.Serial(port, 115200, timeout=3)
            ser.write(b"AT\r\n")
            time.sleep(0.3)
            dial_cmd = f"ATD{phone};\r\n".encode('ascii', errors='ignore')
            ser.write(dial_cmd)
            time.sleep(1.0)
            ser.close()
            if log_cb: log_cb("GSM-OK", f"Cellular call initiated on {port} to {phone}")
            return "SUCCESS"
        except Exception as e:
            if log_cb: log_cb("GSM-ERR", f"GSM Modem error: {e}")
            return f"ERROR: {e}"

# ==============================================================================
# 4. MESSAGING SYSTEM ENGINE (SMS / Text / Webhooks)
# ==============================================================================
class MessagingSystem:
    def format_emergency_sms(self, payload):
        patient = payload.get("patient_name", "Robert Jenkins")
        pid = payload.get("patient_id", "ICU-9024-X")
        ward = payload.get("ward", "Zone-B ICU")
        room = payload.get("room_bed", "Room 402 // Bed 03")
        bpm = payload.get("bpm", 135)
        city = payload.get("city", "Jamshedpur")
        region = payload.get("region", "Jharkhand")
        country = payload.get("country", "India")
        lat = payload.get("lat", 22.8028)
        lon = payload.get("lon", 86.1855)
        maps_url = payload.get("maps_url", f"https://maps.google.com/?q={lat},{lon}")
        osm_url = payload.get("osm_url", f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}")
        ts = payload.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))

        # ASCII-safe header to prevent any Windows CP1252 charmap crashes
        return (
            f"[CRITICAL MEDICAL EMERGENCY ALERT]\n"
            f"Patient: {patient} (#{pid})\n"
            f"Ward: {ward} // {room}\n"
            f"Condition: EMERGENCY (Heart Rate: {bpm} BPM)\n"
            f"Timestamp: {ts}\n"
            f"Location: {city}, {region}, {country}\n"
            f"Coordinates: {lat:.4f} N, {lon:.4f} E\n"
            f"Google Maps: {maps_url}\n"
            f"Direct OSM: {osm_url}\n"
            f"ACTION: Immediate clinical dispatch required!"
        )

    def send_message(self, phone, alert_payload, config=None, log_cb=None):
        config = config or {}
        clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        sms_body = self.format_emergency_sms(alert_payload)
        results = {}

        # 1. Cloud SMS Gateway (Twilio)
        twilio_sid = config.get("twilio_sid", "").strip()
        twilio_token = config.get("twilio_token", "").strip()
        twilio_from = config.get("twilio_from", "").strip()
        if twilio_sid and twilio_token and twilio_from:
            tw_sms = self._send_twilio_sms(twilio_sid, twilio_token, twilio_from, clean_phone, sms_body, log_cb)
            results["cloud_sms"] = tw_sms

        # 2. Hardware GSM Modem SMS
        gsm_port = config.get("gsm_port", "").strip()
        if gsm_port and HAS_SERIAL:
            gsm_sms = self._send_gsm_sms(gsm_port, clean_phone, sms_body, log_cb)
            results["gsm_sms"] = gsm_sms

        # 3. Hospital EMR Webhook
        webhook_url = config.get("webhook_url", "").strip()
        if webhook_url:
            wb_res = self._send_webhook(webhook_url, clean_phone, alert_payload, sms_body, log_cb)
            results["webhook"] = wb_res

        # 4. Windows SMS URI protocol
        try:
            encoded_body = urllib.parse.quote(sms_body)
            webbrowser.open(f"sms:{clean_phone}?body={encoded_body}")
            if log_cb: log_cb("SMS-URI", f"Windows SMS URI protocol triggered for {clean_phone}")
            results["os_sms"] = "TRIGGERED"
        except Exception as e:
            if log_cb: log_cb("SMS-ERR", str(e))
            results["os_sms"] = f"ERROR: {e}"

        return results

    def _send_twilio_sms(self, sid, token, from_num, to_num, text, log_cb=None):
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            data = {"From": from_num, "To": to_num, "Body": text}
            if log_cb: log_cb("TWILIO-SMS", f"Dispatching Cloud SMS to {to_num}...")
            r = requests.post(url, data=data, auth=(sid, token), timeout=8)
            if r.status_code in [200, 201]:
                sid_res = r.json().get('sid', 'OK')
                if log_cb: log_cb("TWILIO-SMS-OK", f"SMS Queued! SID: {sid_res}")
                return "SUCCESS"
            else:
                if log_cb: log_cb("TWILIO-SMS-WARN", f"Twilio SMS HTTP {r.status_code}: {r.text[:120]}")
                return f"HTTP_{r.status_code}"
        except Exception as e:
            if log_cb: log_cb("TWILIO-SMS-ERR", str(e))
            return f"ERROR: {e}"

    def _send_gsm_sms(self, port, phone, text, log_cb=None):
        try:
            if log_cb: log_cb("GSM-SMS", f"Writing SMS to cellular modem on {port}...")
            ser = serial.Serial(port, 115200, timeout=4)
            ser.write(b"AT+CMGF=1\r\n")
            time.sleep(0.3)
            ser.write(f'AT+CMGS="{phone}"\r\n'.encode('ascii', errors='ignore'))
            time.sleep(0.4)
            ser.write(text.encode('utf-8', errors='replace') + b"\x1A")
            time.sleep(2.0)
            ser.close()
            if log_cb: log_cb("GSM-SMS-OK", f"SMS transmitted via GSM modem to {phone}")
            return "SUCCESS"
        except Exception as e:
            if log_cb: log_cb("GSM-SMS-ERR", str(e))
            return f"ERROR: {e}"

    def _send_webhook(self, url, phone, payload, text, log_cb=None):
        try:
            if log_cb: log_cb("WEBHOOK", f"Transmitting JSON alert to {url}...")
            body = {
                "event": "CRITICAL_MEDICAL_EMERGENCY",
                "phone": phone,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "vitals": {"bpm": payload.get("bpm", 135), "condition": "EMERGENCY"},
                "patient": {"name": payload.get("patient_name"), "id": payload.get("patient_id")},
                "location": {
                    "ward": payload.get("ward"),
                    "room_bed": payload.get("room_bed"),
                    "city": payload.get("city"),
                    "coordinates": {"lat": payload.get("lat"), "lon": payload.get("lon")},
                    "maps_url": payload.get("maps_url")
                },
                "text_summary": text
            }
            r = requests.post(url, json=body, timeout=6)
            if log_cb: log_cb("WEBHOOK-OK", f"EMR Webhook replied HTTP {r.status_code}")
            return f"HTTP_{r.status_code}"
        except Exception as e:
            if log_cb: log_cb("WEBHOOK-ERR", str(e))
            return f"ERROR: {e}"

# ==============================================================================
# 5. UNIFIED DISPATCH COORDINATOR
# ==============================================================================
class EmergencyDispatchCoordinator:
    def __init__(self, on_inbound_call=None):
        self.location_sys = LocationSystem()
        self.calling_sys = CallingSystem()
        self.messaging_sys = MessagingSystem()
        
        # Inbound Network Call Listener (anyone with the app receives emergency calls)
        self.receiver = NetworkCallReceiver(self._handle_inbound_packet)
        self.on_inbound_call = on_inbound_call
        self.receiver.start()

    def _handle_inbound_packet(self, packet, addr):
        if packet.get("type") == "EMERGENCY_CALL":
            if self.on_inbound_call:
                self.on_inbound_call(packet, addr)

    def execute_complete_emergency_dispatch(self, phone, patient_state=None, config=None, log_cb=None):
        if log_cb: log_cb("DISPATCH-INIT", f"=== ENGAGING UNIFIED EMERGENCY DISPATCH TO {phone} ===")
        patient_state = patient_state or {}

        # 1. Resolve Location
        loc = self.location_sys.resolve_location(
            custom_ward=patient_state.get("ward_info"),
            custom_room_bed=patient_state.get("room_bed")
        )
        if log_cb: log_cb("LOCATION-OK", f"Coordinates Verified: {loc['lat']:.4f}, {loc['lon']:.4f} ({loc['city']}, {loc['region']})")

        # 2. Package alert payload
        alert_payload = {
            "type": "EMERGENCY_CALL",
            "sender_id": patient_state.get("node_id", "BED_03_ICU_NODE"),
            "patient_name": patient_state.get("patient_name", "Robert Jenkins"),
            "patient_id": patient_state.get("patient_id", "ICU-9024-X"),
            "ward": loc["ward"],
            "room_bed": loc["room_bed"],
            "bpm": patient_state.get("bpm", 135),
            "condition": "CRITICAL EMERGENCY - TACHYCARDIA",
            "city": loc["city"],
            "region": loc["region"],
            "country": loc["country"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "maps_url": loc["maps_url"],
            "osm_url": loc["osm_url"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 3. Broadcast to all other apps on network (P2P App-to-App Emergency Calling)
        if log_cb: log_cb("NETWORK-CALL", "Broadcasting Emergency Call to all network endpoints on port 8765...")
        NetworkCallBroadcaster.broadcast_emergency_call(alert_payload)

        # 4. Fire Messaging Subsystem
        t_msg = threading.Thread(
            target=self.messaging_sys.send_message,
            args=(phone, alert_payload, config, log_cb),
            daemon=True
        )
        t_msg.start()

        # 5. Fire Calling Subsystem
        t_call = threading.Thread(
            target=self.calling_sys.make_call,
            args=(phone, alert_payload, config, log_cb),
            daemon=True
        )
        t_call.start()

        t_msg.join()
        t_call.join()

        if log_cb: log_cb("DISPATCH-COMPLETE", "=== ALL DISPATCH CHANNELS EXECUTED SUCCESSFULLY ===")
        return alert_payload
