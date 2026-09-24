# ⛏️ Mine Rakshak

## Smart Mine Rescue Rover & Real-Time Safety Monitoring System

**Mine Rakshak** is a **Smart India Hackathon (SIH) 2026 prototype** for remote monitoring of hazardous underground mine conditions.

The current implementation is built around a **single ESP32 test rover (MRR-01)**. The ESP32 collects environmental, gas-response, proximity, motion, vibration and safety-related sensor data, sends telemetry over Wi-Fi to a FastAPI backend, stores the data in SQLite, evaluates hazard conditions, and exposes the results through a browser-based monitoring dashboard.

> **Current build:** ESP32 + Wi-Fi + FastAPI + SQLite + HTML/CSS/JavaScript Dashboard
> **Future/optional integrations:** LoRa communication, rover camera integration and rover control.

---

# 📌 Problem Statement

During an underground mine emergency, entering an affected area to determine the condition of the environment can expose rescue personnel to additional risk.

Potential hazards include:

* Methane and carbon-monoxide related gas conditions
* Poor air-quality response
* Fire or flame
* Water presence
* Excessive temperature
* Physical obstructions
* Vibration
* Rover instability or excessive tilt
* Communication loss
* Low rover battery

Mine Rakshak is designed to provide a **remote telemetry and decision-support layer** that allows the condition of a test rover and its surrounding environment to be monitored before or during hazardous inspection.

---

# 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    MINE / TEST ENVIRONMENT                  │
│                                                             │
│  MQ-4  MQ-7  MQ-135  MQ-3   DHT22   HW-611   Flame        │
│  Water  PIR   SW-420   Sound   HC-SR04   MPU6500-class IMU │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    ESP32 SENSOR HUB                         │
│                                                             │
│  Sensor acquisition                                         │
│  ADC / Digital / I²C readings                               │
│  Sensor status checks                                       │
│  JSON telemetry generation                                  │
│  Sequence numbering                                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                         Wi-Fi / HTTP
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                         │
│                                                             │
│  Device authentication                                      │
│  Pydantic telemetry validation                              │
│  Hazard classification                                      │
│  Explainable safety analytics                               │
│  Event logging                                              │
│  Telemetry history                                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                         SQLITE                              │
│                                                             │
│  Telemetry records                                          │
│  Hazard state                                               │
│  Event history                                              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 WEB MONITORING DASHBOARD                    │
│                                                             │
│  Live Sensors | Rover Status | Analytics | Events          │
└─────────────────────────────────────────────────────────────┘
```

---

# 📁 Repository Structure

```text
Mine_Rakshak/
│
├── MineRakshak_ArduinoCode.ino
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── README.txt
│   └── js/
│       ├── api.js
│       └── app.js
│
├── backend/
│   ├── .env.example
│   ├── .gitignore
│   ├── AI_ANALYTICS_THRESHOLDS.txt
│   ├── README.txt
│   ├── requirements.txt
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── hazard.py
│   │   ├── analytics.py
│   │   └── mq_reference.py
│   │
│   └── examples/
│       └── test_telemetry.json
│
└── README.md
```

---

# 🔩 Hardware

The current ESP32 firmware is configured for the following hardware:

| Component         | Purpose                                    |
| ----------------- | ------------------------------------------ |
| ESP32 NodeMCU-32S | Main controller and Wi-Fi telemetry device |
| MQ-4              | Methane-response sensing                   |
| MQ-7              | Carbon-monoxide-response sensing           |
| MQ-135            | Air-quality response sensing               |
| MQ-3              | Gas/VOC response sensing                   |
| DHT22             | Temperature and humidity                   |
| HW-611            | Environmental sensor module                |
| Flame Sensor      | Flame detection                            |
| Water Sensor      | Water detection                            |
| HC-SR04           | Distance / obstacle detection              |
| PIR HC-SR501      | Motion detection                           |
| SW-420            | Vibration detection                        |
| Sound Sensor      | Digital sound-event detection              |
| MPU6500-class IMU | Acceleration, gyroscope and tilt data      |

---

# 🔌 ESP32 Pin Mapping

The current firmware uses the following pin configuration:

| Sensor / Interface |    ESP32 Pin |
| ------------------ | -----------: |
| SW-420 Vibration   |      GPIO 13 |
| Water Sensor       |      GPIO 12 |
| PIR                |      GPIO 14 |
| HC-SR04 TRIG       |      GPIO 26 |
| HC-SR04 ECHO       |      GPIO 25 |
| HW-611 SDA         |      GPIO 33 |
| HW-611 SCL         |      GPIO 32 |
| MQ-4               |      GPIO 35 |
| MQ-7               |      GPIO 34 |
| MQ-135             | GPIO 39 / VN |
| MQ-3               | GPIO 36 / VP |
| Sound Sensor       |      GPIO 15 |
| Flame Sensor       |       GPIO 2 |
| DHT22              |      GPIO 27 |
| IMU SDA            |      GPIO 21 |
| IMU SCL            |      GPIO 22 |
| IMU I²C Address    |       `0x68` |
| HW-611 I²C Address |       `0x76` |

---

# 📡 Communication

### Current Communication

```text
ESP32
  ↓
