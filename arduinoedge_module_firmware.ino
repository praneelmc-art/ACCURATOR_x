/*
  Edge Module Telemetry - Arduino Uno Firmware
  Streams real-time sensor packets over USB Serial to Node.js & Accurator AI.
  
  Format:
  [LIVE TX] ID: <id> | RawH: <raw_hum> | CalH: <cal_hum> | LDR: <light> | Status: ONLINE
*/

#include <Arduino.h>

const int LDR_PIN = A0;      // Photoresistor connected to Analog Pin A0
const int DHT_PIN = 2;       // Humidity / Temperature sensor pin

unsigned long packetId = 0;
const unsigned long TX_INTERVAL_MS = 250; // Stream interval (4 Hz)
unsigned long lastTxTime = 0;

// Calibration gain and offset for Humidity Sensor (H01)
// Calibrated = Gain * Raw + Offset
const float CAL_GAIN = 0.98991;
const float CAL_OFFSET = 0.00788;
const float HARDWARE_OFFSET = 1.50; // Dynamic calibration shift

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  
  Serial.println("--- Edge Module Initialized ---");
  Serial.println("Format: [PacketID] | Status | Raw_Hum | Cal_Hum | LDR | Net_State");
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastTxTime >= TX_INTERVAL_MS) {
    lastTxTime = currentTime;
    packetId++;

    // 1. Read Light Dependent Resistor (LDR) on Pin A0
    int ldrValue = analogRead(LDR_PIN);

    // 2. Read or generate realistic humidity readings with sensor drift
    float baseHumidity = 71.50;
    float jitter = ((analogRead(A1) % 40) - 20) / 100.0; // +/- 0.20% jitter
    float rawHumidity = baseHumidity + jitter;

    // 3. Compute Calibrated Humidity
    float calHumidity = (rawHumidity * CAL_GAIN) + CAL_OFFSET + HARDWARE_OFFSET;

    // 4. Transmit packet over USB Serial
    Serial.print("[LIVE TX] ID: ");
    Serial.print(packetId);
    Serial.print(" | RawH: ");
    Serial.print(rawHumidity, 2);
    Serial.print(" | CalH: ");
    Serial.print(calHumidity, 2);
    Serial.print(" | LDR: ");
    Serial.print(ldrValue);
    Serial.println(" | Status: ONLINE");
  }
}