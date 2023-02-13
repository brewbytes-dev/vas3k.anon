# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from aiogram import Dispatcher
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.types import BotCommand

from aiogram_dialog import DialogRegistry

from bot_loader import bot
from src import config
from extensions.filters import AdminRights, IsGroupJoin, RemoveAdminRights, BotForbidden, ForwardedFromChannelFilter
from apscheduler.schedulers.asyncio import AsyncIOScheduler

DEFAULT_USER_COMMANDS = [
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="pass", description="Временный пропуск"),
        BotCommand(command="call", description="Заявка диспетчеру"),
        # BotCommand(command="doors", description="Мой пропуск"),
    ]

DEFAULT_GROUP_COMMANDS = [
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="admin", description="Позвать администраторов")
]

scheduler = AsyncIOScheduler()

url = urlparse(config.REDIS_URL)
storage = RedisStorage2(port=url.port, password=url.password, host=url.hostname,
                        data_ttl=1000000, state_ttl=1000000, pool_size=256)
dp = Dispatcher(bot, storage=storage)
dp.filters_factory.bind(IsGroupJoin)
dp.filters_factory.bind(AdminRights, event_handlers=[dp.my_chat_member_handlers])
dp.filters_factory.bind(RemoveAdminRights, event_handlers=[dp.my_chat_member_handlers])
dp.filters_factory.bind(BotForbidden, event_handlers=[dp.my_chat_member_handlers])
dp.filters_factory.bind(ForwardedFromChannelFilter, event_handlers=[dp.message_handlers])
registry = DialogRegistry(dp)
#
#

# def reset_storage():
#     import redis
#     rr = redis.Redis().from_url(config.REDIS_URL)
#     rr.flushdb()
#
# reset_storage()
#

