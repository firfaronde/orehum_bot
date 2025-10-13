import json
from datetime import datetime

import asyncio
import asyncpg
import discord

async def load(db, bot):
    async def handler(connection, pid, channel, payload):
        data = json.loads(payload)

        rows = await db.fetch("SELECT * FROM server_ban WHERE server_ban_id = $1", data.get('ban_id'))
        if rows:
            row = rows[0]
            embed = discord.Embed(
                title="Серверный бан",
                color=discord.Color.red()
            )
            tmp = ""
            # rows2 = await fetch("SELECT * FROM player WHERE last_seen_user_name = $1",)
            if row["banning_admin"] is None:
                tmp = "Сервер"
            else:
                rows2 = await db.fetch("SELECT * FROM player WHERE user_id = $1", row["banning_admin"])
                if rows2:
                    tmp = rows2[0]["last_seen_user_name"]
                else:
                    tmp = "Неизвестно"
            embed.add_field(name="Забанил", value=tmp)
            rows2 = await db.fetch("SELECT * FROM player WHERE user_id = $1", row["player_user_id"])
            if rows2:
                tmp = rows2[0]["last_seen_user_name"]
            else:
                tmp = "Неизвестно"
            embed.add_field(name="Игрока", value=tmp)
            embed.add_field(name="С причиной", value=row["reason"])
            dt = datetime.fromisoformat(row["expiration_time"])
            embed.add_field(name="Дата разбана", value=dt.strftime("%d %B %Y года"))

            channel = bot.get_channel(1399082842406912201)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(1399082842406912201)
                except Exception as e:
                    print(e)
                    return
            await channel.send(embed=embed)

        # print("Received:", data)

    await db.add_listener('ban_notification', handler)