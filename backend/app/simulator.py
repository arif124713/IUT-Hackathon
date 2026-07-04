"""
Schedule-driven Markov simulator.

Each tick re-evaluates P(flip) for every device based on time-of-day bucket.
Devices have realistic dwell times rather than random flicker.
"""
import asyncio
import json
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .db import AsyncSessionLocal
from .models import Device, StateEvent
from .ws import manager

# Fixed device seed — 15 devices across 3 rooms
ROOMS = ["drawing", "work1", "work2"]

DEVICE_SPECS = [
    # (id, room, type, name, wattage)
    ("drawing-fan-1",  "drawing", "fan",   "Drawing Fan 1",   65.0),
    ("drawing-fan-2",  "drawing", "fan",   "Drawing Fan 2",   75.0),
    ("drawing-light-1","drawing", "light", "Drawing Light 1", 15.0),
    ("drawing-light-2","drawing", "light", "Drawing Light 2", 15.0),
    ("drawing-light-3","drawing", "light", "Drawing Light 3", 20.0),
    ("work1-fan-1",    "work1",   "fan",   "Work1 Fan 1",     65.0),
    ("work1-fan-2",    "work1",   "fan",   "Work1 Fan 2",     75.0),
    ("work1-light-1",  "work1",   "light", "Work1 Light 1",   15.0),
    ("work1-light-2",  "work1",   "light", "Work1 Light 2",   15.0),
    ("work1-light-3",  "work1",   "light", "Work1 Light 3",   20.0),
    ("work2-fan-1",    "work2",   "fan",   "Work2 Fan 1",     65.0),
    ("work2-fan-2",    "work2",   "fan",   "Work2 Fan 2",     75.0),
    ("work2-light-1",  "work2",   "light", "Work2 Light 1",   15.0),
    ("work2-light-2",  "work2",   "light", "Work2 Light 2",   15.0),
    ("work2-light-3",  "work2",   "light", "Work2 Light 3",   20.0),
]


def _time_bucket(hour: int) -> str:
    if 9 <= hour < 13:
        return "morning"
    if 13 <= hour < 14:
        return "lunch"
    if 14 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


# P(turn ON | currently OFF), P(turn OFF | currently ON) per room per bucket
TRANSITION: dict[str, dict[str, tuple[float, float]]] = {
    "work1": {
        "morning":   (0.30, 0.03),
        "lunch":     (0.05, 0.20),
        "afternoon": (0.25, 0.04),
        "evening":   (0.02, 0.25),
        "night":     (0.00, 0.40),
    },
    "work2": {
        "morning":   (0.30, 0.03),
        "lunch":     (0.05, 0.20),
        "afternoon": (0.25, 0.04),
        "evening":   (0.02, 0.25),
        "night":     (0.00, 0.40),
    },
    "drawing": {
        "morning":   (0.08, 0.10),
        "lunch":     (0.05, 0.15),
        "afternoon": (0.08, 0.10),
        "evening":   (0.02, 0.30),
        "night":     (0.00, 0.50),
    },
}

_running = False


async def seed_devices():
    async with AsyncSessionLocal() as session:
        for spec in DEVICE_SPECS:
            existing = await session.get(Device, spec[0])
            if existing is None:
                session.add(Device(
                    id=spec[0], room=spec[1], type=spec[2],
                    name=spec[3], wattage=spec[4], status=False,
                ))
        await session.commit()


async def _flip(session: AsyncSession, device: Device, new_status: bool):
    now = datetime.utcnow()  # naive UTC — MySQL DATETIME has no tz
    device.status = new_status
    device.last_changed_utc = now
    session.add(StateEvent(device_id=device.id, new_status=new_status, changed_at_utc=now))
    await manager.queue.put({
        "event": "device_update",
        "data": {
            "id": device.id,
            "status": new_status,
            "last_changed": now.isoformat(),
        },
    })


async def run_simulator():
    import logging
    log = logging.getLogger("simulator")
    global _running
    _running = True
    settings = get_settings()
    tz = ZoneInfo(settings.tz)
    log.info("Simulator started (tick=%ss)", settings.sim_tick_seconds)

    try:
        while _running:
            await asyncio.sleep(settings.sim_tick_seconds / max(settings.sim_time_scale, 0.01))

            now_local = datetime.now(tz)
            hour = now_local.hour
            bucket = _time_bucket(hour)

            async with AsyncSessionLocal() as session:
                devices = (await session.execute(select(Device))).scalars().all()
                changed_rooms: set[str] = set()

                for device in devices:
                    p_on, p_off = TRANSITION.get(device.room, TRANSITION["work1"])[bucket]
                    roll = random.random()
                    if not device.status and roll < p_on:
                        await _flip(session, device, True)
                        changed_rooms.add(device.room)
                    elif device.status and roll < p_off:
                        await _flip(session, device, False)
                        changed_rooms.add(device.room)

                if changed_rooms:
                    await session.commit()
                    power_by_room: dict[str, float] = {}
                    total = 0.0
                    all_devs = (await session.execute(select(Device))).scalars().all()
                    for d in all_devs:
                        w = d.wattage if d.status else 0.0
                        power_by_room[d.room] = power_by_room.get(d.room, 0.0) + w
                        total += w
                    await manager.queue.put({
                        "event": "power_update",
                        "data": {"total_w": total, "by_room": power_by_room},
                    })
    except Exception:
        log.exception("Simulator crashed — see traceback above")


async def apply_scenario(scenario: str):
    """Force a demo scenario into the DB."""
    async with AsyncSessionLocal() as session:
        devices = (await session.execute(select(Device))).scalars().all()
        if scenario == "all_off":
            for d in devices:
                if d.status:
                    await _flip(session, d, False)
        elif scenario == "peak_load":
            for d in devices:
                if not d.status:
                    await _flip(session, d, True)
        elif scenario == "after_hours_leftover":
            for d in devices:
                target = d.room in ("work1", "work2")
                if d.status != target:
                    await _flip(session, d, target)
        await session.commit()


def stop_simulator():
    global _running
    _running = False
