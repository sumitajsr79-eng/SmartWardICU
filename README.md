# 🏥 D.B.M.S. Smart Ward ICU & Home Care Telemetry Suite

An intelligent medical IoT telemetry, patient vitals monitoring, and automated emergency dispatch suite built for Windows and Arduino AVR microcontrollers.

---

## 🌟 Key Features

- **🏡 Dual-Domain Monitoring (Home Care & Hospital ICU)**:
  - **Home Care Mode**: Designed for elderly and post-op care. Clean, non-alarming UI with calming soft cyan/emerald aesthetics, 1-click Caregiver SOS, and normal resting vitals tracking.
  - **Hospital ICU Mode**: Clinical Lead-II ECG oscilloscope display, high-visibility telemetry ribbon, arrhythmia classification, and automated multi-channel code-blue dispatches.
- **⚡ 1-Click Quick Access**:
  - Instant one-click launch cards with pre-configured access credentials.
  - Collapsible security key drawer for enterprise multi-tier role authorization (`XXXX-XXXX-XX`).
- **🫀 Rock-Solid Arduino Uno IoT Firmware**:
  - Non-blocking architecture running at 115200 BAUD.
  - Zero-RAM U8x8 OLED display driver preserving 730+ bytes of dynamic SRAM on ATmega328P.
  - Adaptive 620ms refractory lockout completely eliminating dicrotic notch bounce artifacts.
  - Real-time MPU-6050 3-axis accelerometer for instantaneous fall detection (>2.6G threshold).
- **🚨 Automated Emergency Dispatch Center**:
  - Automated voice phone calls via Windows telephony (`tel:` URI protocol) with text-to-speech emergency announcements (`pyttsx3`).
  - Automated emergency SMS dispatch with exact room, bed, and clickable Google Maps navigation pins.
  - Hybrid Wi-Fi, IP, and hardware GPS location engine.

---

## 📁 Repository Structure

```
SmartWardICU/
├── smart_ward_launcher.py             # Desktop Suite Launcher with 1-click mode cards
├── smart_ward_monitor.py              # Main Vitals & ECG Oscilloscope Dashboard
├── emergency_location_dispatcher.py   # Automated Voice & SMS Emergency Dispatcher
├── auth_system.py                     # Multi-tier role & key authentication system
├── hardware_bridge.py                 # Serial USB bridge (CH340 / Arduino Uno)
├── dispatch_engine.py                 # Automated telephony, SMS, and geolocation engine
├── calling_console.py                 # Integrated voice call dialer & TTS audio interface
├── login_view.py                      # Modern clean card UI & quick-launch selector
├── shared_state.py                    # Cross-process interlink & telemetry synchronization
├── build_executables.py               # Automated PyInstaller packaging script
├── generate_icons.py                  # High-DPI multi-layer icon generator (.ico)
├── Launch_Smart_Ward_Suite.bat        # Interactive Windows batch launcher
├── requirements.txt                   # Python package dependencies
├── .gitignore                         # Build and binary ignore rules
├── firmware/
│   └── SmartWard_Uno_Telemetry/
│       ├── SmartWard_Uno_Telemetry.ino # Arduino Uno C++ IoT firmware
│       └── README.md                  # Hardware wiring schematic & pinout guide
└── web_dashboard/
    ├── smart_ward_icu_dashboard.html  # Responsive Web telemetry interface
    ├── start_icu_server.js            # Node.js live mock server
    └── start_icu_server.cjs           # CommonJS script runner
```

---

## 🔑 Access Credentials Cheat Sheet

| Operating Mode | Role | Default Access Key | Target Environment |
|---|---|---|---|
| **🏡 Home Care** | `home` | `5050-8012-34` | Home monitoring, elderly support, family caregivers |
| **👤 Bedside Patient** | `patient` | `1010-4091-72` | Bedside touch screen, simplified emergency controls |
| **🏥 Hospital ICU** | `doctor` | `9090-1284-55` | Intensive care units, medical staff, full telemetry |

---

## 🔌 Hardware Schematics & Pinout

| Component | Arduino Uno Pin | Note |
|---|---|---|
| **SSD1306 0.96" OLED** | A4 (SDA), A5 (SCL), 5V, GND | I2C Address `0x3C` |
| **MPU-6050 Accel/Gyro** | A4 (SDA), A5 (SCL), 5V, GND | I2C Address `0x68` (Fall detection) |
| **Pulse / Heart Sensor** | Analog Pin A0, 5V / 3.3V, GND | Optical photoplethysmogram (PPG) |
| **NEO-6M GPS Module** | Pin 4 (Arduino RX), Pin 3 (TX) | 9600 BAUD (NMEA sentences) |
| **USB Serial Interface** | USB Port (COM3 / COM4) | 115200 BAUD (`CH340` / ATmega16U2) |

---

## 🚀 Getting Started

### 1. Requirements & Installation

```bash
git clone https://github.com/sumitajsr79-eng/SmartWardICU.git
cd SmartWardICU
pip install -r requirements.txt
```

### 2. Flash Arduino Firmware

Connect your Arduino Uno via USB and flash using the Arduino IDE or CLI:

```bash
arduino-cli compile --upload -p COM3 --fqbn arduino:avr:uno firmware/SmartWard_Uno_Telemetry
```

### 3. Launch the Suite

Double-click `Launch_Smart_Ward_Suite.bat` or launch directly via Python:

```bash
# Launch unified suite menu
python smart_ward_launcher.py

# Launch ICU / Home Care dashboard directly
python smart_ward_monitor.py

# Launch emergency dispatcher directly
python emergency_location_dispatcher.py
```

---

## 🛡️ License

MIT License. Designed and developed for patient safety, rapid emergency dispatch, and non-intrusive home care.
