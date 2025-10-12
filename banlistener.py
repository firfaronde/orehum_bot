import json

import asyncio
import asyncpg
import discord

from main import fetch, bot

async def load(db):
    async def handler(connection, pid, channel, payload):
        data = json.loads(payload)

        rows = await fetch("SELECT * FROM server_ban WHERE server_ban_id = $1", data.get('ban_id'))
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
                rows2 = await fetch("SELECT * FROM player WHERE user_id = $1", row["banning_admin"])
                if rows2:
                    tmp = rows2[0]["last_seen_user_name"]
                else:
                    tmp = "Неизвестно"
            embed.add_field(name="Забанил", value=tmp)
            rows2 = await fetch("SELECT * FROM player WHERE user_id = $1", row["player_user_id"])
            if rows2:
                tmp = rows2[0]["last_seen_user_name"]
            else:
                tmp = "Неизвестно"
            embed.add_field(name="Игрока", value=tmp)
            embed.add_field(name="С причиной", value=row["reason"])
            embed.add_field(name="Дата разбана", value=row["expiration_time"])

            await bot.get_channel(1399082842406912201).send(embed=embed)

        print("Received:", data)

    await db.add_listener('ban_notification', handler)