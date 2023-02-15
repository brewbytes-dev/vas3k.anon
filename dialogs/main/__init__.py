from aiogram.types import Message, ContentType
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.when import when_not

import extensions.widgets as w
from src.emojis import Emojis
from . import get, do
from .states import Main


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)


dialog = Dialog(
    Window(
        w.Format("Привет! "
                 "Я vas3k bot для отправки анонимных сообщений в чатик Вастрик.Секс!\n"
                 "Пришли мне вопрос или фото (я его спрячу под спойлер) и я анонимно отправлю в чатик",
                 err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        state=Main.menu,
        getter=get.getter,
    ),
    Window(
        w.Format("Все готово! Отправляем в чатик?", err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        w.Button("Отправляем!", on_click=do.postcard_send, emoji=Emojis.mail),
        w.MainMenu(),
        state=Main.click_send,
        getter=get.getter,
    ),
    Window(
        w.Format("Ушло!", when=when_not("dialog_error")),
        w.Format("{dialog_error}", when="dialog_error"),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        w.MainMenu(),
        state=Main.sent,
        getter=get.getter,
    ),
)
