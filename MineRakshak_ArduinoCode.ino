#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <DHT.h>

#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Adafruit_BMP280.h>

// =====================================================
// ROVER
// =====================================================

const char* ROVER_ID = "MRR-01";

// =====================================================
// WIFI + LOCAL DASHBOARD
// =====================================================

const char* WIFI_SSID = "EsiPhone";
const char* WIFI_PASSWORD = "12345678";

const char* BACKEND_HOST =
  "172.20.10.6";

const uint16_t BACKEND_PORT =
  8000;

const char* SERVER_URL =
  "http://172.20.10.6:8000/api/telemetry";

const char* DEVICE_KEY =
  "MRR-DEVICE-001";

// =====================================================
// FINAL HARDWARE PIN MAP
// =====================================================

// SW-420 vibration
#define VIBRATION_PIN 13

// Water sensor
#define WATER_PIN 12

// PIR
#define PIR_PIN 14

// HC-SR04
#define TRIG_PIN 26
#define ECHO_PIN 25

// HW-611
#define HW611_SDA 33
#define HW611_SCL 32

// MQ sensors
#define MQ4_PIN   35
#define MQ7_PIN   34
#define MQ135_PIN 39
#define MQ3_PIN   36

// Sound
#define SOUND_PIN 15

// Flame
#define FLAME_PIN 2

// DHT22
#define DHT_PIN 27
#define DHT_TYPE DHT22

// MPU / MPU6500-class device
#define MPU_SDA 21
#define MPU_SCL 22
#define MPU_ADDR 0x68

// =====================================================
// SECOND I2C BUS
// =====================================================

TwoWire HW611_WIRE = TwoWire(1);

// =====================================================
// SENSOR OBJECTS
// =====================================================

Adafruit_BME280 bme;
Adafruit_BMP280 bmp(&HW611_WIRE);
DHT dht(DHT_PIN, DHT_TYPE);

// =====================================================
// SENSOR STATUS
// =====================================================

bool mpuAvailable = false;
bool bmeAvailable = false;
bool bmpAvailable = false;

// =====================================================
// TIMING
// =====================================================

unsigned long lastTelemetry = 0;
unsigned long lastReconnectAttempt = 0;

const unsigned long TELEMETRY_INTERVAL = 2000;
const unsigned long WIFI_RETRY_INTERVAL = 15000;

unsigned long sequenceNumber = 0;

// =====================================================
// WIFI EVENTS
// =====================================================

void WiFiEvent(
  WiFiEvent_t event,
  WiFiEventInfo_t info
)
{
  if (
    event ==
    ARDUINO_EVENT_WIFI_STA_GOT_IP
  )
  {
    Serial.println();
    Serial.println("==============================");
    Serial.println("WIFI CONNECTED");

    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());

    Serial.print("RSSI: ");
    Serial.println(WiFi.RSSI());

    Serial.println("==============================");
  }

  if (
    event ==
    ARDUINO_EVENT_WIFI_STA_DISCONNECTED
  )
  {
    Serial.println();

    Serial.print("WiFi disconnected. Reason: ");

    Serial.println(
      info.wifi_sta_disconnected.reason
    );
  }
}

// =====================================================
// WIFI
// =====================================================

void connectWiFi()
{
  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    return;
  }

  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);

  // Keep Wi-Fi fully awake for reliable HTTP telemetry.
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );

  unsigned long startTime =
    millis();

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - startTime < 30000
  )
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    Serial.println("WiFi connected");

    Serial.print("ESP32 IP: ");
    Serial.println(
      WiFi.localIP()
    );
  }
  else
  {
    Serial.println(
      "WiFi connection timed out"
    );
  }
}

// =====================================================
// ULTRASONIC
// =====================================================

