import asyncio
import logging
from json import JSONEncoder

import sentry_sdk
from aiogram import types

from app import dialogs, config
from app.bot_loader import bot
from app.dialogs.main.states import Main
from app.handlers import errors
from app.loader import dp, DEFAULT_USER_COMMANDS
from aiogram_dialog import DialogRegistry

if config.SENTRY_DSN:
    sentry_sdk.init(config.SENTRY_DSN, traces_sample_rate=0.5)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(name)s - %(message)s",
)


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder().default
JSONEncoder.default = _default


async def main():
    logger.info("Starting bot")

    await setup_commands()

    dp.include_router(dialogs.main.router)
    dp.include_router(errors.router)
    await register_registry()

    try:
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        await bot.session.close()


async def setup_commands():
    await bot.set_my_commands(DEFAULT_USER_COMMANDS, scope=types.BotCommandScopeAllPrivateChats())


async def register_registry():
    registry = DialogRegistry(dp)
    registry.register(dialogs.main.dialog)


if __name__ == '__main__':
    while True:
        try:
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopped!")
            exit(0)
