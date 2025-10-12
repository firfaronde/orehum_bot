import json

import asyncio
import asyncpg

async def load(db: asyncpg.connection.Connection):
    async def handler(connection, pid, channel, payload):
        data = json.loads(payload)
        print("Received:", data)

    await db.add_listener('ban_notification', handler)

    while True:
        await asyncio.sleep(10)