float readDistance()
{
  digitalWrite(
    TRIG_PIN,
    LOW
  );

  delayMicroseconds(2);

  digitalWrite(
    TRIG_PIN,
    HIGH
  );

  delayMicroseconds(10);

  digitalWrite(
    TRIG_PIN,
    LOW
  );

  unsigned long duration =
    pulseIn(
      ECHO_PIN,
      HIGH,
      30000
    );

  if (duration == 0)
  {
    return -1.0;
  }

  float distance =
    duration * 0.0343 / 2.0;

  if (
    distance < 0 ||
    distance > 1000
  )
  {
    return -1.0;
  }

  return distance;
}

// =====================================================
// MPU REGISTER WRITE
// =====================================================

void writeMPU(
  byte reg,
  byte value
)
{
  Wire.beginTransmission(
    MPU_ADDR
  );

  Wire.write(reg);
  Wire.write(value);

  Wire.endTransmission();
}

// =====================================================
// MPU SETUP
// =====================================================

void setupMPU()
{
  Serial.println();
  Serial.println("Checking MPU sensor...");

  Wire.begin(
    MPU_SDA,
    MPU_SCL,
    100000
  );

  delay(300);

  // Read WHO_AM_I register 0x75
  Wire.beginTransmission(
    MPU_ADDR
  );

  Wire.write(0x75);

  if (
    Wire.endTransmission(false) != 0
  )
  {
    Serial.println(
      "MPU I2C DEVICE NOT FOUND"
    );

    mpuAvailable = false;

    return;
  }

  Wire.requestFrom(
    MPU_ADDR,
    1
  );

  if (!Wire.available())
  {
    Serial.println(
      "MPU WHO_AM_I READ FAILED"
    );

    mpuAvailable = false;

    return;
  }

  byte who =
    Wire.read();

  Serial.print("WHO_AM_I = 0x");
  Serial.println(
    who,
    HEX
  );

  // Your device returns 0x70
  if (who == 0x70)
  {
    Serial.println(
      "MPU6500-CLASS DEVICE DETECTED"
    );

    // Wake up
    writeMPU(
      0x6B,
      0x00
    );

    delay(100);

    // Gyro ±500 deg/sec
    writeMPU(
      0x1B,
      0x08
    );

    // Accelerometer ±8g
    writeMPU(
      0x1C,
      0x10
    );

    // DLPF configuration
    writeMPU(
      0x1A,
      0x03
    );

    mpuAvailable = true;

    Serial.println(
      "MPU SENSOR READY"
    );
  }
  else
  {
    Serial.println(
      "UNEXPECTED MPU DEVICE"
    );

    mpuAvailable = false;
  }
}

// =====================================================
// MPU READ
// =====================================================

bool readMPU(
  float &ax,
  float &ay,
  float &az,
  float &gx,
  float &gy,
  float &gz,
  float &tilt
)
{
  if (!mpuAvailable)
  {
    return false;
  }

  Wire.beginTransmission(
    MPU_ADDR
  );

  Wire.write(
    0x3B
  );

  if (
    Wire.endTransmission(false) != 0
  )
  {
    return false;
  }

  Wire.requestFrom(
    MPU_ADDR,
    14
  );

  if (
    Wire.available() < 14
  )
  {
    return false;
  }

  int16_t rawAx =
    (Wire.read() << 8) |
    Wire.read();

  int16_t rawAy =
    (Wire.read() << 8) |
    Wire.read();

  int16_t rawAz =
    (Wire.read() << 8) |
    Wire.read();

  // Skip temperature
  Wire.read();
  Wire.read();

  int16_t rawGx =
    (Wire.read() << 8) |
    Wire.read();

  int16_t rawGy =
    (Wire.read() << 8) |
    Wire.read();

  int16_t rawGz =
    (Wire.read() << 8) |
    Wire.read();

  // ±8g = 4096 LSB/g
  ax =
    (rawAx / 4096.0)
    * 9.80665;

  ay =
    (rawAy / 4096.0)
    * 9.80665;

  az =
    (rawAz / 4096.0)
    * 9.80665;

  // ±500 dps = 65.5 LSB/degree/sec
  gx =
    rawGx / 65.5;

  gy =
    rawGy / 65.5;

  gz =
    rawGz / 65.5;

  tilt =
    atan2(
      ax,
      sqrt(
        ay * ay +
        az * az
      )
    )
    * 180.0 / PI;

  tilt =
    abs(tilt);

  tilt =
    constrain(
      tilt,
      0.0,
      180.0
    );

  return true;
}

