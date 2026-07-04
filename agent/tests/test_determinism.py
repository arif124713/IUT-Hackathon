"""
Golden tests for the determinism guard (spec §10.3, §16): the agent may only
state a wattage number that traces back to an actual MCP tool result. These
tests exercise the guard's pure functions directly with mocked tool output —
no real LLM or MCP server involved.
"""
import json

from langchain_core.messages import ToolMessage

from agent.graph import (
    _collect_tool_payloads,
    _numbers_in_payloads,
    _wattages_verified,
    _template_fallback,
)


def _tool_msg(payload: dict) -> ToolMessage:
    return ToolMessage(content=json.dumps(payload), tool_call_id="call_1")


def test_collect_tool_payloads_parses_json_tool_messages():
    messages = [_tool_msg({"total_w": 340, "today_kwh": 2.1})]
    assert _collect_tool_payloads(messages) == [{"total_w": 340, "today_kwh": 2.1}]


def test_collect_tool_payloads_ignores_non_json_content():
    messages = [ToolMessage(content="not json", tool_call_id="call_2")]
    assert _collect_tool_payloads(messages) == []


def test_numbers_in_payloads_walks_nested_structures():
    payloads = [{"room": "work1", "summary": {"power_w": 190}, "devices": [{"wattage": 65}]}]
    assert _numbers_in_payloads(payloads) >= {190, 65}


def test_wattages_verified_true_when_reply_matches_tool_output():
    payloads = [{"total_w": 340}]
    assert _wattages_verified("Total power right now: 340W.", payloads)


def test_wattages_verified_false_on_hallucinated_number():
    payloads = [{"total_w": 340}]
    assert not _wattages_verified("Total power right now: 999W.", payloads)


def test_wattages_verified_false_when_no_tool_was_called():
    assert not _wattages_verified("Total power right now: 340W.", [])


def test_wattages_verified_true_when_reply_has_no_numeric_claims():
    assert _wattages_verified("Everything looks quiet right now!", [])


def test_wattages_verified_tolerates_rounding():
    payloads = [{"total_w": 339.6}]
    assert _wattages_verified("Total power right now: 340W.", payloads)


def test_template_fallback_power_usage():
    text = _template_fallback([{"total_w": 340, "today_kwh": 2.1}])
    assert "340" in text and "2.1" in text


def test_template_fallback_empty_alerts():
    text = _template_fallback([{"alerts": []}])
    assert "No active alerts" in text


def test_template_fallback_room_status():
    payload = {"room": "work2", "summary": {"devices_on": 3, "devices_total": 5, "power_w": 190}}
    text = _template_fallback([payload])
    assert "Work2" in text and "3/5" in text and "190" in text
