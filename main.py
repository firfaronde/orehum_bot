#!/usr/bin/env python3

import sys
import json
import os
from datetime import datetime, timezone, timedelta
# import locale

import discord
from discord import app_commands
import asyncio
import asyncpg
from discord.ext import commands

import localization
import utils
import banlistener as banls

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="o!", intents=intents)

token = None

bans_channel_id = None

db_user: str = "ss14"
db_password: str = ""
db_database: str = "ss14"
db_host: str = "localhost"
db_port: int = 5432
db = None

role_trackers = None

command_run_error = "Произошла ошибка при выполнении команды."

async def timed_task():
    while True:
        try:
            if bot is not None:
                data = await utils.get_status()
                # msg = f"👱{data.get('players', 0)}🗺️{data.get('map', 'Лобби')}"
                # round_duration = utils.get_duration(data.get("round_start_time"))
                # if round_duration:
                #     msg += f"🕛{round_duration}"
                await bot.change_presence(activity=discord.Game(name=f"{data.get('players', 0)} игроков на {data.get('map', 'Лобби')}"))
                await asyncio.sleep(10)
        except Exception as e:
            # print(e)
            await asyncio.sleep(10)

async def main(args):
    print(f"Pid is {os.getpid()}")
    # locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
    global token, db_user, db_password, db_database, db_host, db_port, db, jobs, species, sexes, lifepaths, role_trackers

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

    bans_channel_id = data.get("bans_channel_id")

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
    
    await localization.load()

    role_trackers = await fetch_trackers()
    print(role_trackers)

    asyncio.create_task(timed_task())

    print("Start complete")
    try:
        await bot.start(token)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nShutting down bot...")
    finally:
        print("Disconnecting, please wait...")
        await bot.close()
        await db.close()

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command(name="find")
async def find(ctx, *, text: str = commands.parameter(description="Сикей игрока")):
	"""
	Найти игрока по сикею
	"""
	pattern = f"%{text}%"
	try:
		rows = await fetch(
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
		await error(ctx, e)
        
@bot.command(name="playtime")
async def playtime(ctx, *, text: str = commands.parameter(description="Сикей игрока")):
    """
    Посмотреть наигранное время игрока
    """
    try:
        rows = await fetch(
            "SELECT pt.* FROM player p JOIN play_time pt ON pt.player_id = p.user_id WHERE p.last_seen_user_name like $1 ORDER BY pt.time_spent DESC LIMIT 10",
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
            msg += f"**{localization.get_job_name(row['tracker'])}** {utils.format_timedelta(row['time_spent'])}\n"
        
        embed.add_field(name=text, value=msg)

        await ctx.send(embed=embed)
    except Exception as e:
        await error(ctx, e)

@bot.command(name="status")
async def status(ctx):
    """
    Посмотреть статус основного сервера
    """
    try:
        message = await ctx.send("Выполнение...")
        data = await utils.get_status()
        embed = discord.Embed(color=discord.Color.green())

        msg = (
            f"**Игроков**: {data.get('players', '0')}/{data.get('soft_max_players', '0')}\n"
            f"**Карта**: {data.get('map', 'Неизвестно')}\n"
            f"**Режим**: {data.get('preset', 'Неизвестно')}\n"
            f"**Раунд**: {data.get('round_id', '0')}"
        )

        round_duration = utils.get_duration(data.get("round_start_time"))
        if round_duration:
            msg += f"\n**Раунд идет**: {round_duration}"

        embed.add_field(name=data.get("name", "Неизвестно"), value=msg)
        await message.edit(embed=embed, content="")

    except Exception as e:
        await error(ctx, e)

@bot.command(name="characters")
async def characters(ctx, *, text: str = commands.parameter(description="Сикей игрока")):
    """
    Посмотреть 25 персонажей игрока
    """
    try:
        rows = await fetch("SELECT pr.* FROM profile pr JOIN preference pref ON pr.preference_id = pref.preference_id JOIN player pl ON pref.user_id = pl.user_id WHERE pl.last_seen_user_name like $1 ORDER BY pr.char_name DESC;", text)
        if not rows:
            await ctx.send("Игрок не найден!")
            return
        rows2 = await fetch("SELECT pref.selected_character_slot, pref.* FROM preference pref JOIN player pl ON pref.user_id = pl.user_id WHERE pl.last_seen_user_name like $1;", text)
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
            msg = f"Раса: {localization.get_specie_name(row['species'])}\nВозраст: {row['age']}\nПол: {localization.get_sex_name(row['sex'])}\nЖизненный путь: {localization.get_lifepath_name(row['lifepath'])}\nНациональность: {row['nationality']}\n\n{row['flavor_text']}"
            if selected == row['slot']:
                msg = "\n**Выбранный персонаж**\n\n" + msg
            embed.add_field(name=row['char_name'], value=msg)
            embeds.insert(0, embed)
        await ctx.send(embeds=embeds[:10])
    except Exception as e:
        await error(ctx, e)

async def is_admin(ctx) -> bool:
    member = ctx.author
    return any(role.id == 1399083269416419398 for role in member.roles)

async def is_owner(ctx) -> bool:
    return ctx.author.id == 1416876595301580822

@bot.command(name="player", hidden=True)
@commands.check(is_admin)
async def player(ctx, *, ckey: str = commands.parameter(description="Сикей игрока")):
    try:
        message = await ctx.message.reply("Выполнение...")
        rows = await fetch("SELECT last_seen_user_name FROM player WHERE last_seen_user_name like $1", ckey)
        c = f"**{ckey.replace('@', '')}**\n"
        if rows:
            c += "Есть в БД орехума\n"
        data = await utils.get(f"https://auth.spacestation14.com/api/query/name?name={ckey}")
        if data is not None:
            c += f"Дата регистрации: {data.get('createdTime', "Аккаунта не существует")}"
        await message.edit(content=c)
    except Exception as e:
        await error(ctx, e)

@bot.command(name="sql", hidden=True)
@commands.check(is_owner)
async def sql(ctx, *, query: str):
    try:
        if query.strip().lower().startswith("select"):
            rows = await db.fetch(query)
            count = len(rows)
            data = {}
            for i, row in enumerate(rows, start=1):
                clean_row = {k: str(v) for k, v in dict(row).items()}
                data[f"row{i}"] = clean_row

            text = f"Rows returned: {count}\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}```"
            if len(text) > 1900:
                text = text[:1900] + "\n```... (>1900)```"
            await ctx.send(text)
        else:
            result = await db.execute(query)
            affected = result.split()[-1] if result else "0"
            await ctx.send(f"Rows updated: {affected}")
    except Exception as e:
        await ctx.send(f"Ahh: `{e}`")

async def error(ctx, error: Exception):
    print("Error: " + str(error))
    try:
        await ctx.message.reply(command_run_error)
    except Exception:
        await ctx.response.send_message(command_run_error)

@bot.event
async def on_ready():
    # guild = discord.Object(1399033645880180756)
    # await bot.tree.sync(guild=guild)
    print(f"We have logged in as {bot.user}")
    if bans_channel_id:
        asyncio.create_task(banls.load(db, bot, bans_channel_id))

async def fetch(query: str, *args):
    global db
    try:
        return await db.fetch(query, *args)
    except (asyncpg.exceptions.ConnectionDoesNotExistError, asyncpg.exceptions.InterfaceError):
        print("Reconnecting to db...")
        await db.close()
        db = await asyncpg.connect(
            user=db_user, password=db_password,
            database=db_database, host=db_host, port=db_port
        )
        return await db.fetch(query, *args)

async def fetch_trackers() -> list[str]:
    try:
        trackers = []
        rows = await fetch("SELECT DISTINCT tracker FROM play_time")
        for row in rows:
            trackers.append(row['tracker'])
        return trackers
    except Exception:
        return None

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
