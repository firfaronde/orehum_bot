from quart import Quart, jsonify, abort
from hypercorn.asyncio import serve
from hypercorn.config import Config
import asyncio
import asyncpg

import uuid
import sys
import json
import sys

api = Quart(__name__)

api_port = 80

db_user: str = "ss14"
db_password: str = ""
db_database: str = "ss14"
db_host: str = "localhost"
db_port: int = 5432

db = None

async def main(args):
    global api_port, db_user, db_password, db_port, db_host, db_database, db
    try:
        with open("bot.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print("[Sponsors]No config file found!")
        sys.exit(1)
    except json.JSONDecodeError:
        print("[SponsorsInvalid config file")
        sys.exit(1)
    
    api_port = data.get("api_port", api_port)

    db_user = data.get("db_user", db_user)
    db_password = data.get("db_password", db_password)
    db_host = data.get("db_host", db_host)
    db_port = data.get("db_port", db_port)
    db_database = data.get("db_database", db_database)

    db = await asyncpg.connect(
        user=db_user, password=db_password,
        database=db_database, host=db_host, port=db_port
    )
    
    config = Config()
    config.bind = [f"0.0.0.0:{api_port}"]
    await serve(api, config)

@api.route('/sponsors/<user_id>')
async def get_sponsor(user_id: str):

    try:
        uuid.UUID(user_id)
    except ValueError:
        abort(400)

    try:
        rows = await get_sponsor_tier(user_id)
        if rows:
            row = rows[0]
            data = {k: v for k, v in row.items() if k not in ("id", "sponsor_id")}
            return jsonify(data)
        else:
            abort(404)
    except ValueError:
        abort(400)

async def get_sponsor_tier(user_id: str):
    return await fetch("SELECT st.* FROM sponsors s JOIN sponsors_tiers st ON st.sponsor_id = s.id WHERE s.player_id = $1 LIMIT 1", user_id)

async def fetch(query: str, *args):
    global db
    try:
        return await db.fetch(query, *args)
    except (asyncpg.exceptions.ConnectionDoesNotExistError, asyncpg.exceptions.InterfaceError):
        print("[Sponsors]Reconnecting to db...")
        if db is not None:
            await db.close()
        db = await asyncpg.connect(
            user=db_user, password=db_password,
            database=db_database, host=db_host, port=db_port
        )
        return await db.fetch(query, *args)

asyncio.run(main(sys.argv[1:]))