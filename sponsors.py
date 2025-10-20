from quart import Quart, jsonify, abort
from hypercorn.asyncio import serve
from hypercorn.config import Config

import uuid

import vars

api = Quart(__name__)
from main import fetch

async def load(bot, api_port: int = 80):
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