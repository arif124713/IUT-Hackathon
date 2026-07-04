# Wokwi Simulation Link

**Project:** OfficePulse — ESP32 Room Monitor (work1)

> Paste your public Wokwi link here after creating the project:

**Wokwi link:** `TODO — paste link after building in https://wokwi.com`

---

## How to build this in Wokwi (30 min)

1. Go to [wokwi.com](https://wokwi.com) → **New Project** → **ESP32**
2. Add these parts from the parts panel:
   - 5 × Potentiometer
   - 5 × Slide Switch
   - 5 × LED
   - 5 × Resistor (220 Ω)
   - 1 × Breadboard
3. Wire per the pin map below, then rename each part's label to the device ID
4. Paste the firmware from `diagrams/esp32_room_monitor.ino` into `sketch.ino`
5. Click **Run** → verify Serial output and LED behavior when sliding pots
6. **Share** → copy public link → paste it above
7. Screenshot at 100% zoom → save as `diagrams/wokwi-schematic.png`

---

## Pin Map

| Device | Real component | Wokwi stand-in | Sense pin (ADC1) | LED pin |
|---|---|---|---|---|
| Fan 1 (65 W) | ZMCT103C CT sensor | Potentiometer wiper | GPIO 32 | GPIO 16 |
| Fan 2 (75 W) | ZMCT103C CT sensor | Potentiometer wiper | GPIO 33 | GPIO 17 |
| Light 1 (15 W) | ZMCT103C CT sensor | Potentiometer wiper | GPIO 34 *(input-only)* | GPIO 18 |
| Light 2 (15 W) | ZMCT103C CT sensor | Potentiometer wiper | GPIO 35 *(input-only)* | GPIO 19 |
| Light 3 (20 W) | ZMCT103C CT sensor | Potentiometer wiper | GPIO 36 / VP *(input-only)* | GPIO 21 |

**Wiring each channel:**
- Pot: left leg → 3V3 rail, right leg → GND rail, wiper → sense pin
- Switch: inserted between pot wiper and sense pin (open = device OFF = ADC reads 0)
- LED: GPIO → 220 Ω resistor → LED anode → cathode → GND

---

## Why potentiometers instead of real CT sensors

Wokwi has no ZMCT103C model. A potentiometer on an ADC pin produces the same
0–3.3 V proportional signal that the real CT conditioning circuit would produce.
A slide switch gating the wiper simulates a device being physically on or off.
The firmware logic — threshold detection, wattage estimation, LED drive, JSON
serial output — is identical whether the input comes from a pot or a real sensor.
