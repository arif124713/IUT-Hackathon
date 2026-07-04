---
title: OfficePulse
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Real-time office electricity monitor with AI Discord bot
---

# ⚡ OfficePulse — Real-Time Office Electricity Monitor

> **IUT Hackathon Project** — A full-stack, AI-powered system that monitors, simulates, and reports on office electricity consumption in real time.

---

## 🚀 Live Demo

| Service | Link |
|---|---|
| **Live Web App** | 🌐 [arif124713-officepulse.hf.space](https://arif124713-officepulse.hf.space) |
| **GitHub Repo** | 💻 [github.com/arif124713/IUT-Hackathon](https://github.com/arif124713/IUT-Hackathon) |
| **Join Discord Server** | 💬 [discord.gg/x6T93a2J](https://discord.gg/x6T93a2J) — test the bot live |
| **Add Bot to Your Server** | 🤖 [Invite OfficePulse Bot](https://discord.com/oauth2/authorize?client_id=1522825819926433943&permissions=2048&scope=bot) |
| **Demo Video** | 🎬 [Watch on YouTube](https://youtu.be/6eLO_481F8w) |

---

## Table of Contents

- [Overview](#overview)
- [MCP — The Core Innovation](#mcp--the-core-innovation)
- [Architecture](#architecture)
- [Hardware Design](#hardware-design)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Discord Bot Commands](#discord-bot-commands)
- [Frontend Features](#frontend-features)
- [How the Simulator Works](#how-the-simulator-works)
- [Alert Rules](#alert-rules)
- [Assumptions](#assumptions)

---

## Overview

OfficePulse tracks 15 virtual devices (fans + lights) across 3 office rooms, simulates realistic on/off patterns based on time-of-day, streams live updates over WebSocket, and lets you query the office state via a Discord bot powered by a DeepSeek LLM agent.

**Key capabilities:**
- 📊 Live power dashboard (watts, kWh, per-room breakdown) — hosted on Hugging Face Spaces
- 🗺️ Animated SVG floor plan — fans spin, lights glow when ON
- 🤖 Discord bot with natural-language queries via LangGraph ReAct agent
- 🔔 Proactive Discord alerts for after-hours devices and marathon sessions
- 🏗️ **MCP (Model Context Protocol)** — the bridge between the LLM and live office data

---

## MCP — The Core Innovation

> **Model Context Protocol (MCP)** is an open standard by Anthropic that lets AI models call external tools and data sources in a structured, verifiable way.

In OfficePulse, MCP is the critical layer that makes AI answers trustworthy:

```
Discord User
     │
     ▼
LangGraph ReAct Agent  ←── DeepSeek LLM (reasons about what to do)
     │
     │  calls tools via MCP (streamable-HTTP transport)
     ▼
┌─────────────────────────────────────────┐
│         FastMCP Server  (port 8001)     │
│                                         │
│  • get_office_status()                  │
│  • get_room_status(room)                │
│  • get_power_usage()                    │
│  • get_active_alerts()                  │
│  • get_device_history(device_id)        │
└──────────────┬──────────────────────────┘
               │  HTTP calls to REST API
               ▼
       FastAPI Backend  →  SQLite / MySQL DB
```

**Why MCP matters:**
- The LLM **never fabricates data** — it must call a tool before stating any number
- Tools are **self-describing** (name + docstring), so the agent discovers capabilities automatically
- The `streamable-HTTP` transport works over standard HTTPS — no special infrastructure needed
- Swapping the LLM (DeepSeek → GPT-4 → Claude) requires **zero changes** to the tools layer

**MCP tools exposed:**

| Tool | What it returns |
|---|---|
| `get_office_status()` | Full device snapshot grouped by room + total power |
| `get_room_status(room)` | All devices and power for a specific room |
| `get_power_usage()` | Total watts, per-room watts, today's kWh |
| `get_active_alerts()` | All currently active alerts with messages |
| `get_device_history(device_id)` | Recent state-change events for a device |

---

## Architecture

> Official diagram: [`diagrams/system-architecture.svg`](diagrams/system-architecture.svg)

![OfficePulse System Architecture](diagrams/system-architecture.svg)

The sketch below is illustrative — the SVG above is the definitive diagram:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Interfaces                           │
│  ┌───────────────────────────────┐   ┌────────────────────────────┐ │
│  │  React Frontend (Vite)        │   │    Discord Server          │ │
│  │  arif124713-officepulse.hf.space│  │    (bot commands + alerts) │ │
│  └──────────────┬────────────────┘   └────────────┬───────────────┘ │
│                 │ WebSocket + REST                 │ discord.py      │
└─────────────────┼─────────────────────────────────┼─────────────────┘
                  │                                  │
┌─────────────────▼─────────────────────────────────▼─────────────────┐
│                          Core Services                              │
│  ┌─────────────────────────────┐   ┌──────────────────────────────┐ │
│  │  FastAPI Backend            │   │  Discord Bot + LangGraph     │ │
│  │  (Hugging Face Spaces)      │   │  ReAct Agent  (local)        │ │
│  │  • REST API                 │   │  DeepSeek LLM                │ │
│  │  • WebSocket /ws/live       │   └──────────────┬───────────────┘ │
│  │  • Markov Simulator         │                  │                 │
│  │  • Alerts Engine            │   ┌──────────────▼───────────────┐ │
│  │                             │◄──│  FastMCP Server  (local)     │ │
│  └──────────────┬──────────────┘   │  streamable-HTTP transport   │ │
│                 │ SQLAlchemy async  │  5 MCP tools                 │ │
│  ┌──────────────▼──────────────┐   └──────────────────────────────┘ │
│  │  SQLite (HF) / MySQL (local)│                                    │
│  └─────────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘
```

**Data flow for a Discord `!status` command:**
1. User types `!status` → discord.py bot receives it
2. Bot calls `agent.ask()` → LangGraph ReAct agent initialises
3. Agent fetches tool schemas from the **MCP server** (`get_office_status`, `get_power_usage`, etc.)
4. Agent calls tools → MCP server calls Backend REST API → reads database
5. DeepSeek LLM formats the response with **live, verified data**
6. Bot sends the formatted reply back to Discord

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI 0.139, SQLAlchemy 2.0 async |
| **Database** | SQLite (cloud/HF) · MySQL 8.0 (local) |
| **Simulator** | Markov-chain scheduler (time-of-day buckets) |
| **WebSocket** | asyncio.Queue broadcaster fan-out |
| **MCP Server** | `mcp` 1.28 (FastMCP), streamable-HTTP transport  |
| **AI Agent** | LangGraph 0.2.60 ReAct, langchain-mcp-adapters 0.1.14 |
| **LLM** | DeepSeek (`deepseek-chat`) via OpenAI-compatible API |
| **Discord Bot** | discord.py 2.4, proactive alert poller |
| **Frontend** | React 18, Vite 6, Recharts, custom SVG animations |
| **Hosting** | Hugging Face Spaces (Docker), nginx reverse proxy |

---

## Project Structure

```
IUT/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # Routes, WebSocket, lifespan startup
│   │   ├── models.py         # SQLAlchemy ORM (Device, StateEvent, Alert)
│   │   ├── simulator.py      # Markov device simulator
│   │   ├── alerts.py         # Alerts rules engine
│   │   ├── power.py          # kWh integration
│   │   ├── db.py             # Async engine + session factory (SQLite/MySQL)
│   │   ├── config.py         # pydantic-settings (reads .env)
│   │   ├── schemas.py        # Pydantic response schemas
│   │   └── ws.py             # WebSocket connection manager
│   └── requirements.txt
│
├── mcp_server/               # ⭐ Model Context Protocol server
│   └── server.py             # 5 MCP tools over streamable-HTTP
│
├── agent/                    # LangGraph ReAct agent
│   ├── graph.py              # DeepSeek LLM + MCP tool binding
│   └── requirements.txt
│
├── bot/                      # Discord bot
│   └── main.py               # Commands + proactive alert poller
│
├── frontend/                 # React + Vite
│   └── src/
│       ├── App.jsx           # Root layout + live Dhaka clock
│       ├── hooks/useLiveOffice.js   # WebSocket delta-reduction hook
│       └── components/       # OfficeMap, DeviceTile, PowerMeter, etc.
│
├── diagrams/                 # Hardware + architecture diagrams
│   ├── system-architecture.svg    # Official system architecture diagram
│   ├── esp32_room_monitor.ino     # ESP32 firmware sketch
│   └── wokwi-link.md             # Wokwi simulation link + build guide
│
├── Dockerfile                # HF Spaces Docker build
├── nginx.hf.conf             # nginx: serves React + proxies API/WS/MCP
├── start.sh                  # Startup: backend → MCP → nginx
├── requirements.hf.txt       # Combined Python deps for HF deployment
├── .env.example              # Copy to .env and fill in secrets
└── README.md
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/arif124713/IUT-Hackathon.git
cd IUT-Hackathon
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Create a Python virtual environment

```bash
python -m venv myenv
myenv\Scripts\activate      # Windows
source myenv/bin/activate   # macOS / Linux
```

### 4. Install dependencies

```bash
pip install -r backend/requirements.txt
pip install -r mcp_server/requirements.txt
pip install -r agent/requirements.txt
pip install -r bot/requirements.txt
```

### 5. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 6. Start all services (4 terminals)

```bash
# Terminal 1 — Backend (FastAPI)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — MCP Server ⭐
python mcp_server/server.py

# Terminal 3 — Discord Bot
python bot/main.py

# Terminal 4 — Frontend
cd frontend && npm run dev
```

Frontend runs at the Vite dev server URL shown in the terminal.

> **Or use the live cloud deployment:** [arif124713-officepulse.hf.space](https://arif124713-officepulse.hf.space)

---

## Configuration

Copy `.env.example` to `.env` and fill in every value:

| Variable | Description |
|---|---|
| `DATABASE_URL` | `mysql+aiomysql://user:pass@host:3306/officepulse` (local) or leave blank for SQLite (HF) |
| `DEEPSEEK_API_KEY` | API key from [platform.deepseek.com](https://platform.deepseek.com) |
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal → Bot tab |
| `ALERT_CHANNEL_ID` | Discord channel ID for proactive alerts |
| `BACKEND_URL` | Where the MCP server should call the backend (use live URL for cloud) |
| `MCP_SERVER_URL` | Where the agent connects to MCP (use `http://localhost:8001` locally) |
| `TZ` | Timezone (default: `Asia/Dhaka`) |
| `OFFICE_OPEN` / `OFFICE_CLOSE` | Office hours in `HH:MM` format |

### Discord Bot Setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new application → Bot tab → **Reset Token** → paste to `DISCORD_BOT_TOKEN`
3. Enable **MESSAGE CONTENT INTENT** under Privileged Gateway Intents
4. Use the [invite link](https://discord.com/oauth2/authorize?client_id=1522825819926433943&permissions=2048&scope=bot) to add the bot to your server

---

## API Reference

Base URL: `https://arif124713-officepulse.hf.space` (live) or your local backend

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/devices` | All devices (optional `?room=drawing`) |
| `GET` | `/api/rooms` | Per-room power summary |
| `GET` | `/api/power` | Total watts + today's kWh |
| `GET` | `/api/alerts` | All alerts (optional `?active=true`) |
| `GET` | `/api/summary` | Combined snapshot (devices + power + alerts) |
| `WS` | `/ws/live` | WebSocket stream of real-time events |
| `POST` | `/sim/scenario` | Force a demo scenario (requires `DEMO_MODE=true`) |

### WebSocket Events

```json
{ "event": "device_update", "data": { "id": "work1-fan-1", "status": true, "last_changed": "..." } }
{ "event": "power_update",  "data": { "total_w": 520, "by_room": { "work1": 190, ... } } }
{ "event": "alert",         "data": { "id": 1, "type": "after_hours", "room": "work1", "message": "..." } }
```

---

## Discord Bot Commands

| Command | Description |
|---|---|
| `!help` | Show all commands as an embed |
| `!status` | Full office device snapshot with AI commentary |
| `!room <name>` | Status for one room (`drawing`, `work1`, `work2`) |
| `!usage` | Current watts + today's estimated kWh |
| `!alerts` | List all active alerts |
| `@OfficePulse <question>` | Ask anything in plain English (office questions only) |

The bot uses a **LangGraph ReAct agent** — it always calls live MCP tools before answering, so numbers are never fabricated. Off-topic questions are refused.

[➕ Add OfficePulse to your Discord server](https://discord.com/oauth2/authorize?client_id=1522825819926433943&permissions=2048&scope=bot)

---

## Frontend Features

| Feature | Detail |
|---|---|
| **Live clock** | Ticks every second in Asia/Dhaka timezone |
| **WebSocket chip** | Green "LIVE" / red "Reconnecting" indicator |
| **Power gauge** | SVG dial showing total watts |
| **Room bars** | Per-room watt bars with smooth transitions |
| **kWh counter** | Today's accumulated energy usage |
| **SVG floor plan** | Fans spin (cyan) · Lights glow (amber) when ON |
| **Device tiles** | Per-device status, wattage, last-changed time |
| **Power trend** | 30-point rolling Recharts line chart |
| **Alerts panel** | Active (amber/red) + collapsible resolved alerts |

---

## How the Simulator Works

The simulator runs as an async background task. Every `SIM_TICK_SECONDS` seconds it evaluates each device:

```
P(turn ON  | currently OFF) = f(room, time_bucket)
P(turn OFF | currently ON)  = f(room, time_bucket)
```

Time buckets: `morning (9–13)` · `lunch (13–14)` · `afternoon (14–17)` · `evening (17–22)` · `night (22–9)`

Work rooms have high ON probability during office hours; the drawing room is more sporadic. Each flip is written to `StateEvent` and broadcast over WebSocket.

---

## Alert Rules

| Alert Type | Trigger | Auto-resolve |
|---|---|---|
| `after_hours` | Any device ON outside office hours | When all devices in that room turn off, or office hours resume |
| `marathon_room` | All devices in a room ON for `MARATHON_MINUTES` continuously | When any device turns off |

Active alerts are broadcast over WebSocket and announced in Discord (rate-limited to once per 30 minutes per room+type).

---

## Hardware Design

OfficePulse is designed for real deployment: one ESP32 per room reads five current-transformer sensors (one per device) and posts live data to the FastAPI backend over Wi-Fi. The simulator in the cloud runs the same Markov logic, making it a perfect stand-in until hardware is wired.

### Real-world component chain

| Stage | Component | Purpose |
|---|---|---|
| Sensing | ZMCT103C current transformer (× 5 per room) | Clamps around each device's live wire — galvanic isolation, mains never touches the MCU |
| Conditioning | Burden resistor + half-wave rectifier + RC smoothing | Converts CT secondary current → 0–3.3 V DC proportional to load |
| MCU | ESP32 DevKit v1 | 5 ADC reads, threshold logic, Wi-Fi uplink |
| Uplink | Wi-Fi → HTTP POST /ingest → FastAPI | Replaces the simulator in a real deployment |
| Power | 5 V USB adapter → ESP32 VIN | Standard bench supply |

**Key design decisions:**
- **Isolation:** CTs provide magnetic coupling only — no conductive path from 220 V AC to the 3.3 V logic rail. Resistive voltage dividers from mains are never used.
- **ADC1 only:** GPIOs 32–39 (ADC1) are used exclusively. ADC2 shares silicon with the ESP32 Wi-Fi radio — reading ADC2 while Wi-Fi is active returns garbage.
- **Detection:** RMS-proportional ADC value above threshold 300/4095 ≈ device ON; magnitude maps to `P ≈ V_mains × I` for approximate wattage.
- **Scaling:** One ESP32 per room (3 nodes) posting to the same backend — simpler wiring than a central node with a CD74HC4067 mux.

### Wokwi simulation mapping

Wokwi has no ZMCT103C model. Potentiometers stand in because both produce a 0–3.3 V proportional signal on an ADC pin.

| Real part | Wokwi stand-in | Why equivalent |
|---|---|---|
| CT + conditioning | Potentiometer on ADC pin | Both produce 0–3.3 V proportional to load current |
| Device on/off | Slide switch gating the pot output | Represents current present / absent |
| Detected state | LED per device (220 Ω) | Visual confirmation firmware detected ON |

### Pin map (ESP32 DevKit v1)

| Device | Wattage | Sense pin (ADC1) | Status LED pin |
|---|---|---|---|
| Fan 1 | 65 W | GPIO 32 | GPIO 16 |
| Fan 2 | 75 W | GPIO 33 | GPIO 17 |
| Light 1 | 15 W | GPIO 34 *(input-only)* | GPIO 18 |
| Light 2 | 15 W | GPIO 35 *(input-only)* | GPIO 19 |
| Light 3 | 20 W | GPIO 36 / VP *(input-only)* | GPIO 21 |

**Wiring:** pot left leg → 3V3, right leg → GND, wiper → sense pin. LED: GPIO → 220 Ω → anode, cathode → GND.

### Wokwi project

See [`diagrams/wokwi-link.md`](diagrams/wokwi-link.md) for the public simulation link and step-by-step build instructions.  
Firmware: [`diagrams/esp32_room_monitor.ino`](diagrams/esp32_room_monitor.ino)

> **Why Wokwi over Tinkercad:** Wokwi has first-class ESP32 support with Wi-Fi simulation and shareable text-based projects. Tinkercad's Arduino Uno has no Wi-Fi, which breaks the "posts to backend" story.

---

## Assumptions

The problem statement contains a device-count inconsistency that we address explicitly here rather than silently picking one number.

> **Canonical device count: 15** — 3 rooms × (2 fans + 3 lights) = 15 devices.
>
> The problem statement specifies the per-room composition as 2 fans + 3 lights but also says "all 18 devices" in several places. We implement the explicit room composition (15 devices). `FANS_PER_ROOM` and `LIGHTS_PER_ROOM` are configurable environment variables, so 18 devices (e.g., 3 fans + 3 lights) is a one-line `.env` change if the organizers clarify.
>
> Maximum office load at 15 devices: 2×(65+75) + 3×(15+15+20) = 280 + 150 = **430 W per room × 3 = 1290 W total** (fans vary by room; the simulator uses per-device wattages).

Other assumptions:
- Office timezone: **Asia/Dhaka** (UTC+6) — configurable via `TZ`
- Office hours: **09:00–17:00** — configurable via `OFFICE_OPEN` / `OFFICE_CLOSE`
- Simulator tick: **5 seconds** real time = 1 sim-second (configurable via `SIM_TICK_SECONDS`)
- Alert rate-limit: once per **30 minutes** per room+type to avoid Discord spam

---

## License

MIT — built for the IUT Hackathon.