// =====================================================
// HW-611 SETUP
// =====================================================

void setupHW611()
{
  Serial.println();
  Serial.println("Checking HW-611...");

  HW611_WIRE.begin(
    HW611_SDA,
    HW611_SCL,
    100000
  );

  delay(300);

  HW611_WIRE.beginTransmission(
    0x76
  );

  byte error =
    HW611_WIRE.endTransmission();

  if (error != 0)
  {
    Serial.println(
      "HW-611 I2C DEVICE NOT FOUND"
    );

    return;
  }

  Serial.println(
    "HW-611 DEVICE FOUND @ 0x76"
  );

  // Try BME280 first
  if (
    bme.begin(
      0x76,
      &HW611_WIRE
    )
  )
  {
    bmeAvailable = true;

    Serial.println(
      "HW-611 = BME280"
    );

    return;
  }

  // Your module is currently detected as BMP280
  if (
    bmp.begin(
      0x76
    )
  )
  {
    bmpAvailable = true;

    Serial.println(
      "HW-611 = BMP280"
    );

    return;
  }

  Serial.println(
    "HW-611 DRIVER INIT FAILED"
  );
}

// =====================================================
// BACKEND TCP TEST
// =====================================================

bool testBackendConnection()
{
  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    Serial.println(
      "BACKEND TCP TEST SKIPPED - WIFI DISCONNECTED"
    );

    return false;
  }

  WiFiClient testClient;

  Serial.print(
    "Testing backend TCP: "
  );

  Serial.print(
    BACKEND_HOST
  );

  Serial.print(
    ":"
  );

  Serial.println(
    BACKEND_PORT
  );

  // 3000 ms timeout prevents the ESP32 from hanging here.
  bool connected =
    testClient.connect(
      BACKEND_HOST,
      BACKEND_PORT,
      3000
    );

  if (connected)
  {
    Serial.println(
      "BACKEND TCP CONNECTION: SUCCESS"
    );

    testClient.stop();

    return true;
  }

  Serial.println(
    "BACKEND TCP CONNECTION: FAILED"
  );

  return false;
}

// =====================================================
// TELEMETRY
// =====================================================

