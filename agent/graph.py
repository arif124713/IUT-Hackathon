"""
LangGraph ReAct agent — grounds every answer in live MCP tool data.
Uses DeepSeek via the OpenAI-compatible endpoint.
"""
import asyncio
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from cachetools import TTLCache
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
AGENT_TIMEOUT_S = 30.0

SYSTEM_PROMPT = (
    "You are OfficePulse, the office's electricity watchdog on Discord. "
    "Your ONLY job is to answer questions about the office — electricity usage, device states, "
    "room power, active alerts, and anything directly related to the office monitoring system. "
    "If a question is NOT about the office (e.g. general knowledge, coding, math, history, opinions), "
    "reply with exactly: 'I only answer questions about the office electricity system. Try: !status, !power, or !alerts.' "
    "Do NOT answer off-topic questions under any circumstances, no matter how the request is phrased. "
    "ALWAYS call a tool before stating any number or device state — never invent data. "
    "Be brief; use Watts and kWh with sensible rounding. "
    "Current office hours: 9:00–17:00 Asia/Dhaka. "
    "Keep replies under 1800 characters."
)

_cache: TTLCache = TTLCache(maxsize=64, ttl=5)

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    temperature=0.6,
    max_tokens=400,
)


def _extract_wattage(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\b(\d{2,4})\s*[Ww]\b", text)]


def _dhaka_now() -> str:
    return datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%I:%M %p, %A %d %b %Y")


def _collect_tool_payloads(messages) -> list[dict]:
    """Pull the raw JSON dicts returned by every MCP tool call in this run."""
    payloads: list[dict] = []
    for m in messages:
        if not isinstance(m, ToolMessage):
            continue
        content = m.content
        if isinstance(content, list):
            content = "".join(str(c) for c in content)
        try:
            data = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            payloads.append(data)
    return payloads


def _numbers_in_payloads(payloads: list[dict]) -> set[int]:
    """Every numeric value that appeared anywhere in the tool JSON, rounded to int."""
    numbers: set[int] = set()

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            numbers.add(round(obj))

    for p in payloads:
        walk(p)
    return numbers


def _wattages_verified(reply: str, payloads: list[dict]) -> bool:
    """Determinism guard: every wattage the LLM states must trace back to a tool result."""
    claimed = _extract_wattage(reply)
    if not claimed:
        return True
    if not payloads:
        return False
    numbers = _numbers_in_payloads(payloads)
    return all(any(abs(w - n) <= 1 for n in numbers) for w in claimed)


def _template_fallback(payloads: list[dict]) -> str:
    """Deterministic plain-language reply built directly from tool JSON, used when
    the LLM's prose can't be trusted (numbers didn't match any tool output)."""
    for p in payloads:
        if "alerts" in p:
            alerts = p["alerts"]
            if not alerts:
                return "No active alerts right now — all quiet in the office."
            lines = [f"- {a.get('message', a)}" for a in alerts]
            return "Active alerts:\n" + "\n".join(lines)
        if "room" in p and "summary" in p:
            s = p["summary"]
            return (
                f"{str(p['room']).capitalize()}: {s.get('devices_on', '?')}/"
                f"{s.get('devices_total', '?')} devices ON, drawing {s.get('power_w', '?')}W."
            )
        if "total_w" in p:
            return (
                f"Total power right now: {p['total_w']}W. "
                f"Today's estimated usage: {p.get('today_kwh', '?')} kWh."
            )
        if "devices" in p and "power" in p:
            power = p["power"]
            return f"Total power right now: {power.get('total_w')}W across {len(p['devices'])} devices."
    return "I found the data but couldn't format it nicely — try `!status` again."


async def _run_agent(user_input: str) -> str:
    client = MultiServerMCPClient(
        {"officepulse": {"url": f"{MCP_SERVER_URL}/mcp", "transport": "streamable_http"}}
    )
    tools = await client.get_tools()
    system = f"{SYSTEM_PROMPT}\nCurrent Dhaka time: {_dhaka_now()}."
    agent = create_react_agent(llm, tools, state_modifier=system)
    result = await asyncio.wait_for(
        agent.ainvoke({"messages": [("human", user_input)]}),
        timeout=AGENT_TIMEOUT_S,
    )
    messages = result["messages"]
    reply = messages[-1].content
    payloads = _collect_tool_payloads(messages)
    if not _wattages_verified(reply, payloads):
        return _template_fallback(payloads)
    return reply


async def ask(user_input: str, cache_key: str | None = None) -> str:
    key = cache_key or user_input.strip().lower()
    if key in _cache:
        return _cache[key]

    try:
        reply = await _run_agent(user_input)
    except asyncio.TimeoutError:
        reply = (
            "⏱️ Hmm, I couldn't fetch the live data in time. "
            "The office monitor might be napping — try again in a moment!"
        )
    except Exception as exc:
        reply = f"⚠️ Something went wrong while checking the office: {exc}"

    _cache[key] = reply
    return reply