Wi-Fi
  ↓
HTTP
  ↓
FastAPI Backend
  ↓
SQLite
  ↓
Web Dashboard
```

### Current Rover

```text
Rover ID: MRR-01
Board: ESP32 NodeMCU-32S
Transport: Wi-Fi
Database: SQLite
```

### Future Communication

LoRa is planned as an optional future communication layer for environments where Wi-Fi is not suitable.

The dashboard/API architecture is designed so that the transport layer can be changed without completely redesigning the frontend.

---

# ⚙️ ESP32 Firmware

The main firmware is:

```text
MineRakshak_ArduinoCode.ino
```

The firmware performs the following operations:

1. Initialize ESP32
2. Initialize connected sensors
3. Connect to Wi-Fi
4. Monitor sensor availability
5. Read MQ sensor ADC values
6. Read digital safety sensors
7. Measure ultrasonic distance
8. Read environmental sensor values
9. Read DHT22 temperature/humidity
10. Read IMU acceleration and gyroscope values
11. Calculate rover tilt
12. Build JSON telemetry
13. Check backend connectivity
14. Send telemetry using HTTP POST
15. Print debugging information through Serial Monitor
16. Reconnect to Wi-Fi when required

---

# 🔄 ESP32 Data Pipeline

```text
START
  │
  ▼
Initialize ESP32
  │
  ▼
Initialize Sensors
  │
  ▼
Connect to Wi-Fi
  │
  ▼
Read Sensor Values
  │
  ├── MQ-4
  ├── MQ-7
  ├── MQ-135
  ├── MQ-3
  ├── DHT22
  ├── HW-611
  ├── Flame
  ├── Water
  ├── PIR
  ├── SW-420
  ├── Sound
  ├── HC-SR04
  └── IMU
  │
  ▼
Create JSON Telemetry
  │
  ▼
Check Backend
  │
  ▼
POST /api/telemetry
  │
  ▼
FastAPI Backend
  │
  ▼
Repeat
```

Telemetry is sent approximately every **2 seconds** in the current test firmware.

---

# 📦 Example Telemetry

The backend accepts telemetry through the `TelemetryIn` Pydantic model.

Example:

```json
{
  "rover_id": "MRR-01",
  "sequence": 120,
  "rover_online": true,

  "mq4_raw": 850,
  "mq7_raw": 420,
  "mq135_raw": 610,
  "mq3_raw": 310,

  "temp": 29.4,
  "humidity": 61.2,
  "pressure": 1008.4,

  "distance_cm": 42.5,

  "sound": 0,
  "water": false,
  "flame": false,
  "motion": true,
  "vibration": false,

  "accel_x": 0.12,
  "accel_y": 0.08,
  "accel_z": 9.71,

  "gyro_x": 0.4,
  "gyro_y": 0.2,
  "gyro_z": 0.1,

  "tilt_deg": 4.8,

  "wifi_rssi": -55
}
```

Optional calibrated gas fields are also supported:

```json
{
  "ch4_ppm": 8500,
  "co_ppm": 35
}
```

However, the current firmware primarily sends **raw MQ ADC values**.

---

# 🖥️ Frontend Dashboard

The frontend is intentionally implemented using:

* HTML
* CSS
* JavaScript

There is currently **no React/Vite build system** in this repository.

### Frontend Structure

```text
frontend/
│
├── index.html
├── style.css
│
└── js/
    ├── api.js
    └── app.js
