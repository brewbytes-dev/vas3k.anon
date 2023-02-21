# -*- coding: utf-8 -*-
from urllib.parse import urlparse
from aiogram import Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from aiogram.types import BotCommand

from aiogram_dialog import DialogRegistry

from bot_loader import bot
from app import config

# import redis
# r = redis.from_url(config.REDIS_URL)
# r.flushdb()


DEFAULT_USER_COMMANDS = [
        BotCommand(command="menu", description="Главное меню"),
    ]

url = urlparse(config.REDIS_URL)
storage = RedisStorage2(port=url.port, password=url.password, host=url.hostname,
                        data_ttl=1000000, state_ttl=1000000, pool_size=256)
dp = Dispatcher(bot, storage=storage)
registry = DialogRegistry(dp)

# import redis
# r = redis.from_url(config.REDIS_URL)
# r.flushdb()
