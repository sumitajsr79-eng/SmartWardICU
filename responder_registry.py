"""
D.B.M.S. Smart Ward ICU - Responder Fleet & Emergency Calling Registry System
Features:
- Auto-Discovery via UDP Broadcast Beacon (Port 8765)
- Central HTTP Fleet Registry Server on Admin Station (Port 8888)
- Real-time Device Heartbeat & Online Presence Tracking
- Direct App-to-App Emergency Calling Engine (Port 8770)
- Bi-directional Intercom & SOS Acknowledgment
"""

import os
import sys
import time
import json
import socket
import threading
from typing import Dict, Any, List, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse

import shared_state

DISCOVERY_BEACON_PORT = 8765
ADMIN_REGISTRY_PORT = 8888
DEFAULT_RESPONDER_CALL_PORT = 8770

def get_local_ip() -> str:
    """Discovers the active LAN IP address of this machine"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# ==============================================================================
# 1. ADMIN FLEET REGISTRY SERVER (Runs inside Smart Ward Monitor / Dispatcher)
# ==============================================================================
class FleetHTTPRequestHandler(BaseHTTPRequestHandler):
    server: 'ResponderRegistryServer' # Type hint

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP access logs
        pass

    def _send_json_response(self, data: dict, code: int = 200):
        try:
            body = json.dumps(data).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/fleet':
            active = shared_state.get_active_responders(timeout_seconds=20)
            self._send_json_response({"status": "OK", "responders": active, "count": len(active)})
        elif self.path == '/api/status':
            self._send_json_response({
                "status": "ONLINE",
                "station": "D.B.M.S. Smart Ward ICU Admin Station",
                "ip": get_local_ip(),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            self._send_json_response({"error": "Endpoint not found"}, 404)

    def do_POST(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_len).decode('utf-8')
            data = json.loads(raw_body) if raw_body else {}
        except Exception:
            data = {}

        client_ip = self.client_address[0]

        if self.path == '/api/register':
            data["ip"] = data.get("ip") or client_ip
            shared_state.register_or_update_responder(data)
            
            # Notify server listener
            if hasattr(self.server, 'on_responder_event') and self.server.on_responder_event:
                try:
                    self.server.on_responder_event("JOINED", data)
                except Exception:
                    pass

            self._send_json_response({
                "status": "REGISTERED", 
                "device_id": data.get("device_id"),
                "admin_ip": get_local_ip(),
                "server_time": time.time()
            })

        elif self.path == '/api/heartbeat':
            dev_id = data.get("device_id")
            if dev_id:
                data["ip"] = data.get("ip") or client_ip
                shared_state.register_or_update_responder(data)
            self._send_json_response({"status": "OK", "heartbeat_received": True})

        elif self.path == '/api/ack':
            dev_id = data.get("device_id", "UNKNOWN")
            shared_state.record_responder_acknowledgement(dev_id, data)
            if hasattr(self.server, 'on_responder_event') and self.server.on_responder_event:
                try:
                    self.server.on_responder_event("ACKNOWLEDGED", data)
                except Exception:
                    pass
            self._send_json_response({"status": "ACK_RECORDED"})

        elif self.path == '/api/call_ward':
            # A companion app is calling the ICU Ward Admin station!
            if hasattr(self.server, 'on_incoming_ward_call') and self.server.on_incoming_ward_call:
                try:
                    self.server.on_incoming_ward_call(data)
                except Exception:
                    pass
            self._send_json_response({"status": "RINGING_ADMIN"})

        else:
            self._send_json_response({"error": "Unknown POST route"}, 404)

class ResponderRegistryServer:
    """Central server hosted by Admin station to discover, track, and call responders"""
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, port=ADMIN_REGISTRY_PORT):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(port=port)
            return cls._instance

    def __init__(self, port=ADMIN_REGISTRY_PORT):
        self.port = port
        self.running = False
        self.httpd: Optional[HTTPServer] = None
        self.http_thread: Optional[threading.Thread] = None
        self.beacon_thread: Optional[threading.Thread] = None
        self.on_responder_event: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_incoming_ward_call: Optional[Callable[[Dict[str, Any]], None]] = None

    def start(self):
        if self.running:
            return
        self.running = True

        # 1. Start HTTP Registry server
        def _run_http():
            try:
                server_address = ('0.0.0.0', self.port)
                self.httpd = HTTPServer(server_address, FleetHTTPRequestHandler)
                # Attach references for callback handling
                self.httpd.server = self
                print(f"[REGISTRY-SERVER] Online at http://{get_local_ip()}:{self.port}")
                self.httpd.serve_forever()
            except Exception as e:
                print(f"[REGISTRY-SERVER] Start error on port {self.port}: {e}")

        self.http_thread = threading.Thread(target=_run_http, daemon=True)
        self.http_thread.start()

        # 2. Start UDP Discovery Beacon
        def _run_beacon():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while self.running:
                try:
                    local_ip = get_local_ip()
                    beacon_packet = json.dumps({
                        "type": "SMART_WARD_ADMIN_BEACON",
                        "admin_ip": local_ip,
                        "admin_port": self.port,
                        "station_name": "D.B.M.S. Smart Ward Central Command",
                        "time": time.time()
                    }).encode('utf-8')
                    # Broadcast to LAN and local loopback
                    s.sendto(beacon_packet, ('<broadcast>', DISCOVERY_BEACON_PORT))
                    s.sendto(beacon_packet, ('127.0.0.1', DISCOVERY_BEACON_PORT))
                except Exception:
                    pass
                time.sleep(2.5)
            s.close()

        self.beacon_thread = threading.Thread(target=_run_beacon, daemon=True)
        self.beacon_thread.start()

    def stop(self):
        self.running = False
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass

    def call_single_responder(self, responder: dict, alert_payload: dict) -> bool:
        """Directly calls a specific responder device over network socket"""
        ip = responder.get("ip", "127.0.0.1")
        port = responder.get("call_port", DEFAULT_RESPONDER_CALL_PORT)

        # Build emergency call envelope
        envelope = {
            "type": "EMERGENCY_INCOMING_CALL",
            "caller_id": "SMART_WARD_ADMIN_STATION",
            "caller_name": "Smart Ward ICU Command Station",
            "caller_ip": get_local_ip(),
            "caller_port": self.port,
            "target_device_id": responder.get("device_id"),
            "target_name": responder.get("name"),
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "alert": alert_payload
        }
        
        data_bytes = json.dumps(envelope).encode('utf-8')
        success = False

        # Try TCP Direct Call First
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.5)
            sock.connect((ip, port))
            sock.sendall(data_bytes)
            sock.close()
            success = True
            print(f"[CALL-ENGINE] TCP Emergency Call placed to {responder.get('name')} @ {ip}:{port}")
        except Exception as e:
            # Fallback to UDP Broadcast to that port
            try:
                u_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                u_sock.sendto(data_bytes, (ip, port))
                u_sock.close()
                success = True
                print(f"[CALL-ENGINE] UDP Fallback Call sent to {responder.get('name')} @ {ip}:{port}")
            except Exception as ue:
                print(f"[CALL-ENGINE] Failed to reach {responder.get('name')} @ {ip}:{port}: {ue}")

        return success

    def broadcast_call_to_all_responders(self, alert_payload: dict) -> int:
        """Calls all active registered responders simultaneously"""
        active = shared_state.get_active_responders(timeout_seconds=20)
        reached_count = 0
        
        for r in active:
            if self.call_single_responder(r, alert_payload):
                reached_count += 1
                
        # Also broadcast to network calling receiver
        try:
            import dispatch_engine
            dispatch_engine.NetworkCallBroadcaster.broadcast_emergency_call(alert_payload)
        except Exception:
            pass

        return reached_count

# ==============================================================================
# 2. RESPONDER CLIENT (Runs inside the downloaded Calling System Companion App)
# ==============================================================================
class ResponderClient:
    """Client engine that discovers Admin, registers this device, and handles incoming calls"""
    def __init__(self, device_name="Caregiver Responder", role="Family Caregiver", phone="+91 98765 43210"):
        self.device_id = f"RESP-{abs(hash(device_name + str(time.time()))) % 100000:05d}"
        self.device_name = device_name
        self.role = role
        self.phone = phone
        self.admin_ip: Optional[str] = None
        self.admin_port = ADMIN_REGISTRY_PORT
        self.call_port = DEFAULT_RESPONDER_CALL_PORT
        self.running = False
        
        self.on_call_received: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_admin_discovered: Optional[Callable[[str, int], None]] = None
        
        self._listener_sock: Optional[socket.socket] = None
        self._threads: List[threading.Thread] = []

    def start(self, override_admin_ip: Optional[str] = None):
        if self.running:
            return
        self.running = True
        
        if override_admin_ip:
            self.admin_ip = override_admin_ip

        # 1. Allocate Call Port (try 8770, then increment if busy)
        self._bind_call_port()

        # 2. Start Incoming Call Listener Thread (TCP + UDP)
        t_call_tcp = threading.Thread(target=self._incoming_call_tcp_loop, daemon=True)
        t_call_udp = threading.Thread(target=self._incoming_call_udp_loop, daemon=True)
        t_call_tcp.start()
        t_call_udp.start()
        self._threads.extend([t_call_tcp, t_call_udp])

        # 3. Start Discovery & Registration Thread
        t_discovery = threading.Thread(target=self._discovery_and_heartbeat_loop, daemon=True)
        t_discovery.start()
        self._threads.append(t_discovery)

    def _bind_call_port(self):
        """Finds a free port starting at 8770"""
        for p in range(DEFAULT_RESPONDER_CALL_PORT, DEFAULT_RESPONDER_CALL_PORT + 50):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('0.0.0.0', p))
                s.close()
                self.call_port = p
                print(f"[RESPONDER-APP] Bound call listening port to {self.call_port}")
                return
            except Exception:
                continue

    def _incoming_call_tcp_loop(self):
        """Listens for high-priority incoming TCP emergency call connections"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', self.call_port))
            server.listen(5)
            self._listener_sock = server
        except Exception as e:
            print(f"[RESPONDER-APP] TCP bind error on port {self.call_port}: {e}")
            return

        while self.running:
            try:
                client, addr = server.accept()
                client.settimeout(3.0)
                raw = client.recv(8192)
                client.close()
                if raw:
                    payload = json.loads(raw.decode('utf-8', errors='replace'))
                    self._dispatch_incoming_call(payload)
            except Exception:
                pass

    def _incoming_call_udp_loop(self):
        """Listens for incoming UDP emergency call packets"""
        try:
            u_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            u_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            u_server.bind(('0.0.0.0', self.call_port))
            u_server.settimeout(2.0)
        except Exception as e:
            print(f"[RESPONDER-APP] UDP bind error on port {self.call_port}: {e}")
            return

        while self.running:
            try:
                raw, addr = u_server.recvfrom(8192)
                if raw:
                    payload = json.loads(raw.decode('utf-8', errors='replace'))
                    self._dispatch_incoming_call(payload)
            except socket.timeout:
                continue
            except Exception:
                pass

    def _dispatch_incoming_call(self, payload: dict):
        """Fires the incoming call callback to trigger ringing UI"""
        caller = payload.get('caller_name', 'Smart Ward Admin')
        print(f"[RESPONDER-APP] [INCOMING-CALL] Emergency Call Received from: {caller}")
        if self.on_call_received:
            try:
                self.on_call_received(payload)
            except Exception as e:
                print(f"[RESPONDER-APP] Error in call handler: {e}")

    def _discovery_and_heartbeat_loop(self):
        """Discovers Admin via UDP Beacon, registers, and sends heartbeats every 3s"""
        # 1. Listen for UDP beacon if admin_ip not known
        udp_beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            udp_beacon_sock.bind(('0.0.0.0', DISCOVERY_BEACON_PORT))
            udp_beacon_sock.settimeout(1.5)
        except Exception:
            udp_beacon_sock = None

        while self.running:
            # Check if admin_ip is resolved
            if not self.admin_ip and udp_beacon_sock:
                try:
                    data, addr = udp_beacon_sock.recvfrom(2048)
                    beacon = json.loads(data.decode('utf-8', errors='replace'))
                    if beacon.get("type") == "SMART_WARD_ADMIN_BEACON":
                        self.admin_ip = beacon.get("admin_ip")
                        self.admin_port = beacon.get("admin_port", ADMIN_REGISTRY_PORT)
                        print(f"[RESPONDER-APP] [DISCOVERED] Auto-Discovered Admin Station @ {self.admin_ip}:{self.admin_port}")
                        if self.on_admin_discovered:
                            try:
                                self.on_admin_discovered(self.admin_ip, self.admin_port)
                            except Exception:
                                pass
                except socket.timeout:
                    # Fallback check on localhost and LAN gateway
                    for fallback_ip in ['127.0.0.1', get_local_ip()]:
                        try:
                            req = urllib.request.Request(f"http://{fallback_ip}:{self.admin_port}/api/status", method='GET')
                            with urllib.request.urlopen(req, timeout=0.8) as resp:
                                if resp.status == 200:
                                    self.admin_ip = fallback_ip
                                    print(f"[RESPONDER-APP] [PROBE-OK] Discovered Admin via Local Probe: {self.admin_ip}")
                                    break
                        except Exception:
                            pass

            # If admin_ip is known, send registration or heartbeat
            if self.admin_ip:
                try:
                    url = f"http://{self.admin_ip}:{self.admin_port}/api/register"
                    payload = {
                        "device_id": self.device_id,
                        "name": self.device_name,
                        "role": self.role,
                        "phone": self.phone,
                        "ip": get_local_ip(),
                        "call_port": self.call_port,
                        "status": "ONLINE",
                        "timestamp": time.time()
                    }
                    body = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        pass
                except Exception as e:
                    # Connection failed, keep searching
                    pass

            time.sleep(3.0)

    def acknowledge_emergency_call(self, call_payload: dict, status_note="Accepted & Responding"):
        """Sends an SOS Acknowledgment back to Admin Station"""
        if not self.admin_ip:
            return False
        try:
            url = f"http://{self.admin_ip}:{self.admin_port}/api/ack"
            body = json.dumps({
                "device_id": self.device_id,
                "responder_name": self.device_name,
                "role": self.role,
                "phone": self.phone,
                "status_note": status_note,
                "timestamp": time.time(),
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S")
            }).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[RESPONDER-APP] Ack error: {e}")
            return False

    def call_admin_ward_station(self, message="Caregiver Requesting Ward Audio Line") -> bool:
        """Initiates a return call from this companion app to the Admin ICU Station"""
        if not self.admin_ip:
            return False
        try:
            url = f"http://{self.admin_ip}:{self.admin_port}/api/call_ward"
            body = json.dumps({
                "type": "CALL_WARD_REQUEST",
                "caller_id": self.device_id,
                "caller_name": self.device_name,
                "caller_role": self.role,
                "caller_phone": self.phone,
                "caller_ip": get_local_ip(),
                "caller_port": self.call_port,
                "message": message,
                "timestamp": time.time()
            }).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[RESPONDER-APP] Call ward error: {e}")
            return False

    def stop(self):
        """Stops background threads and closes listener socket"""
        self.running = False
        if self._listener_sock:
            try:
                self._listener_sock.close()
            except Exception:
                pass
