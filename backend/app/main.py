import asyncio
import logging
import time as _time
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import init_db, get_db
from .models import Device, Alert
from .schemas import (
    DeviceOut, RoomOut, PowerOut, AlertOut, SummaryOut,
    HealthOut, ScenarioIn, ScenarioOut,
)
from .ws import manager
from .power import compute_today_kwh
from .simulator import seed_devices, run_simulator, stop_simulator, apply_scenario
from .alerts import run_alerts, stop_alerts

_start_time = _time.monotonic()
_sim_task: asyncio.Task | None = None
_alerts_task: asyncio.Task | None = None
_broadcaster_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sim_task, _alerts_task, _broadcaster_task
    await init_db()
    await seed_devices()
    _broadcaster_task = asyncio.create_task(manager.run_broadcaster())
    _sim_task = asyncio.create_task(run_simulator())
    _alerts_task = asyncio.create_task(run_alerts())
    yield
    stop_simulator()
    stop_alerts()
    for t in (_sim_task, _alerts_task, _broadcaster_task):
        if t:
            t.cancel()


settings = get_settings()

app = FastAPI(title="OfficePulse API", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _device_out(d: Device) -> DeviceOut:
    return DeviceOut(
        id=d.id,
        room=d.room,
        type=d.type,
        name=d.name,
        status=d.status,
        wattage=d.wattage,
        current_draw_w=d.wattage if d.status else 0.0,
        last_changed=d.last_changed_utc,
    )


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthOut)
async def health():
    return HealthOut(
        status="ok",
        uptime_s=round(_time.monotonic() - _start_time, 1),
        sim_running=_sim_task is not None and not _sim_task.done(),
    )


@app.get("/api/devices", response_model=list[DeviceOut])
async def get_devices(room: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    q = select(Device)
    if room:
        q = q.where(Device.room == room)
    devices = (await db.execute(q.order_by(Device.room, Device.id))).scalars().all()
    return [_device_out(d) for d in devices]


@app.get("/api/rooms", response_model=list[RoomOut])
async def get_rooms(db: AsyncSession = Depends(get_db)):
    devices = (await db.execute(select(Device).order_by(Device.room))).scalars().all()
    rooms: dict[str, list[Device]] = {}
    for d in devices:
        rooms.setdefault(d.room, []).append(d)
    result = []
    for room, devs in rooms.items():
        on = [d for d in devs if d.status]
        result.append(RoomOut(
            room=room,
            devices_on=len(on),
            devices_total=len(devs),
            power_w=sum(d.wattage for d in on),
        ))
    return result


@app.get("/api/power", response_model=PowerOut)
async def get_power(db: AsyncSession = Depends(get_db)):
    devices = (await db.execute(select(Device))).scalars().all()
    by_room: dict[str, float] = {}
    total = 0.0
    for d in devices:
        w = d.wattage if d.status else 0.0
        by_room[d.room] = by_room.get(d.room, 0.0) + w
        total += w
    kwh = await compute_today_kwh(db)
    return PowerOut(total_w=total, by_room=by_room, today_kwh=kwh, as_of=datetime.now(timezone.utc))


@app.get("/api/alerts", response_model=list[AlertOut])
async def get_alerts(active: bool | None = Query(None), db: AsyncSession = Depends(get_db)):
    q = select(Alert).order_by(Alert.triggered_at.desc())
    if active is not None:
        q = q.where(Alert.active == active)
    alerts = (await db.execute(q)).scalars().all()
    return alerts


@app.get("/api/summary", response_model=SummaryOut)
async def get_summary(db: AsyncSession = Depends(get_db)):
    devices = (await db.execute(select(Device))).scalars().all()
    by_room: dict[str, float] = {}
    total = 0.0
    for d in devices:
        w = d.wattage if d.status else 0.0
        by_room[d.room] = by_room.get(d.room, 0.0) + w
        total += w
    kwh = await compute_today_kwh(db)
    alerts = (
        await db.execute(select(Alert).where(Alert.active == True).order_by(Alert.triggered_at.desc()))
    ).scalars().all()
    return SummaryOut(
        devices=[_device_out(d) for d in devices],
        power=PowerOut(total_w=total, by_room=by_room, today_kwh=kwh, as_of=datetime.now(timezone.utc)),
        alerts=list(alerts),
    )


@app.post("/sim/scenario", response_model=ScenarioOut)
async def sim_scenario(body: ScenarioIn):
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="DEMO_MODE is not enabled")
    valid = {"after_hours_leftover", "all_off", "peak_load"}
    if body.scenario not in valid:
        raise HTTPException(status_code=400, detail=f"scenario must be one of {valid}")
    await apply_scenario(body.scenario)
    return ScenarioOut(applied=body.scenario)


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep-alive pings from client
    except WebSocketDisconnect:
        manager.disconnect(ws)