void sendTelemetry()
{
  // =================================================
  // MQ SENSORS
  // =================================================

  int mq4Raw =
    analogRead(
      MQ4_PIN
    );

  int mq7Raw =
    analogRead(
      MQ7_PIN
    );

  int mq135Raw =
    analogRead(
      MQ135_PIN
    );

  int mq3Raw =
    analogRead(
      MQ3_PIN
    );

  // =================================================
  // DIGITAL SENSORS
  // =================================================

  bool vibrationDetected =
    digitalRead(
      VIBRATION_PIN
    ) == HIGH;

  bool waterDetected =
    digitalRead(
      WATER_PIN
    ) == HIGH;

  bool motionDetected =
    digitalRead(
      PIR_PIN
    ) == HIGH;

  bool soundDetected =
    digitalRead(
      SOUND_PIN
    ) == HIGH;

  bool flameDetected =
    digitalRead(
      FLAME_PIN
    ) == LOW;

  // =================================================
  // ULTRASONIC
  // =================================================

  float distance =
    readDistance();

  bool distanceAvailable =
    distance >= 0;

  // =================================================
  // ENVIRONMENT
  // =================================================

  float temperature = 0;
  float humidity = 0;
  float pressure = 0;

  bool temperatureAvailable = false;
  bool humidityAvailable = false;
  bool pressureAvailable = false;

  // Primary temperature + pressure source: HW-611 (BME280/BMP280)
  if (bmeAvailable)
  {
    temperature =
      bme.readTemperature();

    pressure =
      bme.readPressure()
      / 100.0F;

    if (
      !isnan(temperature) &&
      temperature >= -40 &&
      temperature <= 125
    )
    {
      temperatureAvailable = true;
    }

    if (
      !isnan(pressure) &&
      pressure >= 250 &&
      pressure <= 1200
    )
    {
      pressureAvailable = true;
    }
  }

  else if (bmpAvailable)
  {
    temperature =
      bmp.readTemperature();

    pressure =
      bmp.readPressure()
      / 100.0F;

    if (
      !isnan(temperature) &&
      temperature >= -40 &&
      temperature <= 125
    )
    {
      temperatureAvailable = true;
    }

    if (
      !isnan(pressure) &&
      pressure >= 250 &&
      pressure <= 1200
    )
    {
      pressureAvailable = true;
    }
  }

  // Humidity source: DHT22 on GPIO27.
  // DHT22 is read once per telemetry cycle.
  float dhtHumidity =
    dht.readHumidity();

  if (
    !isnan(dhtHumidity) &&
    dhtHumidity >= 0 &&
    dhtHumidity <= 100
  )
  {
    humidity =
      dhtHumidity;

    humidityAvailable =
      true;
  }

  // =================================================
  // MPU DATA
  // =================================================

  float accelX = 0;
  float accelY = 0;
  float accelZ = 0;

  float gyroX = 0;
  float gyroY = 0;
  float gyroZ = 0;

  float tilt = 0;

  bool mpuDataAvailable =
    readMPU(
      accelX,
      accelY,
      accelZ,
      gyroX,
      gyroY,
      gyroZ,
      tilt
    );

  // =================================================
  // JSON
  // =================================================

  StaticJsonDocument<1536> doc;

  sequenceNumber++;

  doc["rover_id"] =
    ROVER_ID;

  doc["sequence"] =
    sequenceNumber;

  doc["rover_online"] =
    true;

  // =================================================
  // MQ DATA
  // =================================================

  doc["mq4_raw"] =
    mq4Raw;

  doc["mq7_raw"] =
    mq7Raw;

  doc["mq135_raw"] =
    mq135Raw;

  doc["mq3_raw"] =
    mq3Raw;

  // No fake PPM until calibration
  doc["ch4_ppm"] =
    nullptr;

  doc["co_ppm"] =
    nullptr;

  doc["air_quality"] =
    mq135Raw;

  // =================================================
  // ENVIRONMENT
  // =================================================

  if (temperatureAvailable)
  {
    doc["temp"] =
      temperature;
  }
  else
  {
    doc["temp"] =
      nullptr;
  }

  if (humidityAvailable)
  {
    doc["humidity"] =
      humidity;
  }
  else
  {
    doc["humidity"] =
      nullptr;
  }

  if (pressureAvailable)
  {
    doc["pressure"] =
      pressure;
  }
  else
  {
    doc["pressure"] =
      nullptr;
  }

  // =================================================
  // DISTANCE
  // =================================================

  if (distanceAvailable)
  {
    doc["distance_cm"] =
      distance;
  }
  else
  {
    doc["distance_cm"] =
      nullptr;
  }

  // =================================================
  // SAFETY
  // =================================================

  doc["sound"] =
    soundDetected ? 1 : 0;

  doc["water"] =
    waterDetected;

  doc["flame"] =
    flameDetected;

  doc["motion"] =
    motionDetected;

  doc["vibration"] =
    vibrationDetected;

  // =================================================
  // MPU
  // =================================================

  if (mpuDataAvailable)
  {
    doc["accel_x"] =
      accelX;

    doc["accel_y"] =
      accelY;

    doc["accel_z"] =
      accelZ;

    doc["gyro_x"] =
      gyroX;

    doc["gyro_y"] =
      gyroY;

    doc["gyro_z"] =
      gyroZ;

    doc["tilt_deg"] =
      tilt;
  }
  else
  {
    doc["accel_x"] =
      nullptr;

    doc["accel_y"] =
      nullptr;

    doc["accel_z"] =
      nullptr;

    doc["gyro_x"] =
      nullptr;

    doc["gyro_y"] =
      nullptr;

    doc["gyro_z"] =
      nullptr;

    doc["tilt_deg"] =
      nullptr;
  }

  // =================================================
  // WIFI / BATTERY
  // =================================================

  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    doc["rssi"] =
      WiFi.RSSI();
  }
  else
  {
    doc["rssi"] =
      nullptr;
  }

  doc["battery_percent"] =
    nullptr;

  // =================================================
  // SERIALIZE
  // =================================================

  String jsonData;

  serializeJson(
    doc,
    jsonData
  );

  // =================================================
  // SERIAL OUTPUT
  // =================================================

  Serial.println();
  Serial.println(
    "================================"
  );

  Serial.println(
    "ROVER TELEMETRY"
  );

  Serial.println(
    jsonData
  );

  Serial.println(
    "--------------------------------"
  );

  Serial.print("MQ4 RAW: ");
  Serial.println(mq4Raw);

  Serial.print("MQ7 RAW: ");
  Serial.println(mq7Raw);

  Serial.print("MQ135 RAW: ");
  Serial.println(mq135Raw);

  Serial.print("MQ3 RAW: ");
  Serial.println(mq3Raw);

  Serial.print("Distance: ");

  if (distanceAvailable)
  {
    Serial.print(distance);
    Serial.println(" cm");
  }
  else
  {
    Serial.println("NO ECHO");
  }

  Serial.print("MPU: ");

  if (mpuDataAvailable)
  {
    Serial.println("OK");

    Serial.print("Accel X: ");
    Serial.println(accelX);

    Serial.print("Accel Y: ");
    Serial.println(accelY);

    Serial.print("Accel Z: ");
    Serial.println(accelZ);

    Serial.print("Gyro X: ");
    Serial.println(gyroX);

    Serial.print("Gyro Y: ");
    Serial.println(gyroY);

    Serial.print("Gyro Z: ");
    Serial.println(gyroZ);

    Serial.print("Tilt: ");
    Serial.println(tilt);
  }
  else
  {
    Serial.println(
      "NO DATA"
    );
  }

  Serial.print("HW-611: ");

  if (bmeAvailable)
  {
    Serial.println(
      "BME280 OK"
    );
  }
  else if (bmpAvailable)
  {
    Serial.println(
      "BMP280 OK"
    );
  }
  else
  {
    Serial.println(
      "NOT FOUND"
    );
  }

  Serial.print("DHT22 Humidity: ");

  if (humidityAvailable)
  {
    Serial.print(humidity);
    Serial.println(" %");
  }
  else
  {
    Serial.println("NO DATA");
  }

  // =================================================
  // WIFI CHECK
  // =================================================

  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    Serial.println(
      "Telemetry not sent - WiFi disconnected"
    );

    Serial.println(
      "================================"
    );

    return;
  }

  // =================================================
  // HTTP POST
  // =================================================

  // First prove that the backend port is reachable.
  if (!testBackendConnection())
  {
    Serial.println(
      "Telemetry not sent - backend unreachable"
    );

    Serial.println(
      "================================"
    );

    return;
  }

  WiFiClient client;

  HTTPClient http;

  http.setConnectTimeout(3000);
  http.setTimeout(5000);

  Serial.print("POST -> ");
  Serial.println(SERVER_URL);

  if (
    !http.begin(
      client,
      SERVER_URL
    )
  )
  {
    Serial.println(
      "HTTP initialization failed"
    );

    return;
  }

  http.addHeader(
    "Content-Type",
    "application/json"
  );

  http.addHeader(
    "X-Device-Key",
    DEVICE_KEY
  );

  int responseCode =
    http.POST(
      jsonData
    );

  Serial.print(
    "Backend response code: "
  );

  Serial.println(
    responseCode
  );

  if (responseCode > 0)
  {
    String response =
      http.getString();

    Serial.print(
      "Backend response: "
    );

    Serial.println(
      response
    );
  }
  else
  {
    Serial.print(
      "HTTP error: "
    );

    Serial.println(
      http.errorToString(
        responseCode
      )
    );
  }

  http.end();

  Serial.println(
    "================================"
  );
}