```

---

# 📊 Dashboard Features

The current dashboard provides:

### Sensor Dashboard

* MQ-4 raw ADC
* MQ-7 raw ADC
* MQ-135 raw ADC
* MQ-3 raw ADC
* Environmental readings
* Temperature
* Humidity
* Pressure
* Flame status
* Water status
* PIR motion
* SW-420 vibration
* Sound detection
* HC-SR04 distance
* IMU data
* Rover tilt
* Wi-Fi RSSI

### Rover Section

The Rover tab currently contains reserved areas for:

* Rover camera integration
* Rover controls
* Future rover-kit integration

The current rover controls are intentionally disabled because the present rover is operated separately.

### Analytics

The dashboard also includes the AI Analytics interface, which displays:

* Explainable risk score
* Safety alerts
* Warning conditions
* Critical conditions
* Sensor health
* Raw MQ trends
* Threshold/reference information
* Telemetry coverage
* Data-quality information

---

# 🧠 Safety Analytics

The backend contains an explainable analytics engine in:

```text
backend/app/analytics.py
```

The current system combines:

* Live sensor values
* Safety/reference thresholds
* Recent telemetry history
* Raw MQ sensor trends
* Sensor/data-quality checks
* Communication freshness
* Rover operational conditions

The analytics endpoint is:

```text
GET /api/analytics
```

### Important

The current system is **not a trained machine-learning model**.

It is an **explainable decision-support engine**.

The backend intentionally separates:

```text
Regulatory / Reference Values
            +
Operational Prototype Rules
            +
Sensor Data Quality
            +
Short-Term Trends
            ↓
Explainable Analytics
```

A future machine-learning model should be trained only after collecting sufficient labelled field telemetry.

---

# 🚨 Hazard Classification

Hazard classification is performed on the backend.

The main logic is located in:

```text
backend/app/hazard.py
```

Current conditions include:

* Calibrated methane concentration
* Calibrated carbon monoxide concentration
* Obstacle distance
* Flame detection
* Water detection
* Vibration
* Rover tilt
* Battery level

The resulting state is:

```text
SAFE
WARNING
DANGER
```

Example:

```text
Sensor Data
     ↓
Hazard Classifier
     ↓
┌───────────────┐
│ SAFE          │
│ WARNING       │
│ DANGER        │
└───────────────┘
     ↓
Event Logging
     ↓
Dashboard
```

The backend stores the hazard result together with telemetry and logs hazard state transitions as events.

---

# 🧪 MQ Sensor Processing

MQ sensors provide analog responses through the ESP32 ADC.

The current system therefore treats their primary readings as:

```text
RAW ADC VALUES
```

and **not automatically as certified ppm values**.

```text
MQ Sensor
    ↓
Analog Output
    ↓
ESP32 ADC
    ↓
Raw ADC
    ↓
Backend
    ↓
Trend / Sensor Health Analysis
```

The repository contains:

```text
backend/app/mq_reference.py
```

which implements a manufacturer-reference Rs/R0 estimation model for:

* MQ-4
* MQ-7
* MQ-135
* MQ-3

These values are explicitly treated as **reference estimates**, not certified gas measurements.

Proper deployment would require:

* Sensor-specific calibration
* Controlled reference gases
* Accurate load resistance
* Stable heater operation
* Environmental compensation
* Sensor ageing compensation
* Validated electronics
* Certified gas instrumentation

---

# 🔧 Backend

The backend is implemented using:

* Python
* FastAPI
* Pydantic
* SQLite
* Uvicorn
* python-dotenv

### Backend Structure

```text
backend/
│
├── .env.example
├── .gitignore
├── AI_ANALYTICS_THRESHOLDS.txt
├── README.txt
├── requirements.txt
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── config.py
│   ├── database.py
│   ├── hazard.py
│   ├── analytics.py
│   └── mq_reference.py
│
└── examples/
    └── test_telemetry.json
