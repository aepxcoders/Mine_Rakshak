MINERAKSHAK - SEPTEMBER 2026 TEST BUILD
======================================

WHAT THIS BUILD MATCHES
-----------------------
Rover: MRR-01 only
Controller: ESP32 NodeMCU-32S
Prototype telemetry: Wi-Fi
Laptop/backend test address used today: 192.168.1.28:8000
Device header: X-Device-Key: MRR-DEVICE-001
Camera: hardware connected; stream URL is configured with CAMERA_URL

TEST SENSOR MAP
---------------
GPIO13       SW-420 vibration
GPIO12       Water sensor
GPIO14       PIR motion
GPIO26       HC-SR04 TRIG
GPIO25       HC-SR04 ECHO
GPIO33       HW-611 SDA
GPIO32       HW-611 SCL
GPIO35       MQ-4 analog
GPIO34       MQ-7 analog
GPIO39 / VN  MQ-135 analog
GPIO36 / VP  MQ-3 analog
GPIO15       Sound sensor
GPIO2        Flame sensor
GPIO21       IMU SDA
GPIO22       IMU SCL

I2C TEST RESULTS
----------------
HW-611 found at 0x76.
IMU found at 0x68 and WHO_AM_I returned 0x70.
WHO_AM_I 0x70 identifies an MPU6500-class device. The current ESP32 test code
uses a register-level reader and now supplies live acceleration, gyro and tilt.

IMPORTANT GAS-SENSOR RULE
-------------------------
The test build sends MQ-4, MQ-7, MQ-135 and MQ-3 as raw ESP32 ADC readings:
mq4_raw, mq7_raw, mq135_raw, mq3_raw.

Do NOT label those ADC values as ppm. ch4_ppm / co_ppm remain optional and the
backend only uses them for gas hazard rules after real calibration is added.

START BACKEND
-------------
1. Copy .env.example to .env.
2. No external database setup is required. SQLite is created automatically.
3. Install packages:
   pip install -r requirements.txt
4. Start:
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Useful URLs:
http://127.0.0.1:8000/docs
http://192.168.1.28:8000/health
http://192.168.1.28:8000/api/system/test-profile

ESP32 -> BACKEND
----------------
POST http://192.168.1.28:8000/api/telemetry
Header:
X-Device-Key: MRR-DEVICE-001
Content-Type: application/json

See examples/test_telemetry.json for the exact recommended test payload.
The backend also accepts common aliases such as mq4, mq7, mq135, mq3, pir,
ultrasonic_cm and temperature, and normalizes them to the dashboard fields.

FRONTEND -> BACKEND
-------------------
The frontend reads:
GET /api/rover/latest?rover_id=MRR-01
GET /api/events?rover_id=MRR-01

The frontend automatically defaults to port 8000 on the same hostname from
which the dashboard is opened, so opening the dashboard at
http://192.168.1.28:8080 connects it to http://192.168.1.28:8000.

ROVER MOVEMENT
--------------
The test dashboard does not send movement commands. Rover movement remains in
the Smorphi mobile app, matching the current prototype test setup.


CURRENT ROVER INTEGRATION NOTES (13 SEP 2026)
----------------------------------------------
- Active sensor transport for the bench test: Wi-Fi.
- LoRa modules are planned/available for a later field version, but they are not
  required by this test backend. The REST API can stay unchanged when LoRa is
  added through a gateway.
- Rover movement remains controlled through the Smorphi rover application.
  This backend intentionally exposes no movement-control endpoint in the test build.
- The camera belongs to the rover kit, not the ESP32 sensor stack. CAMERA_URL
  should remain empty until the rover camera stream/API is identified.
- HW-611 test wiring: SCL GPIO33, SDA GPIO32.

DASHBOARD DISPLAY RULES (FINAL TEST CLEANUP)
--------------------------------------------
- BMP280 humidity is displayed as N/A, never 0%.
- ESP32 `rssi` is normalized to `wifi_rssi` and shown in dBm.
- Sound GPIO15 is digital in this build and is shown as DETECTED / CLEAR.
- Live MPU data is labeled as live when acceleration/gyro values arrive.
- Tilt >=45° is a warning; >=70° is danger in the prototype classifier.
- Event history logs hazard-state transitions rather than every tiny value change.

AI ANALYTICS API (v4.0)
-----------------------
GET /api/analytics?rover_id=MRR-01&history_limit=30

Returns:
- overall analytics state and 0-100 risk score
- analysis coverage percentage
- critical/warning/caution/info alerts with recommended operator action
- raw MQ baseline/trend checks and ADC saturation checks
- regulatory/reference threshold table
- operational prototype threshold table
- explicit limitations so raw ADC values are never presented as certified ppm measurements

See AI_ANALYTICS_THRESHOLDS.txt for the threshold basis used by this test build.
