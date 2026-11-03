# D.B.M.S. Smart Ward ICU - Arduino Uno Firmware

### Microcontroller: Arduino Uno (ATmega328P, 5V Logic, 16 MHz)

This firmware implements a real-time, non-blocking telemetry engine for the Smart Ward ICU patient monitoring device.

---

## 1. Hardware Pinout & Wiring Table

| Component | Component Pin | Arduino Uno Pin | Power Rail | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **0.96" OLED Display** | `SDA` | **Analog Pin A4** | 5V & GND | Hardware I2C (Address `0x3C` or `0x3D`) |
| | `SCL` | **Analog Pin A5** | | |
| **MPU6050 IMU** | `SDA` | **Analog Pin A4** | 5V & GND | Hardware I2C (Address `0x68`, shares bus with OLED) |
| | `SCL` | **Analog Pin A5** | | |
| **Heart Pulse Sensor** | `Signal (S)` | **Analog Pin A0** | **3.3V** & GND | **Strictly connect VCC to 3.3V** to protect ADC reference |
| **NEO-6M GPS Module** | `TX` | **Digital Pin 4** | 5V & GND | Arduino RX (`SoftwareSerial` listens here) |
| | `RX` | **Digital Pin 3** | | Arduino TX (GPS listens here) |

> [!IMPORTANT]
> **Power Separation:** The Heart Pulse Sensor module **must be powered from 3.3V**, while the OLED, MPU6050, and NEO-6M run reliably from the Arduino Uno's **5V** header.
> **Hardware Exclusions:** No servo, no LED, no buzzer, and no slide switch are connected. All alarms and indicators are rendered visually on the OLED and transmitted via serial telemetry.

---

## 2. Required Arduino IDE Libraries

Install these libraries from the **Arduino IDE Library Manager** (`Ctrl + Shift + I` or `Sketch -> Include Library -> Manage Libraries...`):

1. **`Adafruit SSD1306`** (by *Adafruit*)
2. **`Adafruit GFX Library`** (by *Adafruit*)
3. **`MPU6050`** (by *Electronic Cats* or *Jeff Rowberg / I2Cdevlib*)
4. **`TinyGPSPlus`** (by *Mikal Hart*)
5. *(Wire and SoftwareSerial are built into the Arduino AVR Core and require no installation)*

---

## 3. How the Non-Blocking Tasks Work

The sketch uses zero blocking `delay()` functions, allowing all sensors to be processed cooperatively:

```
[Loop Execution (Every Cycle)]
  ├── Task A: gpsSerial.read() -> gps.encode() [Continuous NMEA Stream]
  ├── Task B: Pulse Sensor Sample (Every 20 ms / 50 Hz) -> Dynamic Peak BPM
  ├── Task C: MPU6050 Read (Every 30 ms / ~33 Hz) -> 3-Axis Vector G-Force -> Fall Detector
  ├── Task D: OLED Frame Render (Every 250 ms / 4 Hz) -> Crisp 128x64 Dashboard
  └── Task E: Serial Telemetry Output (Every 1000 ms / 1 Hz) -> JSON stream
```

### Biomechanical Fall Detection Stages:
1. **Free-Fall Phase:** Total acceleration drops below **0.55 G**.
2. **Impact Phase:** Acceleration spikes above **2.80 G** within 600 ms of free fall.
3. **Emergency Latch:** Latches the screen into **`! ! EMERGENCY ALERT ! !`** mode, displaying the patient impact magnitude, heart rate, and GPS location.
4. **Reset:** Clears automatically after 12 seconds or upon receiving the command `RESET` via the Serial Monitor.

---

## 4. Serial Monitor Configuration

- **Baud Rate:** `115200`
- **Output Format (1 Hz JSON stream):**
  ```json
  {"telemetry":{"bpm":76,"fall_alert":false,"g_force":1.01,"lat":37.774920,"lng":-122.419410,"sats":6}}
  ```
- **Manual Commands:** Type `RESET` or `CLEAR` into the serial input bar and press Enter to clear a latched fall alarm.
