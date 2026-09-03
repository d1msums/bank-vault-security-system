# Intelligent Bank Vault Security System

An IoT vault security system built for ITT569 (Internet of Things) at UiTM. It combines keypad authentication, motion/gas sensing, a servo-controlled lock, and real-time Telegram alerts, with a Flask dashboard on top for live monitoring.

**[Demo video](https://youtu.be/ElBB1NgDEyM?si=PdTLc-rUhNeH3x2R)** · **[Technical report](docs/technical-report.pdf)**

## Overview

The vault is unlocked via keypad PIN entry, which an ESP32 checks and uses to drive a servo lock. While armed, the system also watches for unauthorized motion (PIR sensor) and gas leaks (MQ-2 sensor). Any access attempt or sensor trigger gets logged to a SQLite database and pushed out as an alert through a Telegram bot, and the whole thing is visible on a Flask web dashboard.

## Architecture

Keypad + sensors feed into the ESP32, which handles the servo lock directly. The ESP32 also pushes events over HTTP to a Flask backend, which writes to SQLite for history and triggers the Telegram bot for real-time alerts so that notifications go out whether or not anyone's actually watching the dashboard.

## Tech stack

- **Microcontroller:** ESP32
- **Sensors:** PIR (motion), MQ-2 (gas)
- **Actuation:** Servo motor
- **Backend:** Flask (Python)
- **Database:** SQLite
- **Alerts:** Telegram Bot API

## My contributions

This was a group project for ITT569; a few of us split the work. I mainly worked on:

- Designing the SQLite schema for logging access attempts and sensor events
- Building the Telegram bot integration end-to-end, from event trigger to notification
- ESP32 firmware for sensor handling and access control logic

Along the way I also ended up doing a fair amount of debugging:
- Switched the whole setup from dual Arduino + ESP32 to ESP32-only after we kept running into hardware faults — simpler and a lot more reliable
- Chased down false-trigger issues on the PIR sensor
- Tuned the MQ-2 analog threshold since it kept false-positiving on gas detection
- Fixed a rendering bug on the Flask dashboard that was breaking the live status view
- Tracked down some ESP32 → Flask POST requests that were silently failing and dropping events

## How to Run

### 1. Setup database
```bash
cd database
python setup_db.py
```

### 2. Run Flask dashboard
```bash
cd dashboard
python app.py
```

Open browser at `http://localhost:5000`

### 3. Upload ESP32 sketch
- Open `hardware/esp32_main.ino` in Arduino IDE
- Update WiFi credentials and Flask IP in sketch
- Select Board: ESP32 Dev Module
- Upload to ESP32

### 4. Update Flask IP in sketch
Find this line and update with your laptop IP:
```cpp
const char* flaskURL = "http://YOUR_LAPTOP_IP:5000/log";
```

---

## ESP32 Pin Mapping

| GPIO | Component |
|------|-----------|
| 2 | Buzzer Signal |
| 13, 12, 14, 27 | Keypad Rows 1-4 |
| 26, 25, 33 | Keypad Columns 1-3 |
| 21 (SDA) | LCD I2C Data |
| 22 (SCL) | LCD I2C Clock |
| 32 | Servo Signal |
| 34 (AO) | MQ-2 Gas Sensor |
| 35 | PIR Motion Sensor |

---

## Deliverables

Full technical report, demo video, and a dataset we published on Kaggle.

## Team

Built with my ITT569 project team, full credit in the report.

## License

Academic project for ITT569, UiTM. Feel free to reference the architecture if it's useful for your own IoT security build.
