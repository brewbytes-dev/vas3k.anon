import typing

from aiogram.types import Message, ContentType
from aiogram_dialog import Dialog, DialogManager
from src.utils import get_id_from_message

from dialogs.main.states import Main
from dialogs.main.parsers import PostCardData
from src.config import SEX_CHAT_ID


async def getter(dialog_manager: DialogManager, **kwargs):
    data: PostCardData = PostCardData.register(dialog_manager)
    return {
        "user": data.username,
        "dialog_error": data.dialog_error,
    }


async def user_data(m: Message, d: Dialog, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    if not m.text:
        return

    if not m.text.startswith("@"):
        return
    #
    if m.text.startswith("https://t.me"):
        chat_id = m.text.split('/')[-2]
        if "-100" + str(chat_id) != str(SEX_CHAT_ID):
            data.dialog_error = 'Эта ссылка не из чата Вастрик.Секс'
            return
        data.reply_message_id = m.text.split('/')[-1]
    elif m.text.startswith("@"):
        data.username = m.text.strip()
    else:
        data.dialog_error = 'Не могу разобрать сообщение'
        return

    data.dialog_error = ''
    await dialog_manager.switch_to(Main.get_postcard)


async def postcard_data(m: Message, d: Dialog, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    text, photos, messages = data.text, data.photos, data.messages

    if m.content_type == ContentType.TEXT:
        text.append(m.text)
        await m.reply(m.text)
    elif m.content_type == ContentType.PHOTO:
        text.append(m.caption)
        photos.append(get_id_from_message(m))
    else:
        data.dialog_error = "Нормальная открытка содержит только текст и фото"
        return

    data.dialog_error = ''
    data.message_id = m.message_id
    data.text = text
    data.photos = photos

    # await m.reply(f"{text=}, {photos=}, {data.reply_message_id=}",)
    await dialog_manager.switch_to(Main.click_send)
