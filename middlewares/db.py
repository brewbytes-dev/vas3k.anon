import asyncpg
import aiogram

import ujson
from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

from src.base import Repo


class DbMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ['process_update']

    def __init__(self, pool: asyncpg.Pool, dp: aiogram.Dispatcher):
        super().__init__()
        self.pool = pool
        self.dp = dp

    async def pre_process_aiogd_update(self, obj, data, *args):
        await self.pre_process(obj, data, args)

    async def pre_process(self, obj, data, *args):
        db = await self.pool.acquire()
        await setup_db_config(db)

        data["repo"] = Repo(db)
        data["db"] = db

    async def post_process(self, obj, data, *args):
        try:
            del data["repo"]
        except:
            pass

        db = data.get("db")
        if db:
            await db.close()


async def setup_db_config(acquired_pool):
    await acquired_pool.set_type_codec(
        'json',
        encoder=lambda x: x,
        decoder=ujson.loads,
        schema='pg_catalog'
    )

    await acquired_pool.set_type_codec(
        'jsonb',
        encoder=lambda x: x,
        decoder=ujson.loads,
        schema='pg_catalog'
    )

    return acquired_pool
