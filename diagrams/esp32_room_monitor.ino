/*
 * OfficePulse — ESP32 Room Monitor Firmware
 * One ESP32 per room. Reads 5 current-sense inputs (2 fans + 3 lights),
 * drives a status LED per device, prints JSON to Serial every 2 s.
 *
 * REAL HARDWARE: each ADC pin is wired to a ZMCT103C current-transformer
 * breakout (burden resistor + half-wave rectifier + RC smoothing → 0–3.3 V DC).
 * Galvanic isolation means 220 V mains NEVER touches the MCU.
 *
 * WOKWI SIM: potentiometer wiper on each ADC pin stands in for the CT output.
 *            A slide switch gates the pot so zero voltage = device OFF.
 *            LED per device confirms the firmware detected ON state.
 *
 * ADC NOTE: ADC1 pins only (GPIO 32–39). ADC2 shares silicon with the Wi-Fi
 * radio — reading ADC2 while Wi-Fi is active returns garbage on ESP32.
 */

#include <Arduino.h>

// ── Wi-Fi + HTTP (uncomment on real hardware) ──────────────────────────────
// #include <WiFi.h>
// #include <HTTPClient.h>
// const char* WIFI_SSID     = "YOUR_SSID";
// const char* WIFI_PASSWORD = "YOUR_PASSWORD";
// const char* INGEST_URL    = "https://arif124713-officepulse.hf.space/ingest";

// ── Room identity ──────────────────────────────────────────────────────────
const char* ROOM_ID = "work1";   // change to "work2" or "drawing" per unit

// ── Pin mapping (ADC1 only — avoids Wi-Fi conflict) ───────────────────────
struct Device {
  const char* id;
  uint8_t     sensePin;   // ADC1 input
  uint8_t     ledPin;     // status LED output
  uint16_t    ratedW;     // nameplate wattage for power estimate
};

const Device DEVICES[] = {
  { "fan-1",   32, 16,  65 },
  { "fan-2",   33, 17,  75 },
  { "light-1", 34, 18,  15 },   // GPIO 34/35/36 are input-only — fine for ADC
  { "light-2", 35, 19,  15 },
  { "light-3", 36, 21,  20 },
};
const int NUM_DEVICES = sizeof(DEVICES) / sizeof(DEVICES[0]);

// ON threshold: raw ADC value > 300 out of 4095 (≈ 0.24 V) means load present
const int ON_THRESHOLD = 300;
// Samples averaged per reading for noise rejection
const int ADC_SAMPLES  = 8;

// ── Helpers ────────────────────────────────────────────────────────────────

int readADCAvg(uint8_t pin) {
  long sum = 0;
  for (int i = 0; i < ADC_SAMPLES; i++) {
    sum += analogRead(pin);
    delayMicroseconds(50);
  }
  return (int)(sum / ADC_SAMPLES);
}

// Linear power estimate: raw/4095 * ratedW (good enough for monitoring)
float estimateWatts(int raw, uint16_t ratedW) {
  return (raw / 4095.0f) * ratedW;
}

// ── Setup ──────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < NUM_DEVICES; i++) {
    // ADC pins: input by default; explicit pinMode not needed but harmless
    // LED pins must be OUTPUT
    if (DEVICES[i].ledPin < 34) {   // GPIO 34–39 are input-only on ESP32
      pinMode(DEVICES[i].ledPin, OUTPUT);
      digitalWrite(DEVICES[i].ledPin, LOW);
    }
  }

  // ── Wi-Fi connect (uncomment on real hardware) ─────────────────────────
  // WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  // while (WiFi.status() != WL_CONNECTED) { delay(200); }
}

// ── Main loop ──────────────────────────────────────────────────────────────

void loop() {
  bool   onState[NUM_DEVICES];
  float  watts[NUM_DEVICES];
  float  totalW = 0;

  for (int i = 0; i < NUM_DEVICES; i++) {
    int raw       = readADCAvg(DEVICES[i].sensePin);
    onState[i]    = raw > ON_THRESHOLD;
    watts[i]      = onState[i] ? estimateWatts(raw, DEVICES[i].ratedW) : 0;
    totalW       += watts[i];

    // Drive status LED
    if (DEVICES[i].ledPin < 34) {
      digitalWrite(DEVICES[i].ledPin, onState[i] ? HIGH : LOW);
    }
  }

  // ── Serial JSON output ─────────────────────────────────────────────────
  Serial.print("{\"room\":\"");
  Serial.print(ROOM_ID);
  Serial.print("\",\"devices\":[");
  for (int i = 0; i < NUM_DEVICES; i++) {
    Serial.print("{\"id\":\"");
    Serial.print(DEVICES[i].id);
    Serial.print("\",\"on\":");
    Serial.print(onState[i] ? "true" : "false");
    Serial.print(",\"est_w\":");
    Serial.print((int)watts[i]);
    Serial.print("}");
    if (i < NUM_DEVICES - 1) Serial.print(",");
  }
  Serial.print("],\"total_w\":");
  Serial.print((int)totalW);
  Serial.println("}");

  // ── HTTP POST to backend (uncomment on real hardware) ──────────────────
  // if (WiFi.status() == WL_CONNECTED) {
  //   HTTPClient http;
  //   http.begin(INGEST_URL);
  //   http.addHeader("Content-Type", "application/json");
  //   // Rebuild payload as String here and http.POST(payload);
  //   http.end();
  // }

  delay(2000);
}
