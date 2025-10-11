#!/usr/bin/env python3

import sys
import json
import os

import discord
from discord import app_commands
import asyncio
import asyncpg
from discord.ext import commands

import localization
import utils

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="o!", intents=intents)

token = None

db_user: str = "ss14"
db_password: str = ""
db_database: str = "ss14"
db_host: str = "localhost"
db_port: int = 5432
db = None

command_run_error = "Произошла ошибка при выполнении команды."

async def timed_task():
    while True:
        try:
            if bot is not None:
                data = await utils.get_status()
                await bot.change_presence(activity=discord.Game(name=f"{data.get('players', 0)} игроков на {data.get('map', 'Лобби')}"))
                await asyncio.sleep(10)
        except Exception as e:
            print(e)
            await asyncio.sleep(10)

async def main(args):
    print(f"Pid is {os.getpid()}")
    global token, db_user, db_password, db_database, db_host, db_port, db, jobs, species, sexes, lifepaths

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
    
    await localization.load()

    asyncio.create_task(timed_task())
    
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
        embed = discord.Embed(
            title="",
            color=discord.Color.green()
        )

        msg = f"**Игроков**: {data.get("players", "0")}/{+data.get("soft_max_players", "0")}\n**Карта**: {data.get("map", "Неизвестно")}\n**Режим**: {data.get("preset", "Неизвестно")}\n**Раунд**: {data.get("round_id", "0")}"

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
        rows = await fetch("SELECT pr.* FROM profile pr JOIN preference pref ON pr.preference_id = pref.preference_id JOIN player pl ON pref.user_id = pl.user_id WHERE pl.last_seen_user_name = $1 ORDER BY pr.char_name DESC;", text)
        if not rows:
            await ctx.send("Игрок не найден!")
            return
        rows2 = await fetch("SELECT pref.selected_character_slot, pref.* FROM preference pref JOIN player pl ON pref.user_id = pl.user_id WHERE pl.last_seen_user_name = $1;", text)
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

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))