```

---

# 🧩 Backend Modules

| File              | Responsibility                                  |
| ----------------- | ----------------------------------------------- |
| `main.py`         | API routes, authentication and telemetry flow   |
| `models.py`       | Pydantic validation and telemetry normalization |
| `database.py`     | SQLite persistence and event history            |
| `hazard.py`       | Hazard classification                           |
| `analytics.py`    | Explainable safety analytics                    |
| `mq_reference.py` | Manufacturer-reference MQ estimation            |
| `config.py`       | Environment configuration                       |

---

# 🌐 API Endpoints

| Method | Endpoint                   | Purpose                             |
| ------ | -------------------------- | ----------------------------------- |
| `GET`  | `/`                        | Backend information                 |
| `GET`  | `/health`                  | Backend and SQLite health           |
| `GET`  | `/api/system/test-profile` | Current hardware/test configuration |
| `POST` | `/api/telemetry`           | Receive ESP32 telemetry             |
| `GET`  | `/api/rover/latest`        | Latest rover telemetry              |
| `GET`  | `/api/events`              | Recent events                       |
| `GET`  | `/api/analytics`           | Safety analytics                    |

---

# 🔐 Telemetry Authentication

The telemetry endpoint requires a device key.

```http
X-Device-Key: <configured-device-key>
Content-Type: application/json
```

The backend validates the key before accepting telemetry.

The configuration is controlled through:

```text
DEVICE_KEY
```

in the backend environment.

Do not commit real production credentials to GitHub.

---

# 🗄️ Database

The current implementation uses **SQLite**.

MongoDB is **not used in the current repository**.

SQLite stores:

* Telemetry records
* Hazard state
* Event history
* Timestamps
* Rover ID
* Sensor payloads

The current database design is intentionally lightweight for the SIH prototype and local testing environment.

---

# 📡 API Data Flow

```text
ESP32
  │
  │ POST /api/telemetry
  ▼
FastAPI
  │
  ├── Device Authentication
  │
  ├── Pydantic Validation
  │
  ├── Hazard Classification
  │
  ├── Telemetry Storage
  │
  └── Event Logging
  │
  ▼
SQLite
  │
  ├── Latest Telemetry
  ├── Historical Telemetry
  └── Events
  │
  ▼
Dashboard
  │
  ├── /api/rover/latest
  ├── /api/events
  └── /api/analytics
```

---

# 🚀 Installation & Setup

## 1. Clone the Repository

```bash
git clone https://github.com/aepxcoders/Mine_Rakshak.git
cd Mine_Rakshak
```

---

# 2. Backend Setup

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

### Windows

```powershell
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 3. Environment Configuration

Create:

```text
backend/.env
```

Use:

```text
backend/.env.example
```

as the template.

Important configuration values include:

```env
DEVICE_KEY=MRR-DEVICE-001
STALE_AFTER_SECONDS=15
CAMERA_URL=
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

For an actual deployment, use strong secrets instead of development values.

---

# 4. Start the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

# 5. Start the Frontend

The frontend does not require Node.js or a build system.

From the repository root:

```bash
cd frontend
python -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080
```

The dashboard automatically uses the backend on the same hostname at port `8000`.

For example:

```text
Frontend:
http://127.0.0.1:8080

Backend:
http://127.0.0.1:8000
```

---

# 6. Configure the ESP32

Open:

```text
MineRakshak_ArduinoCode.ino
```

in Arduino IDE.

Install the required libraries:

```text
WiFi
HTTPClient
Wire
ArduinoJson
DHT
Adafruit Sensor
Adafruit BME280
Adafruit BMP280
```

Update the network configuration in the firmware:

```cpp
const char* WIFI_SSID = "...";
const char* WIFI_PASSWORD = "...";

const char* BACKEND_HOST = "...";

const uint16_t BACKEND_PORT = 8000;

const char* SERVER_URL =
  "http://<backend-host>:8000/api/telemetry";

const char* DEVICE_KEY = "...";
```

Upload the firmware to the ESP32.

Open Serial Monitor:

```text
115200 baud
```

---

# 🧪 Test Without Hardware

The repository contains:

```text
backend/examples/test_telemetry.json
```

This can be used to test the backend independently of the ESP32.

From the `backend` directory:

### Windows

```powershell
curl -X POST "http://127.0.0.1:8000/api/telemetry" `
  -H "Content-Type: application/json" `
  -H "X-Device-Key: MRR-DEVICE-001" `
  --data-binary "@examples/test_telemetry.json"
```

Alternatively, use the FastAPI Swagger interface:

```text
http://127.0.0.1:8000/docs
```

---

# 🔍 Current Test Profile

The current backend identifies the active prototype as:

