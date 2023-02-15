import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Select

from app.bot_loader import bot
from app.dialogs.main.states import Main
from app.dialogs.main.parsers import PostCardData
from app.dialogs.main.get import content_author_selector
from app.config import CHAT_ID
from app.extensions.widgets import Button

logger = logging.getLogger(__name__)


async def on_start_postcard(start_data, dialog_manager: DialogManager):
    widget = dialog_manager.dialog().find('r_ct')
    await widget.set_checked(dialog_manager.event, "0", dialog_manager)


async def change_author(c: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id: str):
    data: PostCardData = PostCardData.register(dialog_manager)
    if int(item_id) == 0:
        data.content_author = None
    else:
        data.content_author = content_author_selector[int(item_id)][0]


async def postcard_send(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    text = "\n".join(data.text) or None

    if len(data.photos):
        if data.content_author:
            text = text or "" + '\n' + data.content_author
        await bot.send_photo(CHAT_ID, data.photos[0], text, has_spoiler=True)
    else:
        if text is None:
            await c.message.answer("Что-то пошло не так, "
                                   "попробуйте заново или напишите разработчику "
                                   "@mindsweeper")
            return await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)

        await bot.send_message(CHAT_ID, f"{text}")

    await dialog_manager.start(Main.sent, mode=StartMode.RESET_STACK)
