from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TelemetryIn(BaseModel):
    """Telemetry accepted from the September 2026 MineRakshak test rover.

    Raw MQ ADC values are the primary prototype fields. Calibrated ppm values are
    optional and should only be sent after sensor calibration.
    """

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def normalize_test_payload(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        aliases = {
            "mq4": "mq4_raw",
            "mq7": "mq7_raw",
            "mq135": "mq135_raw",
            "mq3": "mq3_raw",
            "pir": "motion",
            "pir_detected": "motion",
            "water_detected": "water",
            "flame_detected": "flame",
            "vibration_detected": "vibration",
            "ultrasonic_cm": "distance_cm",
            "distance": "distance_cm",
            "temperature": "temp",
            "wifiRSSI": "wifi_rssi",
            "rssi": "wifi_rssi",
            "camera": "camera_connected",
        }
        for source, target in aliases.items():
            if target not in data and source in data:
                data[target] = data[source]
        return data

    rover_id: str = Field(default="MRR-01", min_length=1, max_length=64)
    sequence: int | None = Field(default=None, ge=0)
    timestamp: str | None = None
    rover_online: bool = True

    # Test-version MQ sensors (ADC)
    mq4_raw: int | None = Field(default=None, ge=0, le=4095)
    mq7_raw: int | None = Field(default=None, ge=0, le=4095)
    mq135_raw: int | None = Field(default=None, ge=0, le=4095)
    mq3_raw: int | None = Field(default=None, ge=0, le=4095)

    # Optional calibrated values. Do not populate these from raw ADC readings.
    ch4_ppm: float | None = Field(default=None, ge=0)
    co_ppm: float | None = Field(default=None, ge=0)
    air_quality: float | None = Field(default=None, ge=0)

    # HW-611 environmental module / BME-class data when available.
    temp: float | None = Field(default=None, ge=-40, le=125)
    humidity: float | None = Field(default=None, ge=0, le=100)
    pressure: float | None = Field(default=None, ge=250, le=1200)
    hw611_address: str | None = None
    hw611_status: str | None = None

    # Ultrasonic
    distance_cm: float | None = Field(default=None, ge=0, le=1000)

    # Current test wiring uses the module digital output: 0 = clear, 1 = detected.
    # Keep numeric compatibility with the ESP32 payload while the UI renders
    # this as CLEAR / DETECTED rather than a fake sound level.
    sound: float | None = Field(default=None, ge=0)

    # Digital sensors
    water: bool | None = None
    flame: bool | None = None
    motion: bool | None = None
    vibration: bool | None = None

    # IMU: the test device answers at 0x68 with WHO_AM_I 0x70. The current
    # register-level MPU6500-class reader supplies live acceleration, gyro and
    # tilt values; identity/status fields remain optional for compatibility.
    imu_address: str | None = None
    imu_who_am_i: str | None = None
    imu_status: str | None = None
    accel_x: float | None = None
    accel_y: float | None = None
    accel_z: float | None = None
    gyro_x: float | None = None
    gyro_y: float | None = None
    gyro_z: float | None = None
    tilt_deg: float | None = Field(default=None, ge=0, le=180)

    # Rover/test metadata
    mine_zone: str | None = None
    direction: str | None = None
    battery_percent: float | None = Field(default=None, ge=0, le=100)
    wifi_rssi: int | None = None
    camera_connected: bool | None = None
