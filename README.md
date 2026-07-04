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

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running Each Service](#running-each-service)
- [API Reference](#api-reference)
- [Discord Bot Commands](#discord-bot-commands)
- [Frontend Features](#frontend-features)
- [How the Simulator Works](#how-the-simulator-works)
- [Alert Rules](#alert-rules)
- [Docker Deployment](#docker-deployment)

---

## Overview

OfficePulse tracks 15 virtual devices (fans + lights) across 3 office rooms, simulates realistic on/off patterns based on time-of-day, streams live updates over WebSocket, and lets you query the office state via a Discord bot powered by a DeepSeek LLM agent.

**Key capabilities:**
- 📊 Live power dashboard (watts, kWh, per-room breakdown)
- 🗺️ Animated SVG floor plan — fans spin, lights glow when ON
- 🤖 Discord bot with natural-language queries via LangGraph ReAct agent
- 🔔 Proactive Discord alerts for after-hours devices and marathon sessions
- 🏗️ MCP (Model Context Protocol) server bridges the LLM to live office data

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│  ┌──────────────────────┐        ┌────────────────────────────┐ │
│  │  React Frontend       │        │    Discord Server          │ │
│  │  localhost:5173       │        │    (bot commands + alerts) │ │
│  └──────────┬───────────┘        └─────────────┬──────────────┘ │
│             │ WebSocket + REST                  │ discord.py     │
└─────────────┼───────────────────────────────────┼───────────────┘
              │                                   │
┌─────────────▼───────────────────────────────────▼───────────────┐
│                        Core Services                            │
│  ┌────────────────────────┐    ┌──────────────────────────────┐ │
│  │  FastAPI Backend        │    │   Discord Bot + LangGraph    │ │
│  │  localhost:8000         │    │   ReAct Agent (DeepSeek LLM) │ │
│  │  • REST API             │    └──────────────┬───────────────┘ │
│  │  • WebSocket /ws/live   │                   │ MCP tools       │
│  │  • Markov Simulator     │    ┌──────────────▼───────────────┐ │
│  │  • Alerts Engine        │◄───│   FastMCP Server             │ │
│  └───────────┬─────────────┘    │   localhost:8001             │ │
│              │ SQLAlchemy async  └──────────────────────────────┘ │
│  ┌───────────▼─────────────┐                                     │
│  │  MySQL 8.0 Database      │                                     │
│  │  devices / events /      │                                     │
│  │  alerts tables           │                                     │
│  └─────────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow for a Discord `!status` command:**
1. User types `!status` → discord.py bot receives it
2. Bot calls `agent.ask()` → LangGraph ReAct agent initialises
3. Agent fetches tools from MCP server (`get_office_status`, `get_power_usage`, etc.)
4. Agent calls tools → MCP server calls Backend REST API → reads MySQL
5. DeepSeek LLM formats the response with live data
6. Bot sends the formatted reply back to Discord

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13, FastAPI 0.139, SQLAlchemy 2.0 async, aiomysql |
| **Database** | MySQL 8.0 |
| **Simulator** | Markov-chain scheduler (time-of-day buckets) |
| **WebSocket** | asyncio.Queue broadcaster fan-out |
| **MCP Server** | `mcp` 1.28 (FastMCP), streamable-HTTP transport |
| **AI Agent** | LangGraph 0.2.60 ReAct, langchain-mcp-adapters 0.1.14 |
| **LLM** | DeepSeek (`deepseek-chat`) via OpenAI-compatible API |
| **Discord Bot** | discord.py 2.4, proactive alert poller |
| **Frontend** | React 18, Vite 6, Recharts, custom SVG animations |
| **Deployment** | Docker + Docker Compose |

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
│   │   ├── db.py             # Async engine + session factory
│   │   ├── config.py         # pydantic-settings (reads .env)
│   │   ├── schemas.py        # Pydantic response schemas
│   │   └── ws.py             # WebSocket connection manager
│   ├── tests/
│   │   └── test_power.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── mcp_server/               # Model Context Protocol server
│   ├── server.py             # 5 MCP tools wrapping backend REST
│   ├── requirements.txt
│   └── Dockerfile
│
├── agent/                    # LangGraph ReAct agent
│   ├── graph.py              # DeepSeek LLM + MCP tool binding
│   └── requirements.txt
│
├── bot/                      # Discord bot
│   ├── main.py               # Commands + proactive alert poller
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── App.jsx           # Root layout + live Dhaka clock
│   │   ├── hooks/
│   │   │   └── useLiveOffice.js   # WebSocket delta-reduction hook
│   │   ├── components/
│   │   │   ├── OfficeMap.jsx      # Animated SVG floor plan
│   │   │   ├── DeviceTile.jsx     # Fan/light tiles with animations
│   │   │   ├── PowerMeter.jsx     # Gauge + per-room bars
│   │   │   ├── PowerTrendChart.jsx # Recharts line chart
│   │   │   ├── AlertsPanel.jsx    # Active + resolved alerts
│   │   │   ├── RoomCard.jsx       # Room device grid
│   │   │   └── ConnectionChip.jsx # WebSocket status indicator
│   │   ├── styles/
│   │   │   └── global.css         # Dark theme + SVG animations
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── nginx.conf
│   └── Dockerfile
│
├── docker-compose.yml        # One-command full stack deployment
├── .env.example              # Copy to .env and fill in secrets
├── office-pulse-spec.md      # Original specification
└── README.md
```

---

## Prerequisites

- **Python 3.13+**
- **Node.js 18+** and npm
- **MySQL 8.0** running locally (or via Docker)
- A **DeepSeek API key** — [platform.deepseek.com](https://platform.deepseek.com)
- A **Discord bot token** — [discord.com/developers](https://discord.com/developers/applications)

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
# Edit .env with your credentials (see Configuration below)
```

### 3. Create the MySQL database

```sql
CREATE DATABASE officepulse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Create and activate a Python virtual environment

```bash
python -m venv myenv

# Windows
myenv\Scripts\activate

# macOS / Linux
source myenv/bin/activate
```

### 5. Install Python dependencies

```bash
pip install -r backend/requirements.txt
pip install -r mcp_server/requirements.txt
pip install -r agent/requirements.txt
pip install -r bot/requirements.txt
pip install cryptography audioop-lts  # MySQL sha2 auth + Python 3.13 compat
```

### 6. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 7. Start all services (4 terminals)

```bash
# Terminal 1 — Backend
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — MCP Server
python mcp_server/server.py

# Terminal 3 — Discord Bot
python bot/main.py

# Terminal 4 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Configuration

Copy `.env.example` to `.env` and fill in every value:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Full MySQL connection string |
| `MYSQL_PASSWORD` | MySQL root password |
| `DEEPSEEK_API_KEY` | DeepSeek API key from platform.deepseek.com |
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal → Bot tab |
| `ALERT_CHANNEL_ID` | Discord channel ID for proactive alerts (right-click → Copy ID) |
| `TZ` | Timezone for office hours (default: `Asia/Dhaka`) |
| `OFFICE_OPEN` | Office open time in `HH:MM` format (default: `09:00`) |
| `OFFICE_CLOSE` | Office close time in `HH:MM` format (default: `17:00`) |
| `SIM_TICK_SECONDS` | How often the simulator ticks (default: `5`) |
| `MARATHON_MINUTES` | Minutes before a "marathon room" alert fires (default: `120`) |

### Discord Bot Setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new application → Bot tab → **Reset Token** → copy it to `DISCORD_BOT_TOKEN`
3. Under **Privileged Gateway Intents**, enable **MESSAGE CONTENT INTENT**
4. OAuth2 → URL Generator → Scopes: `bot` → Permissions: `Read Messages`, `Send Messages`, `Embed Links`, `Read Message History`
5. Open the generated URL to invite the bot to your server
6. Right-click your alert channel → **Copy Channel ID** → paste to `ALERT_CHANNEL_ID`

---

## Running Each Service

### Backend (FastAPI)

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On startup it:
- Creates all database tables (if not present)
- Seeds 15 devices across 3 rooms (if not present)
- Starts the Markov device simulator
- Starts the alerts rules engine

### MCP Server

```bash
python mcp_server/server.py
```

Runs on **port 8001**, exposes 5 tools over streamable-HTTP for the LangGraph agent.

### Discord Bot

```bash
python bot/main.py
```

Connects to Discord Gateway and starts polling for alerts every 20 seconds.

### Frontend (dev)

```bash
cd frontend
npm run dev        # http://localhost:5173
npm run build      # production build → dist/
npm run preview    # preview production build
```

---

## API Reference

Base URL: `http://localhost:8000`

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

### Demo Scenarios (`DEMO_MODE=true`)

```bash
curl -X POST http://localhost:8000/sim/scenario -H "Content-Type: application/json" \
     -d '{"scenario": "peak_load"}'
# Options: "peak_load" | "all_off" | "after_hours_leftover"
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
| `@OfficePulse <question>` | Ask anything in plain English |

The bot uses a **LangGraph ReAct agent** — it always calls live MCP tools before answering, so numbers are never fabricated.

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
| **Flip animation** | Device tiles animate on state change |

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
| `after_hours` | Any device ON outside `OFFICE_OPEN`–`OFFICE_CLOSE` | When all devices in that room turn off, or office hours resume |
| `marathon_room` | All devices in a room ON continuously for `MARATHON_MINUTES` | When any device in the room turns off |

Active alerts are broadcast over WebSocket and announced in Discord (rate-limited to once per 30 minutes per room+type).

---

## Docker Deployment

A `docker-compose.yml` is included for one-command deployment:

```bash
# Copy and fill in your secrets
cp .env.example .env

# Build and start everything
docker compose up --build

# Services:
#   Frontend  → http://localhost:5173
#   Backend   → http://localhost:8000
#   MCP       → http://localhost:8001
#   MySQL     → localhost:3306
```

Individual service builds:

```bash
docker build -t officepulse-backend  ./backend
docker build -t officepulse-mcp      ./mcp_server
docker build -t officepulse-bot      ./bot
docker build -t officepulse-frontend ./frontend
```

---

## License

MIT — built for the IUT Hackathon.
