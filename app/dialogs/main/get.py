from aiogram.types import Message, ContentType
from aiogram.utils.markdown import hlink
from aiogram_dialog import Dialog, DialogManager

from app.bot_loader import bot
from app.config import CHAT_NAME, BOT_NAME
from app.dialogs.main.parsers import PostCardData
from app.dialogs.main.states import Main
from app.extensions.emojis import Emojis
from app.utils import get_id_from_message, ALL_MEDIA

content_author_selector = (
    ("<пусто>", 0),
    ('#не_моё', 1),
    ('#моё', 2)
)


async def final_getter(dialog_manager: DialogManager, **kwargs):
    data: PostCardData = PostCardData.register(dialog_manager)

    if data.sent_url:
        sent_link = hlink('Ушло!', data.sent_url)
    else:
        sent_link = 'Ушло!'

    return {
        "dialog_error": data.dialog_error,
        "no_error": not data.dialog_error,
        "sent_link": sent_link
    }


async def getter(dialog_manager: DialogManager, **kwargs):
    data: PostCardData = PostCardData.register(dialog_manager)

    return {
        "content_author_selector": content_author_selector,
        "content_author": data.content_author,
        "m_type": bool(data.medias),
        "bot_name": BOT_NAME,
        "chat_name": CHAT_NAME,
        "bot_version": bot.version,
        "user": data.username,
        "dialog_error": data.dialog_error,
        "no_error": not data.dialog_error,
    }


async def user_data(m: Message, d: Dialog, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    if not m.text:
        data.dialog_error = 'Ошибка! Нет текста.'
        return

    data.username = m.text.strip()
    await dialog_manager.switch_to(Main.get_postcard)


async def postcard_data(m: Message, d: Dialog, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    data.clean()
    text, medias, messages = data.text, data.medias, data.messages

    if m.content_type == ContentType.TEXT:
        text.append(m.text)
    elif m.content_type in ALL_MEDIA:
        if m.caption is not None:
            text.append(m.caption)
        medias.append(get_id_from_message(m))
    elif m.content_type == ContentType.POLL:
        pass
    else:
        data.dialog_error = f"{Emojis.error} Принимаем только текст, медиа или опрос"
        return

    data.dialog_error = ''
    data.message_id = m.message_id
    data.text = text
    data.medias = medias
    data.content_type = m.content_type

    await dialog_manager.switch_to(Main.click_send)
