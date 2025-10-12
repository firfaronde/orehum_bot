import aiohttp
from datetime import datetime, timezone, timedelta

def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days} д")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} м")

    return " ".join(parts) if parts else "0 м"

async def get_status():
    url = "http://47.89.131.63:17110/status"
    timeout = aiohttp.ClientTimeout(total=2)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data

def get_duration(round_start_time: str) -> str | None:
    if not round_start_time:
        return None

    try:
        start_time = datetime.fromisoformat(round_start_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - start_time

        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        return f"{hours}ч {minutes}м"
    except Exception:
        return None