"""
API + WebSocket integration tests (spec §16).

Uses FastAPI's in-process TestClient (no real server, no real network) against
an isolated SQLite DB configured in conftest.py, so these are safe to run
repeatedly without touching the dev MySQL database.

A single module-scoped client is shared across all tests: `ws.manager` holds a
process-wide `asyncio.Queue` created at import time, and repeatedly entering/
exiting `TestClient(app)` spins up a fresh event loop each time, which can
strand that queue on a closed loop. One client -> one loop -> no cross-loop
queue reuse.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["sim_running"] is True


def test_devices_seeded_correctly(client):
    r = client.get("/api/devices")
    assert r.status_code == 200
    devices = r.json()
    assert len(devices) == 15
    assert {d["room"] for d in devices} == {"drawing", "work1", "work2"}
    assert len([d for d in devices if d["type"] == "fan"]) == 6
    assert len([d for d in devices if d["type"] == "light"]) == 9


def test_devices_filtered_by_room(client):
    r = client.get("/api/devices", params={"room": "work1"})
    devices = r.json()
    assert len(devices) == 5
    assert all(d["room"] == "work1" for d in devices)


def test_rooms_rollup_matches_devices(client):
    devices = client.get("/api/devices").json()
    rooms = client.get("/api/rooms").json()
    assert {r["room"] for r in rooms} == {"drawing", "work1", "work2"}
    for room in rooms:
        room_devices = [d for d in devices if d["room"] == room["room"]]
        assert room["devices_total"] == len(room_devices)


def test_power_totals_match_device_states(client):
    devices = client.get("/api/devices").json()
    power = client.get("/api/power").json()
    expected_total = sum(d["wattage"] for d in devices if d["status"])
    assert power["total_w"] == expected_total
    assert power["today_kwh"] >= 0


def test_alerts_endpoint_shape(client):
    r = client.get("/api/alerts", params={"active": True})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_summary_combines_devices_power_alerts(client):
    body = client.get("/api/summary").json()
    assert len(body["devices"]) == 15
    assert "total_w" in body["power"]
    assert isinstance(body["alerts"], list)


def test_scenario_peak_load_turns_everything_on(client):
    r = client.post("/sim/scenario", json={"scenario": "peak_load"})
    assert r.status_code == 200
    devices = client.get("/api/devices").json()
    assert all(d["status"] for d in devices)


def test_scenario_rejects_invalid_name(client):
    r = client.post("/sim/scenario", json={"scenario": "not-a-real-scenario"})
    assert r.status_code == 400


def test_device_history_reflects_forced_scenario(client):
    client.post("/sim/scenario", json={"scenario": "all_off"})
    client.post("/sim/scenario", json={"scenario": "peak_load"})
    device_id = client.get("/api/devices").json()[0]["id"]

    r = client.get(f"/api/devices/{device_id}/history")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
    assert events[0]["device_id"] == device_id
    assert events[0]["new_status"] is True


def test_device_history_unknown_device_404(client):
    r = client.get("/api/devices/does-not-exist/history")
    assert r.status_code == 404


def test_websocket_receives_event_on_forced_scenario(client):
    with client.websocket_connect("/ws/live") as ws:
        r = client.post("/sim/scenario", json={"scenario": "all_off"})
        assert r.status_code == 200

        seen_events = set()
        for _ in range(30):
            msg = ws.receive_json()
            seen_events.add(msg["event"])
            if seen_events & {"device_update", "power_update"}:
                break
        assert seen_events & {"device_update", "power_update"}
