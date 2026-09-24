MineRakshak — Local ESP32 Test Dashboard
========================================

CURRENT TEST UI
---------------
The default screen is the dense sensor dashboard used for hardware testing.
It intentionally focuses on live ESP32 sensor telemetry and does NOT pretend
that rover movement or the rover-kit camera are already integrated.

Tabs:
1. Sensors Dashboard
   - MQ-4 / MQ-7 / MQ-135 / MQ-3 raw ADC values
   - HW-611 environmental readings
   - flame, water, HC-SR04, PIR, SW-420, sound
   - IMU identity/status and motion graphs only when compatible values arrive
   - Wi-Fi test transport
   - LoRa is marked as a future option

2. Rover
   - reserved rover-kit camera panel
   - disabled rover controls because Smorphi is driven by its own app
   - future integration roadmap

IMPORTANT
---------
MQ values are RAW ADC values until proper calibration is completed. Do not
label them ppm.

The backend URL defaults to:
  http(s)://<same-hostname>:8000

The current rover is:
  MRR-01

The dashboard polls:
  GET /api/rover/latest?rover_id=MRR-01

Future LoRa use does not require redesigning the dashboard. The backend API can
remain the same while the transport between the rover and gateway changes.

FINAL LIVE-DATA CLEANUP
-----------------------
- BMP280 humidity displays N/A.
- Wi-Fi RSSI displays the ESP32 `rssi` value in dBm.
- Sound GPIO15 is displayed as DETECTED / CLEAR (digital DO).
- IMU labels switch to LIVE MPU DATA when acceleration/gyro telemetry is present.
- Rover camera and rover controls remain in the Rover tab as pending/disabled.

AI ANALYTICS TAB (v4.0)
-----------------------
The AI Analytics tab calls GET /api/analytics and renders an explainable risk score, critical/warning/caution alerts, sensor/data-quality gates, raw MQ trend intelligence and threshold references.
This is deliberately an explainable decision-support engine, not a falsely-labelled trained ML model. A future ML model should be trained only after labelled field telemetry is collected and validated.
