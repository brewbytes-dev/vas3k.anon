import asyncio
import logging
from json import JSONEncoder

import sentry_sdk
from aiogram import exceptions, types
from aiogram.dispatcher import filters
from aiogram_dialog import StartMode, DialogManager
from aiogram_dialog.exceptions import (InvalidStackIdError, UnknownIntent, UnknownState,
                                       InvalidIntentIdError, OutdatedIntent,
                                       DialogStackOverflow)
from aiogram_dialog.utils import remove_kbd

from app import dialogs, bot_loader, config
from app.dialogs.main.states import Main
from app.loader import dp, registry, DEFAULT_USER_COMMANDS
from app.utils import clean_user_fsm

if config.SENTRY_DSN:
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

    await setup_commands()
    await register_errors_handler()

    PRIVATE_FILTER = filters.ChatTypeFilter(types.ChatType.PRIVATE)
    dp.register_message_handler(dialogs.main.start, PRIVATE_FILTER,
                                commands=['start', 'help', 'menu', 'access'], state='*')

    await register_registry()

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