// =====================================================
// SETUP
// =====================================================

void setup()
{
  Serial.begin(115200);

  delay(2000);

  Serial.println();
  Serial.println();
  Serial.println(
    "================================"
  );

  Serial.println(
    "MINE RESCUE ROVER - SIH 2026"
  );

  Serial.println(
    "MRR-01 FINAL TEST BUILD"
  );

  Serial.println(
    "================================"
  );

  WiFi.onEvent(
    WiFiEvent
  );

  // =================================================
  // DIGITAL SENSORS
  // =================================================

  pinMode(
    VIBRATION_PIN,
    INPUT
  );

  pinMode(
    WATER_PIN,
    INPUT
  );

  pinMode(
    PIR_PIN,
    INPUT
  );

  pinMode(
    SOUND_PIN,
    INPUT
  );

  pinMode(
    FLAME_PIN,
    INPUT
  );

  // =================================================
  // ULTRASONIC
  // =================================================

  pinMode(
    TRIG_PIN,
    OUTPUT
  );

  pinMode(
    ECHO_PIN,
    INPUT
  );

  digitalWrite(
    TRIG_PIN,
    LOW
  );

  // =================================================
  // MQ SENSORS
  // =================================================

  pinMode(
    MQ4_PIN,
    INPUT
  );

  pinMode(
    MQ7_PIN,
    INPUT
  );

  pinMode(
    MQ135_PIN,
    INPUT
  );

  pinMode(
    MQ3_PIN,
    INPUT
  );

  analogReadResolution(12);

  // =================================================
  // DHT22
  // =================================================

  dht.begin();

  // =================================================
  // SENSOR SETUP
  // =================================================

  setupMPU();

  setupHW611();

  // =================================================
  // WIFI
  // =================================================

  connectWiFi();

  if (
    WiFi.status() ==
    WL_CONNECTED
  )
  {
    testBackendConnection();
  }

  // =================================================
  // READY
  // =================================================

  Serial.println();
  Serial.println(
    "================================"
  );

  Serial.println(
    "ESP32 SENSOR HUB READY"
  );

  Serial.println(
    "MPU bus: SDA21 / SCL22"
  );

  Serial.println(
    "HW-611: SDA33 / SCL32 / 0x76"
  );

  Serial.println(
    "DHT22: DATA GPIO27"
  );

  Serial.print(
    "Dashboard: "
  );

  Serial.println(
    SERVER_URL
  );

  Serial.println(
    "================================"
  );
}

// =====================================================
// LOOP
// =====================================================

void loop()
{
  // =================================================
  // WIFI RECONNECT
  // =================================================

  if (
    WiFi.status() !=
    WL_CONNECTED
  )
  {
    if (
      millis() -
      lastReconnectAttempt >=
      WIFI_RETRY_INTERVAL
    )
    {
      lastReconnectAttempt =
        millis();

      Serial.println(
        "WiFi lost - reconnecting..."
      );

      WiFi.reconnect();
    }
  }

  // =================================================
  // TELEMETRY
  // =================================================

  if (
    millis() -
    lastTelemetry >=
    TELEMETRY_INTERVAL
  )
  {
    lastTelemetry =
      millis();

    sendTelemetry();
  }

  delay(50);
}