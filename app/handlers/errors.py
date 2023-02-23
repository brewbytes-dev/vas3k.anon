import logging
from typing import Any

from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.filters import ExceptionTypeFilter
from aiogram_dialog import DialogManager, StartMode

from aiogram_dialog.api.exceptions import (InvalidStackIdError, UnknownIntent, UnknownState,
                                           OutdatedIntent,
                                           DialogStackOverflow)

from app.bot_loader import bot
from app.dialogs.main import Main
from app.utils import clean_user_fsm

router = Router(name='errors')

logger = logging.getLogger(__name__)


BUTTONS_IDS = {'start_bot': Main.menu,
               }


@router.errors(ExceptionTypeFilter(OutdatedIntent, UnknownIntent, UnknownState, InvalidStackIdError))
async def dialog_error_handler(exception: ErrorEvent, dialog_manager: DialogManager) -> Any:
    await handle_and_start_new(exception, dialog_manager)


@router.errors(ExceptionTypeFilter(InvalidStackIdError, DialogStackOverflow))
async def dialog_error_skip(exception: ErrorEvent) -> Any:
    return True


def guess_state(callback_data):
    for btn_id, btn_state in BUTTONS_IDS.items():
        if btn_id in callback_data:
            return btn_state


async def handle_and_start_new(error: ErrorEvent, dialog_manager: DialogManager, *args, **kwargs):
    if error.update.callback_query:
        user = error.update.callback_query.from_user
        chat = error.update.callback_query.message.chat
        state = guess_state(error.update.callback_query.data)
        message = error.update.callback_query.message
    else:
        user = error.update.message.from_user
        chat = error.update.message.chat
        state = None
        message = error.update.message

    if state is None:
        logger.warning("Exception suppressed [User: %s, %s]:\n%s", user.id, user.username, error.exception)
        err_message = 'Что-то пошло не так, попробуйте еще раз'
        state = Main.menu
    else:
        err_message = ''

    if chat.type == 'private':
        await clean_user_fsm(user.id)
        await dialog_manager.start(state, mode=StartMode.RESET_STACK, data={'user_id'     : user.id,
                                                                            'dialog_error': err_message})
    else:
        await message.delete_reply_markup()
        await bot.send_message(chat_id=chat.id, text=err_message)
    return True
