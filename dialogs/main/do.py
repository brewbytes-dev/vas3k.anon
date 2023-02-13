import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from bot_loader import bot
from dialogs.main.states import Main
from dialogs.main.parsers import PostCardData
from src.config import SEX_CHAT_ID
from extensions.widgets import Button

logger = logging.getLogger(__name__)


async def postcard_send(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    text = "\n".join(data.text)

    if data.reply_message_id:
        reply_to = int(data.reply_message_id)
    else:
        reply_to = None

    if len(data.photos):
        await bot.send_photo(SEX_CHAT_ID, data.photos[0],
                             f"💌 Привет {data.username}! Тебе прислали новую открытку!\n\n{text}",
                             reply_to_message_id=reply_to)
    else:
        if not len(text):
            await c.message.answer("Что-то пошло не так, попробуйте заново или напишите разработчику "
                                   "@mindsweeper")
            return await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)

        await bot.send_message(SEX_CHAT_ID, f"💌 Привет {data.username}! Тебе прислали новую открытку! Вот текст:\n\n{text}",
                               reply_to_message_id=reply_to)

    await dialog_manager.start(Main.sent, mode=StartMode.RESET_STACK)
