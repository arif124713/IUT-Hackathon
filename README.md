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
| **Add Bot to Server** | 🤖 [Invite OfficePulse Bot](https://discord.com/oauth2/authorize?client_id=1522825819926433943&permissions=2048&scope=bot) |

---

## Table of Contents

- [Overview](#overview)
- [MCP — The Core Innovation](#mcp--the-core-innovation)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Discord Bot Commands](#discord-bot-commands)
- [Frontend Features](#frontend-features)
- [How the Simulator Works](#how-the-simulator-works)
- [Alert Rules](#alert-rules)

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
| **MCP Server** | `mcp` 1.28 (FastMCP), streamable-HTTP transport ← *hackathon highlight* |
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

## License

MIT — built for the IUT Hackathon.