```text
Project        : MineRakshak
Rover ID       : MRR-01
Board          : ESP32 NodeMCU-32S
Transport      : Wi-Fi
Database       : SQLite
Telemetry      : HTTP + JSON
Gas Handling   : Raw ADC + optional reference estimates
LoRa           : Optional / Future
Camera         : Integration Pending
Rover Control  : Disabled in Dashboard
```

---

# 🎥 Camera & Rover Control

The current repository contains placeholders for future rover integration.

### Camera

```text
Status: Integration Pending
```

### Rover Controls

```text
Status: Disabled
```

The current rover movement is handled separately, and the dashboard does not pretend that autonomous rover control is already integrated.

This separation keeps the current sensor-monitoring prototype stable while leaving room for future rover integration.

---

# 📈 Future Development

Planned extensions include:

* LoRa gateway integration
* Multi-rover support
* Underground communication network
* Live rover camera stream
* Rover navigation and control integration
* Mine-zone mapping
* Sensor fusion
* Historical time-series analysis
* Labelled-data machine-learning models
* Predictive hazard analysis
* Sensor failure detection
* Emergency notification system
* Mobile monitoring application
* Offline telemetry buffering
* Stronger device authentication
* Secure firmware updates
* Production-grade observability
* Cloud deployment
* Digital mine environment visualization

---

# 🔐 Security Considerations

The current prototype provides basic device authentication through a device key.

A production deployment should additionally implement:

* HTTPS / TLS
* Per-device credentials
* Credential rotation
* Secure secret management
* API rate limiting
* Role-based access control
* Signed/authenticated device messages
* Network segmentation
* Database access controls
* Audit logging
* Secure OTA firmware updates
* Hardware security where applicable

Never commit:

```text
Wi-Fi passwords
Device keys
API secrets
Production credentials
Private certificates
```

to the repository.

---

# ⚠️ Limitations

Mine Rakshak is currently an **SIH prototype/test system**, not a certified mine-safety product.

Important limitations include:

1. MQ sensors are not automatically calibrated gas instruments.
2. Raw ADC values must not be interpreted as certified ppm measurements.
3. Manufacturer-reference MQ estimates are not a replacement for calibration.
4. The current sound sensor provides digital detection rather than calibrated dBA.
5. The HW-611/BMP280 dry-bulb temperature reading is not a wet-bulb measurement.
6. Prototype obstacle, tilt and communication thresholds are engineering test rules.
7. Wi-Fi is the current communication mechanism.
8. Underground deployment may require a different communication architecture.
9. LoRa is not the current telemetry transport.
10. Camera integration is currently pending.
11. Rover movement controls are currently disabled in the dashboard.
12. The current analytics engine is explainable rule/trend-based analysis, not trained machine learning.
13. Reference gas estimates require proper sensor calibration before they can be used for validated concentration measurement.

---

# 🛡️ Safety Disclaimer

Mine Rakshak is an academic/prototype system developed for the **Smart India Hackathon 2026** problem context.

The thresholds, reference estimates and analytics implemented in this repository must **not** be treated as certified mine-safety limits or as a replacement for:

* Approved mining safety equipment
* Certified gas detection equipment
* Industrial monitoring systems
* Mine rescue procedures
* Regulatory requirements
* Qualified safety personnel

Any real-world deployment would require:

* Domain validation
* Certified sensing hardware
* Sensor calibration
* Communication reliability testing
* Environmental testing
* Cybersecurity validation
* Hardware validation
* Regulatory compliance
* Professional mine-safety review

---

# 👥 Team

## APEX CODERS

### Mine Rakshak

**Smart India Hackathon 2026**

---

# 📌 Project Status

```text
ESP32 Sensor Integration       : ACTIVE
Wi-Fi Telemetry                : ACTIVE
FastAPI Backend                : ACTIVE
SQLite Storage                 : ACTIVE
Hazard Classification          : ACTIVE
Explainable Analytics          : ACTIVE
Web Dashboard                  : ACTIVE
Raw MQ Monitoring              : ACTIVE
MQ Reference Estimation        : ACTIVE
LoRa Communication             : FUTURE
Camera Integration             : PENDING
Rover Control Integration      : PENDING
Machine Learning Model         : FUTURE
Multi-Rover Architecture       : FUTURE
```

---

# 📄 License

This project is developed as part of the **Smart India Hackathon 2026** prototype by **APEX CODERS**.

Refer to the repository for the applicable project licensing and usage terms.
