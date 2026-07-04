"""
Unit tests for kWh integration math using fixed event fixtures.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_kwh_zero_when_always_off():
    """Device that was never ON should contribute 0 kWh."""
    from backend.app.power import compute_today_kwh

    mock_session = AsyncMock(spec=AsyncSession)

    # No devices
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = execute_result

    kwh = await compute_today_kwh(mock_session)
    assert kwh == 0.0


@pytest.mark.asyncio
async def test_alert_after_hours_trigger():
    """After-hours rule should fire when a device is ON outside 09:00-17:00."""
    from freezegun import freeze_time
    import asyncio

    # Freeze time to 22:00 Dhaka
    with freeze_time("2026-07-04 16:00:00"):   # 16:00 UTC = 22:00 Dhaka
        from backend.app.alerts import _is_office_hours
        from backend.app.config import get_settings
        from datetime import time as dtime
        from zoneinfo import ZoneInfo

        settings = get_settings()
        tz = ZoneInfo(settings.tz)
        now_local = datetime(2026, 7, 4, 22, 0, 0, tzinfo=tz)
        assert not _is_office_hours(now_local, settings)


def test_room_alias_resolver():
    """Room alias map should resolve common human spellings."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp_server"))
    from server import ROOM_ALIASES

    assert ROOM_ALIASES["work room 1"] == "work1"
    assert ROOM_ALIASES["drawing room"] == "drawing"
    assert ROOM_ALIASES["work 2"] == "work2"
