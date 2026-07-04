"""
FastMCP server — thin wrappers over the backend REST API.
All tools go through the backend; no direct DB access here.
"""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_DHAKA = ZoneInfo("Asia/Dhaka")
from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

mcp = FastMCP(
    "OfficePulse MCP",
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path="/mcp",
)

ROOM_ALIASES: dict[str, str] = {
    "drawing room": "drawing",
    "drawing":      "drawing",
    "work room 1":  "work1",
    "work1":        "work1",
    "work 1":       "work1",
    "room 1":       "work1",
    "work room 2":  "work2",
    "work2":        "work2",
    "work 2":       "work2",
    "room 2":       "work2",
}


def _now_ts() -> str:
    return datetime.now(_DHAKA).strftime("%Y-%m-%d %H:%M:%S %Z")


async def _get(path: str) -> dict | list:
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=8.0) as client:
        r = await client.get(path)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def get_office_status() -> dict:
    """Return the full device snapshot grouped by room, plus current power."""
    data = await _get("/api/summary")
    return {**data, "generated_at": _now_ts()}


@mcp.tool()
async def get_room_status(room: str) -> dict:
    """
    Return all devices and power for a specific room.
    Accepts aliases like 'work room 1', 'drawing', etc.
    """
    key = ROOM_ALIASES.get(room.lower().strip())
    if key is None:
        return {
            "error": f"Unknown room '{room}'. Valid rooms: drawing, work1, work2.",
            "generated_at": _now_ts(),
        }
    devices = await _get(f"/api/devices?room={key}")
    rooms = await _get("/api/rooms")
    room_data = next((r for r in rooms if r["room"] == key), {})
    return {"room": key, "devices": devices, "summary": room_data, "generated_at": _now_ts()}


@mcp.tool()
async def get_power_usage() -> dict:
    """Return total_w, per-room watts, and today's estimated kWh."""
    data = await _get("/api/power")
    return {**data, "generated_at": _now_ts()}


@mcp.tool()
async def get_active_alerts() -> dict:
    """Return all currently active alerts."""
    alerts = await _get("/api/alerts?active=true")
    return {"alerts": alerts, "count": len(alerts), "generated_at": _now_ts()}


@mcp.tool()
async def get_device_history(device_id: str, limit: int = 10) -> dict:
    """
    Return recent state-change events for a specific device.
    Useful for 'when was fan 2 last turned on?' type questions.
    """
    return {
        "note": f"History endpoint not yet wired — device_id={device_id}, limit={limit}",
        "generated_at": _now_ts(),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
