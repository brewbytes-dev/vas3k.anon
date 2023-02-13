import asyncio
import logging
from json import JSONEncoder

import asyncpg
import sentry_sdk
from aiogram import exceptions, types
from aiogram_dialog import StartMode, DialogManager
from aiogram_dialog.exceptions import (InvalidStackIdError, UnknownIntent, UnknownState,
                                       InvalidIntentIdError, OutdatedIntent,
                                       DialogStackOverflow)
# TODO: add this to library # from aiogram_dialog.exceptions import UnknownStateGroup
from aiogram_dialog.utils import remove_kbd

import bot_loader
import dialogs
from dialogs.main import Main
from loader import dp, registry, DEFAULT_USER_COMMANDS, DEFAULT_GROUP_COMMANDS
from middlewares.db import DbMiddleware, setup_db_config
from src import config
from src.base import Repo
from src.utils import clean_user_fsm

sentry_sdk.init(config.SENTRY_DSN, traces_sample_rate=0.5)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(name)s - %(message)s",
)

BUTTONS_IDS = {'start_bot': Main.menu,
               }


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder().default
JSONEncoder.default = _default


def guess_state(callback_data):
    for btn_id, btn_state in BUTTONS_IDS.items():
        if btn_id in callback_data:
            return btn_state


async def handle_and_start_new(update: types.Update, exception, dialog_manager: DialogManager, *args, **kwargs):
    if update.callback_query:
        user = update.callback_query.from_user
        chat = update.callback_query.message.chat
        state = guess_state(update.callback_query.data)
        message = update.callback_query.message
    else:
        user = update.message.from_user
        chat = update.message.chat
        state = None
        message = update.message

    if state is None:
        logger.warning("Exception suppressed [User: %s, %s]:\n%s", user.id, user.username, exception)
        err_message = 'Что-то пошло не так, попробуйте еще раз'
        state = Main.menu
    else:
        err_message = ''

    await remove_kbd(update.bot, message)

    if chat.type == 'private':
        await clean_user_fsm(user.id)
        await dialog_manager.start(state, mode=StartMode.RESET_STACK, data={'user_id': user.id,
                                                                            'dialog_error': err_message})

    else:
        await update.bot.send_message(chat_id=chat.id, text=err_message)
    return True


async def skip_error(update: types.Update, exception, *args, **kwargs):
    return True


async def main():
    logger.info("Starting bot")

    async_pool = await asyncpg.create_pool(config.DATABASE_URL)
    async with async_pool.acquire() as conn:
        conn = await setup_db_config(conn)
        _repo = Repo(conn)

    logger.info("DB Middleware setup complete")

    await setup_commands()

    # dp.middleware.setup(AlbumMiddleware(latency=1))
    # dp.register_inline_handler(inline_echo, state='*')

    await register_errors_handler()
    # await register_inline(dp, dbv)
    # await register_group(dp, dbv)
    # await register_pulse(dp, dbv)
    # await register_claims(dp, dbv)
    # await register_private(dp, dbv)
    await register_registry()
    dp.setup_middleware(DbMiddleware(async_pool, dp))

    try:
        # await dp.skip_updates()
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot_loader.bot.session.close()



async def setup_commands():
    await bot_loader.bot.set_my_commands(DEFAULT_USER_COMMANDS, scope=types.BotCommandScope.from_type(
        types.BotCommandScopeType.ALL_PRIVATE_CHATS))

    await bot_loader.bot.set_my_commands(DEFAULT_GROUP_COMMANDS, scope=types.BotCommandScope.from_type(
        types.BotCommandScopeType.ALL_GROUP_CHATS))


async def register_errors_handler():
    dp.register_errors_handler(callback=handle_and_start_new, exception=InvalidIntentIdError)
    dp.register_errors_handler(callback=handle_and_start_new, exception=OutdatedIntent)
    dp.register_errors_handler(callback=handle_and_start_new, exception=UnknownIntent)
    dp.register_errors_handler(callback=handle_and_start_new, exception=UnknownState)
    # TODO: add this to library # dp.register_errors_handler(callback=handle_and_start_new, exception=UnknownStateGroup)
    dp.register_errors_handler(callback=handle_and_start_new, exception=InvalidStackIdError)
    dp.register_errors_handler(callback=skip_error, exception=exceptions.InvalidQueryID)
    dp.register_errors_handler(callback=skip_error, exception=exceptions.MessageNotModified)
    dp.register_errors_handler(callback=skip_error, exception=DialogStackOverflow)


async def register_registry():
    registry.register(dialogs.main.dialog)


if __name__ == '__main__':
    while True:
        try:
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopped!")
            exit(0)
