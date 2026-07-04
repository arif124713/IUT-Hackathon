import asyncio
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Device, StateEvent
from .config import get_settings

_cache: tuple[float, float] | None = None
_cache_ttl = 2.0


def _local_midnight_naive_utc() -> datetime:
    """Return today's midnight in UTC as a naive datetime (MySQL stores naive)."""
    tz = ZoneInfo(get_settings().tz)
    now_local = datetime.now(tz)
    midnight_local = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    return midnight_local.astimezone(timezone.utc).replace(tzinfo=None)


def _now_naive_utc() -> datetime:
    return datetime.utcnow()


async def compute_today_kwh(session: AsyncSession) -> float:
    global _cache
    now = asyncio.get_event_loop().time()
    if _cache and (now - _cache[0]) < _cache_ttl:
        return _cache[1]

    midnight = _local_midnight_naive_utc()
    now_utc = _now_naive_utc()

    devices = (await session.execute(select(Device))).scalars().all()
    total_wh = 0.0

    for device in devices:
        events = (
            await session.execute(
                select(StateEvent)
                .where(
                    and_(
                        StateEvent.device_id == device.id,
                        StateEvent.changed_at_utc >= midnight,
                    )
                )
                .order_by(StateEvent.changed_at_utc)
            )
        ).scalars().all()

        pre_event = (
            await session.execute(
                select(StateEvent)
                .where(
                    and_(
                        StateEvent.device_id == device.id,
                        StateEvent.changed_at_utc < midnight,
                    )
                )
                .order_by(StateEvent.changed_at_utc.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        state_at_midnight = pre_event.new_status if pre_event else False

        timeline: list[tuple[datetime, bool]] = [(midnight, state_at_midnight)]
        for ev in events:
            # Strip tz if MySQL added one, keep naive UTC consistent
            ts = ev.changed_at_utc
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            timeline.append((ts, ev.new_status))
        timeline.append((now_utc, device.status))

        for i in range(len(timeline) - 1):
            ts, state = timeline[i]
            next_ts = timeline[i + 1][0]
            if state:
                duration_h = (next_ts - ts).total_seconds() / 3600
                total_wh += device.wattage * duration_h

    kwh = round(total_wh / 1000, 3)
    _cache = (now, kwh)
    return kwh
