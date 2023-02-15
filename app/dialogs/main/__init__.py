import operator

from aiogram.types import Message, ContentType
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Radio
from aiogram_dialog.widgets.when import when_not

import app.extensions.widgets as w
from app.extensions.emojis import Emojis
from . import get, do
from .states import Main

MineOrNot = (
    w.Format("\nЭто фото сделано вами или из сети?",
             when="photo_type"
             ),
    Radio(
        w.Format("🔘 {item[0]}"),  # E.g `🔘 Apple`
        w.Format("⚪️ {item[0]}"),
        id="r_ct",
        item_id_getter=operator.itemgetter(1),
        items="content_author_selector",
        when="photo_type",
        on_click=do.change_author,
    ),
)


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)


dialog = Dialog(
    Window(
        w.Format("Привет! "
                 "Я {bot_name} [{bot_version}] для отправки анонимных сообщений в чатик {chat_name}!\n"
                 "Пришли мне вопрос или фото (я его спрячу под спойлер) и я анонимно отправлю в чатик",
                 err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        state=Main.menu,
        getter=get.getter,
    ),
    Window(
        w.Format("Все готово! Для отправки в чат нажми на кнопку «Отправляем!». Если ты ошибся, просто отправь новое сообщение или нажми кнопку «В главное меню» ", err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        *MineOrNot,
        w.Button("Отправляем!", on_click=do.postcard_send, emoji=Emojis.mail),
        w.MainMenu(),
        state=Main.click_send,
        getter=get.getter,
    ),
    Window(
        w.Format("Ушло!", when=when_not("dialog_error")),
        w.Format("{dialog_error}", when="dialog_error"),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        *MineOrNot,
        w.MainMenu(),
        state=Main.sent,
        getter=get.getter,
    ),
    on_start=do.on_start_postcard,
)
