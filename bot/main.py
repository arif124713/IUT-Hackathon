"""
OfficePulse Discord bot.

Commands:  !status  !room <name>  !usage  !alerts  !help
Mention:   @OfficePulse <free text>  → full agent mode
Proactive: polls /api/alerts every 20 s, announces new ones.
"""
import asyncio
import os
import sys

import discord
import httpx
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Allow importing agent from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.graph import ask

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID", "0"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Track last seen alert id to avoid re-announcing
_last_alert_id: int = 0
# Rate-limit: (type, room) → last_announced_ts
_announce_rate: dict[tuple[str, str], float] = {}
RATE_LIMIT_S = 30 * 60


async def _backend_get(path: str) -> dict | list | None:
    try:
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=6.0) as client:
            r = await client.get(path)
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


def _canned_error() -> str:
    return "⚠️ I can't reach the office monitor right now. Try again in a moment!"


# ── Commands ────────────────────────────────────────────────────────────────

@bot.command(name="status")
async def cmd_status(ctx):
    async with ctx.typing():
        reply = await ask("Give me a friendly summary of all office devices and current power usage.", "status")
    await ctx.send(reply)


@bot.command(name="room")
async def cmd_room(ctx, *, room_name: str = ""):
    if not room_name:
        await ctx.send("Usage: `!room <drawing | work1 | work2>`")
        return
    async with ctx.typing():
        reply = await ask(f"What is the current status of {room_name}?", f"room:{room_name.lower()}")
    await ctx.send(reply)


@bot.command(name="usage")
async def cmd_usage(ctx):
    async with ctx.typing():
        reply = await ask("What is the current total power usage and today's estimated kWh?", "usage")
    await ctx.send(reply)


@bot.command(name="alerts")
async def cmd_alerts(ctx):
    async with ctx.typing():
        reply = await ask("Are there any active office alerts right now?", "alerts")
    await ctx.send(reply)


@bot.command(name="help")
async def cmd_help(ctx):
    embed = discord.Embed(
        title="OfficePulse Commands",
        color=discord.Color.from_str("#00bcd4"),
    )
    embed.add_field(name="!status",       value="Full office device snapshot",         inline=False)
    embed.add_field(name="!room <name>",  value="Status for one room (drawing/work1/work2)", inline=False)
    embed.add_field(name="!usage",        value="Current watts + today's kWh",         inline=False)
    embed.add_field(name="!alerts",       value="Active alerts",                        inline=False)
    embed.add_field(name="@OfficePulse",  value="Ask anything in plain English",        inline=False)
    await ctx.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Handle @mention free-text
    if bot.user in message.mentions:
        text = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if text:
            async with message.channel.typing():
                reply = await ask(text)
            await message.channel.send(reply)
            return
    await bot.process_commands(message)


# ── Proactive alert announcer ──────────────────────────────────────────────

@tasks.loop(seconds=20)
async def poll_alerts():
    global _last_alert_id
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if channel is None:
        return

    data = await _backend_get(f"/api/alerts?active=true")
    if not data:
        return

    import time
    now = time.monotonic()
    for alert in data:
        if alert["id"] <= _last_alert_id:
            continue
        _last_alert_id = max(_last_alert_id, alert["id"])
        rate_key = (alert["type"], alert["room"])
        if now - _announce_rate.get(rate_key, 0) < RATE_LIMIT_S:
            continue
        _announce_rate[rate_key] = now
        msg = await ask(
            f"Generate a playful Discord ping for this alert: {alert['message']}",
            f"proactive:{alert['id']}",
        )
        await channel.send(f"⚠️ {msg}")


@bot.event
async def on_ready():
    print(f"OfficePulse bot ready as {bot.user}")
    poll_alerts.start()


if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
