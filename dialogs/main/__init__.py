from aiogram.types import Message, ContentType
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import MessageInput

import extensions.widgets as w
from src.emojis import Emojis
from . import get, do
from .states import Main


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)


dialog = Dialog(
    Window(
        w.Format("Привет! "
                 "Я vas3k bot для отправки анонимных валентинок в чатик Вастрик Секс!\n"
                 "Пришли мне юзернейм кому хочешь отправить поздравление (или просто напиши имя текстом)!"),
        MessageInput(get.user_data, content_types=ContentType.ANY),
        state=Main.menu,
        getter=get.getter,
    ),
    Window(
        w.Format("Отправьте мне открытку, затем мы все проверим и отправим ее {user}",
                 err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        w.MainMenu(),
        getter=get.getter,
        state=Main.get_postcard,
    ),
    Window(
        w.Format("Все готово! Отправляем в чатик тегая получателя?", err_prefix=True),
        w.Button("Отправляем!", on_click=do.postcard_send, emoji=Emojis.mail),
        w.MainMenu(),
        state=Main.click_send,
        getter=get.getter,
    ),
    Window(
        w.Format("Ушло!", err_prefix=True),
        MessageInput(get.user_data, content_types=ContentType.ANY),
        w.MainMenu(),
        state=Main.sent,
        getter=get.getter,
    ),
)
