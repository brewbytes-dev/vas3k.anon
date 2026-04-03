import asyncio
import logging
from json import JSONEncoder
from typing import Any

import sentry_sdk
from aiogram import types

from app import dialogs, config
from app.bot_loader import bot
from app.dialogs.main.states import Main
from app.handlers import errors
from app.loader import dp, DEFAULT_USER_COMMANDS
from aiogram_dialog import DialogRegistry


TRANSIENT_POLLING_ERROR_PREFIXES = (
    "Failed to fetch updates - TelegramNetworkError",
    "Failed to fetch updates - TelegramServerError",
    "Failed to fetch updates - TelegramRetryAfter",
)


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    logentry = event.get("logentry") or {}
    message = "\n".join(
        part
        for part in (
            event.get("message") or "",
            logentry.get("formatted") or logentry.get("message") or "",
        )
        if part
    )
    message_l = message.lower()
    if any(message.startswith(prefix) for prefix in TRANSIENT_POLLING_ERROR_PREFIXES):
        return None
    transient_polling_markers = (
        "failed to fetch updates - telegramnetworkerror",
        "failed to fetch updates - telegramservererror",
        "failed to fetch updates - telegramretryafter",
        "cause exception while getting updates.",
        "bad gateway",
        "request timeout error",
    )
    if any(marker in message_l for marker in transient_polling_markers):
        return None
    return event


if config.SENTRY_DSN:
    sentry_sdk.init(config.SENTRY_DSN, traces_sample_rate=0.5, before_send=_before_send)

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
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
