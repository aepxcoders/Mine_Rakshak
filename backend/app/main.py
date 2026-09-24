from datetime import datetime, timezone
from hmac import compare_digest

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import (
    db_ok,
    latest_event,
    latest_telemetry,
    recent_events,
    recent_telemetry,
    save_telemetry,
    should_log_hazard,
    log_event,
)
from .hazard import classify_hazard
from .analytics import analyze_telemetry, SAFETY_REFERENCES, OPERATIONAL_REFERENCES
from .models import TelemetryIn

app = FastAPI(
    title=settings.app_name,
    version="4.3.0-mq-reference",
    description="MineRakshak September 2026 single-rover Wi-Fi test backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Device-Key"],
)


def require_device_key(x_device_key: str | None):
    if not x_device_key:
        raise HTTPException(status_code=401, detail="Missing X-Device-Key")
    if not compare_digest(x_device_key, settings.device_key):
        raise HTTPException(status_code=401, detail="Invalid device key")


def telemetry_age_seconds(received_at):
    if received_at is None:
        return None
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - received_at).total_seconds()
    return max(0, round(age, 2))


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": "4.3.0-mq-reference",
        "profile": "single-rover-wifi-test",
        "rover_id": "MRR-01",
        "database": "SQLite",
        "status": "running",
    }


@app.get("/health")
def health():
    database_status = db_ok()
    return {
        "status": "ok" if database_status else "degraded",
        "sqlite": database_status,
    }


@app.get("/api/system/test-profile")
def get_test_profile():
    return {
        "success": True,
        "profile": "MineRakshak September 2026 test version",
        "rover_id": "MRR-01",
        "board": "ESP32 NodeMCU-32S",
        "transport": "wifi",
        "future_transport": "lora_optional",
        "gas_mode": "manufacturer_reference_ppm_estimates_plus_raw_adc",
        "sensor_map": {
            "vibration": "GPIO13",
            "water": "GPIO12",
            "motion": "GPIO14",
            "ultrasonic_trig": "GPIO26",
            "ultrasonic_echo": "GPIO25",
            "hw611_scl": "GPIO33",
            "hw611_sda": "GPIO32",
            "mq4_raw": "GPIO35",
            "mq7_raw": "GPIO34",
            "mq135_raw": "GPIO39/VN",
            "mq3_raw": "GPIO36/VP",
            "sound": "GPIO15",
            "flame": "GPIO2",
            "dht22": "GPIO27",
            "imu_sda": "GPIO21",
            "imu_scl": "GPIO22",
        },
        "i2c": {
            "hw611": "0x76",
            "imu": "0x68",
            "imu_who_am_i": "0x70",
            "imu_driver_state": "mpu6500_class_register_reader_active",
        },
        "camera": "rover_kit_stream_integration_pending",
        "rover_control": "smorphi_app_only_dashboard_controls_disabled",
    }


@app.post("/api/telemetry")
def receive_telemetry(
    telemetry: TelemetryIn,
    x_device_key: str | None = Header(default=None),
):
    require_device_key(x_device_key)
    payload = telemetry.model_dump()

    # Backend is the source of truth for test-version hazards.
    # Raw MQ ADC values are stored; reference ppm/equivalent estimates are calculated separately in analytics.
    hazard = classify_hazard(payload)
    saved = save_telemetry(payload, hazard)
    rover_id = payload["rover_id"]

    if should_log_hazard(rover_id, hazard):
        severity = hazard["state"]
        message = "; ".join(hazard.get("reasons", [])) or "Hazard state changed"
        log_event(
            rover_id=rover_id,
            event_type="hazard",
            message=message,
            severity=severity,
            details=hazard,
        )

    return {
        "success": True,
        "message": "Telemetry received",
        "rover_id": rover_id,
        "hazard": hazard,
        "telemetry": saved,
    }


@app.get("/api/rover/latest")
def get_latest_rover(rover_id: str | None = Query(default="MRR-01")):
    telemetry = latest_telemetry(rover_id)

    if telemetry is None:
        return {
            "success": True,
            "rover_id": rover_id or "MRR-01",
            "rover_online": False,
            "telemetry": None,
            "telemetry_age_seconds": None,
            "server_hazard": {
                "state": "unknown",
                "reasons": ["No telemetry received"],
                "gas_calibrated": False,
            },
            "latest_event": None,
            "capabilities": {"camera": bool(settings.camera_url)},
            "camera_url": settings.camera_url or None,
        }

    age = telemetry_age_seconds(telemetry.get("received_at"))
    online = (
        bool(telemetry.get("rover_online", True))
        and age is not None
        and age <= settings.stale_after_seconds
    )
    hazard = telemetry.get(
        "hazard",
        {"state": "unknown", "reasons": [], "gas_calibrated": False},
    )
    current_rover_id = telemetry.get("rover_id", "MRR-01")

    return {
        "success": True,
        "rover_id": current_rover_id,
        "rover_online": online,
        "telemetry_age_seconds": age,
        "telemetry": telemetry,
        "server_hazard": hazard,
        "latest_event": latest_event(current_rover_id),
        "capabilities": {"camera": bool(settings.camera_url)},
        "camera_url": settings.camera_url or None,
    }


@app.get("/api/events")
def get_events(
    limit: int = Query(default=50, ge=1, le=200),
    rover_id: str | None = Query(default="MRR-01"),
):
    return {
        "success": True,
        "events": recent_events(limit=limit, rover_id=rover_id),
    }


@app.get("/api/analytics")
def get_analytics(
    rover_id: str | None = Query(default="MRR-01"),
    history_limit: int = Query(default=30, ge=5, le=120),
):
    telemetry = latest_telemetry(rover_id)
    if telemetry is None:
        return {
            "success": True,
            "rover_id": rover_id or "MRR-01",
            "telemetry_age_seconds": None,
            "analytics": {
                "engine": "MineRakshak Live Safety Analytics v2",
                "method": "Live sensor states + safety thresholds + short-term trend analysis",
                "machine_learning": False,
                "state": "unknown",
                "risk_score": 0,
                "summary": "NO DATA — waiting for rover telemetry",
                "analysis_coverage_percent": 0,
                "alerts": [],
                "gas_trends": [],
                "checks": {},
                "regulatory_references": SAFETY_REFERENCES,
                "operational_references": OPERATIONAL_REFERENCES,
                "limitations": ["No telemetry has been received yet."],
            },
        }

    age = telemetry_age_seconds(telemetry.get("received_at"))
    history = recent_telemetry(limit=history_limit, rover_id=rover_id)
    analytics = analyze_telemetry(telemetry, history, age_seconds=age)
    return {
        "success": True,
        "rover_id": telemetry.get("rover_id", rover_id or "MRR-01"),
        "telemetry_age_seconds": age,
        "analytics": analytics,
    }
