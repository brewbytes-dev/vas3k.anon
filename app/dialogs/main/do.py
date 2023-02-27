import logging

from aiogram.types import CallbackQuery, ContentType
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Select

from app.bot_loader import bot
from app.dialogs.main.states import Main
from app.dialogs.main.parsers import PostCardData
from app.dialogs.main.get import content_author_selector
from app.config import CHAT_ID
from app.extensions.widgets import Button
from app.utils import ALL_MEDIA, Forwarder

logger = logging.getLogger(__name__)


async def on_start_postcard(start_data, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    start_data = dialog_manager.start_data
    data.update((start_data, ))

    widget = dialog_manager.find('mine_r_ct')
    await widget.set_checked("0")


async def change_author(c: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id: str):
    data: PostCardData = PostCardData.register(dialog_manager)
    if int(item_id) == 0:
        data.content_author = None
    else:
        data.content_author = content_author_selector[int(item_id)][0]


async def postcard_send(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    text = "\n".join(data.text) or None

    if data.content_type == ContentType.POLL:
        sent = await bot.copy_message(CHAT_ID, c.message.chat.id, data.message_id)
    elif data.content_type in ALL_MEDIA:
        if data.content_author:
            text = (text or "" + '\n' + data.content_author) or None

        fwder: Forwarder = ALL_MEDIA.get(data.content_type)
        kwargs = {"caption": text}
        if fwder.spoilering:
            kwargs.update({"has_spoiler": True})

        sent = await fwder.sender(CHAT_ID, data.medias[0], **kwargs)
    elif text is None:
        sent = await c.message.answer("Что-то пошло не так, "
                                      "попробуйте заново или напишите разработчику "
                                      "@mindsweeper")
    else:
        sent = await bot.send_message(CHAT_ID, text)

    await dialog_manager.start(Main.sent,
                               mode=StartMode.RESET_STACK,
                               data={"sent_url": sent.get_url()})
