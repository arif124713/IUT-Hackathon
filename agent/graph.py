"""
LangGraph ReAct agent — grounds every answer in live MCP tool data.
Uses DeepSeek via the OpenAI-compatible endpoint.
"""
import asyncio
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from cachetools import TTLCache
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
AGENT_TIMEOUT_S = 30.0

SYSTEM_PROMPT = (
    "You are OfficePulse, the office's friendly electricity watchdog on Discord. "
    "ALWAYS call a tool before stating any number or device state — never invent data. "
    "Be warm, brief, and lightly funny; the boss hates robotic data dumps. "
    "Use Watts and kWh with sensible rounding. "
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
    return result["messages"][-1].content


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
