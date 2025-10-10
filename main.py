#!/usr/bin/env python3

import sys
import json
import datetime
import socket

import discord
import asyncio
import asyncpg
import aiohttp
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="o7", intents=intents)

token = None

db_user: str = "ss14"
db_password: str = ""
db_database: str = "ss14"
db_host: str = "localhost"
db_port: int = 5432
db = None
jobs = None

command_run_error = "Произошла ошибка при выполнении команды."

async def main(args):
    global token, db_user, db_password, db_database, db_host, db_port, db, jobs

    try:
        with open("bot.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print("No config file found!")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Invalid config file")
        sys.exit(1)

    # set var's
    token = data.get("token")
    db_user = data.get("db_user", db_user)
    db_password = data.get("db_password", db_password)
    db_host = data.get("db_host", db_host)
    db_port = data.get("db_port", db_port)
    db_database = data.get("db_database", db_database)

    if not token:
        print("No bot token found")
        sys.exit(1)
    if not db_password:
        print("No database password found")
        sys.exit(1)

    db = await asyncpg.connect(
        user=db_user, password=db_password,
        database=db_database, host=db_host, port=db_port
    )

    print("Connected to db!")

    jobs = await load_jobs("https://raw.githubusercontent.com/BohdanNovikov0207/Orehum-Project/refs/heads/master/Resources/Locale/ru-RU/job/job-names.ftl")
    jobs["Overall"] = "Общее"
    jobs["Admin"] = "Админ"
    print("Jobs localization loaded")

    try:
        await bot.start(token)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nShutting down bot...")
    finally:
        print("Disconnecting, please wait...")
        await bot.close()
        await db.close()



@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command(name="find")
async def find(ctx, *, text: str):
	"""
	Найти игрока по сикею
	"""
	pattern = f"%{text}%"
	try:
		rows = await db.fetch(
            "SELECT * FROM player WHERE last_seen_user_name ILIKE $1 LIMIT 10",
            pattern
        )
		if not rows:
			await ctx.send("Игрок не найден")
			return
		msg = f"Найдено {len(rows)}:\n```\n" # предпологаем, что юзер полный мудак.
		for row in rows:
			msg += f"{row['last_seen_user_name'].replace("@", "")}\n"
		msg += "```"
		await ctx.send(msg)
	except Exception as e:
		print(e)
		await ctx.send(command_run_error)
        
@bot.command(name="playtime")
async def playtime(ctx, *, text: str):
    """
    Посмотреть наигранное время игрока
    """
    try:
        rows = await db.fetch(
            "SELECT pt.* FROM player p JOIN play_time pt ON pt.player_id = p.user_id WHERE p.last_seen_user_name = $1 ORDER BY pt.time_spent DESC LIMIT 10",
            text
        )
        if not rows:
            await ctx.send("Игрок не найден")
            return
        embed = discord.Embed(
            title="",
            color=discord.Color.blue()
        )
        msg = ""
        for row in rows:
            msg += f"**{get_job_name(row['tracker'])}** {format_timedelta(row['time_spent'])}\n"
        
        embed.add_field(name=text, value=msg)

        await ctx.send(embed=embed)
    except Exception as e:
        print(e)
        await ctx.send(command_run_error)

@bot.command(name="status")
async def status(ctx):
    """
    Посмотреть статус основного сервера
    """
    try:
        message = await ctx.send("Выполнение...")
        data = await get_status()
        embed = discord.Embed(
            title="",
            color=discord.Color.green()
        )

        msg = f"**Игроков**: {data.get("players", "0")}/{+data.get("soft_max_players", "0")}\n**Карта**: {data.get("map", "Неизвестно")}\n**Режим**: {data.get("preset", "Неизвестно")}\n**Раунд**: {data.get("round_id", "0")}"

        embed.add_field(name=data.get("name", "Неизвестно"), value=msg)

        await message.edit(embed=embed, content="")
    except Exception as e:
        print(e)
        await ctx.send(command_run_error)

@bot.command(name="characters")
async def characters(ctx, *, text: str):
    """
    Посмотреть 25 персонажей игрока
    """
    try:
        rows = await db.fetch("SELECT pr.* FROM profile pr JOIN preference pref ON pr.preference_id = pref.preference_id JOIN player pl ON pref.user_id = pl.user_id WHERE pl.last_seen_user_name = $1 ORDER BY pr.char_name DESC;", text)
        if not rows:
            await ctx.send("Игрок не найден!")
            return
        rows2 = await db.fetch("SELECT pref.selected_character_slot, pref.* FROM preference pref JOIN player pl ON pref.user_id = pl.user_id WHERE pl.last_seen_user_name = $1;", text)
        if not rows2:
            await ctx.send("Выбранный персонаж игрока не найден...")
            return
        selected = rows2[0]['selected_character_slot']
        embeds = []
        for row in rows:
            embed = discord.Embed(
                title="",
                color=discord.Color.from_str(row['skin_color'][:7])
            )
            msg = f"Раса: {row['species']}\nВозраст: {row['age']}\nПол: {row['sex']}\nЖизненный путь: {row['lifepath']}\nНациональность: {row['nationality']}\n\n{row['flavor_text']}"
            if selected == row['slot']:
                msg = "\n**Выбранный персонаж**\n\n" + msg
            embed.add_field(name=row['char_name'], value=msg)
            embeds.insert(0, embed)
        await ctx.send(embeds=embeds)
    except Exception as e:
        print(e)
        await ctx.send(command_run_error)

def format_timedelta(td: datetime.timedelta) -> str:
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

def get_job_name(job_id: str) -> str:
    return jobs.get(job_id, job_id)

async def load_jobs(url: str) -> dict[str, str]:
    job_names = {}

    connector = aiohttp.TCPConnector(family=socket.AF_INET) # IPv4 only
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Error while loading jobs ftl: {resp.status}")
            text = await resp.text()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            job_names[key.strip()] = val.strip().strip('"')

    return job_names

async def get_status():
    url = "http://46.149.69.119:10046/status"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))