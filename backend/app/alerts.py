"""
Alerts rules engine — evaluates every ALERTS_EVAL_SECONDS.

Rules:
  after_hours  — any device ON outside office hours
  marathon_room — all devices in a room ON continuously > MARATHON_MINUTES
"""
import asyncio
from datetime import datetime, timezone, timedelta, time as dtime
from zoneinfo import ZoneInfo
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .db import AsyncSessionLocal
from .models import Device, StateEvent, Alert
from .ws import manager

_running = False


def _is_office_hours(now_local: datetime, settings) -> bool:
    oh = dtime.fromisoformat(settings.office_open)
    oc = dtime.fromisoformat(settings.office_close)
    return oh <= now_local.time() < oc


async def _get_or_create_alert(
    session: AsyncSession, alert_type: str, room: str, message: str
) -> Alert:
    existing = (
        await session.execute(
            select(Alert).where(
                and_(Alert.type == alert_type, Alert.room == room, Alert.active == True)
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.message = message
        return existing

    alert = Alert(type=alert_type, room=room, message=message)
    session.add(alert)
    await session.flush()
    await manager.queue.put({
        "event": "alert",
        "data": {
            "id": alert.id,
            "type": alert.type,
            "room": alert.room,
            "message": alert.message,
            "triggered_at": alert.triggered_at.isoformat(),
        },
    })
    return alert


async def _resolve_alert(session: AsyncSession, alert: Alert):
    alert.active = False
    alert.resolved_at = datetime.now(timezone.utc)
    await manager.queue.put({
        "event": "alert",
        "data": {
            "id": alert.id,
            "type": alert.type,
            "room": alert.room,
            "message": alert.message,
            "active": False,
            "resolved_at": alert.resolved_at.isoformat(),
        },
    })


async def _evaluate(session: AsyncSession):
    settings = get_settings()
    tz = ZoneInfo(settings.tz)
    now_utc = datetime.utcnow()          # naive UTC — matches MySQL DATETIME
    now_local = datetime.now(tz)
    in_hours = _is_office_hours(now_local, settings)

    devices = (await session.execute(select(Device))).scalars().all()

    # Group by room
    by_room: dict[str, list[Device]] = {}
    for d in devices:
        by_room.setdefault(d.room, []).append(d)

    for room, devs in by_room.items():
        on_devs = [d for d in devs if d.status]

        # --- after_hours rule ---
        if not in_hours and on_devs:
            fans = [d for d in on_devs if d.type == "fan"]
            lights = [d for d in on_devs if d.type == "light"]
            parts = []
            if fans:
                parts.append(f"{len(fans)} fan{'s' if len(fans) > 1 else ''}")
            if lights:
                parts.append(f"{len(lights)} light{'s' if len(lights) > 1 else ''}")
            msg = (
                f"{room.capitalize()}: {' and '.join(parts)} still ON "
                f"at {now_local.strftime('%H:%M')} — outside office hours."
            )
            await _get_or_create_alert(session, "after_hours", room, msg)
        else:
            # Resolve any active after_hours alert for this room
            active = (
                await session.execute(
                    select(Alert).where(
                        and_(Alert.type == "after_hours", Alert.room == room, Alert.active == True)
                    )
                )
            ).scalar_one_or_none()
            if active:
                await _resolve_alert(session, active)

        # --- marathon_room rule ---
        if len(on_devs) == len(devs):  # all devices in room are ON
            # Find when the LAST device turned on (= room became fully ON)
            last_on_event = (
                await session.execute(
                    select(StateEvent)
                    .where(
                        and_(
                            StateEvent.device_id.in_([d.id for d in devs]),
                            StateEvent.new_status == True,
                        )
                    )
                    .order_by(StateEvent.changed_at_utc.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if last_on_event:
                on_since = last_on_event.changed_at_utc
                duration_min = (now_utc - on_since).total_seconds() / 60
                if duration_min >= settings.marathon_minutes:
                    hrs = int(duration_min // 60)
                    msg = (
                        f"{room.capitalize()}: all {len(devs)} devices have been ON "
                        f"for over {hrs} hour{'s' if hrs != 1 else ''}."
                    )
                    await _get_or_create_alert(session, "marathon_room", room, msg)
        else:
            active = (
                await session.execute(
                    select(Alert).where(
                        and_(
                            Alert.type == "marathon_room",
                            Alert.room == room,
                            Alert.active == True,
                        )
                    )
                )
            ).scalar_one_or_none()
            if active:
                await _resolve_alert(session, active)


async def run_alerts():
    import logging
    log = logging.getLogger("alerts")
    global _running
    _running = True
    settings = get_settings()
    log.info("Alerts engine started (eval every %ss)", settings.alerts_eval_seconds)

    try:
        while _running:
            await asyncio.sleep(settings.alerts_eval_seconds)
            async with AsyncSessionLocal() as session:
                await _evaluate(session)
                await session.commit()
    except Exception:
        log.exception("Alerts engine crashed — see traceback above")


def stop_alerts():
    global _running
    _running = False
