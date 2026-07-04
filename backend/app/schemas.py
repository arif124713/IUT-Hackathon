from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    room: str
    type: str
    name: str
    status: bool
    wattage: float
    current_draw_w: float   # wattage if ON else 0
    last_changed: datetime


class RoomOut(BaseModel):
    room: str
    devices_on: int
    devices_total: int
    power_w: float


class PowerOut(BaseModel):
    total_w: float
    by_room: dict[str, float]
    today_kwh: float
    as_of: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    room: str
    message: str
    active: bool
    triggered_at: datetime
    resolved_at: datetime | None = None


class SummaryOut(BaseModel):
    devices: list[DeviceOut]
    power: PowerOut
    alerts: list[AlertOut]


class HealthOut(BaseModel):
    status: str
    uptime_s: float
    sim_running: bool


class ScenarioIn(BaseModel):
    scenario: str   # "after_hours_leftover" | "all_off" | "peak_load"


class ScenarioOut(BaseModel):
    applied: str


# WebSocket event payloads
class WsDeviceUpdate(BaseModel):
    event: str = "device_update"
    data: dict


class WsPowerUpdate(BaseModel):
    event: str = "power_update"
    data: dict


class WsAlert(BaseModel):
    event: str = "alert"
    data: dict
