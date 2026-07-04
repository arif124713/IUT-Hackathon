# Wokwi Simulation Link

**Project:** OfficePulse — ESP32 Room Monitor (work1)

**Wokwi link:** https://wokwi.com/projects/468612636471182337

Built, wired, and verified: the sketch compiles and runs in-simulator against the
circuit below (5 sense channels + 5 status LEDs on one ESP32 DevKit-C).

---

## Circuit

| Device | Real component | Wokwi stand-in | Sense pin (ADC1) | LED pin |
|---|---|---|---|---|
| Fan 1 (65 W) | ZMCT103C CT sensor | Potentiometer wiper, gated by slide switch | GPIO 32 | GPIO 16 |
| Fan 2 (75 W) | ZMCT103C CT sensor | Potentiometer wiper, gated by slide switch | GPIO 33 | GPIO 17 |
| Light 1 (15 W) | ZMCT103C CT sensor | Potentiometer wiper, gated by slide switch | GPIO 34 *(input-only)* | GPIO 18 |
| Light 2 (15 W) | ZMCT103C CT sensor | Potentiometer wiper, gated by slide switch | GPIO 35 *(input-only)* | GPIO 19 |
| Light 3 (20 W) | ZMCT103C CT sensor | Potentiometer wiper, gated by slide switch | GPIO 36 / VP *(input-only)* | GPIO 21 |

**Wiring per channel:**
- Potentiometer: left leg → 3V3, right leg → GND, wiper → slide switch
- Slide switch: sits between the pot wiper and the ESP32 sense pin (open = device OFF = ADC reads 0)
- Status LED: ESP32 GPIO → 220 Ω resistor → LED anode → cathode → GND

Firmware: [`diagrams/esp32_room_monitor.ino`](esp32_room_monitor.ino) — reads all 5 ADC
channels every 2 s, drives the matching status LED, and prints a JSON summary
(`{"room":"work1","devices":[...],"total_w":...}`) over Serial. This is the same
firmware that would POST to `/ingest` on real hardware (see the commented-out
Wi-Fi/HTTP block at the top of the sketch).

Full part-and-wire definition: [`diagram.json`](diagram.json) (importable into any new Wokwi ESP32 project).

---

## Why potentiometers instead of real CT sensors

Wokwi has no ZMCT103C model. A potentiometer on an ADC pin produces the same
0–3.3 V proportional signal that the real CT conditioning circuit would produce.
A slide switch gating the wiper simulates a device being physically on or off.
The firmware logic — threshold detection, wattage estimation, LED drive, JSON
serial output — is identical whether the input comes from a pot or a real sensor.
