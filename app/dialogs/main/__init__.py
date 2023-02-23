import operator

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import Message, ContentType
from aiogram.filters import Command
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Radio

import app.extensions.widgets as w
from app.extensions.emojis import Emojis
from . import get, do
from .states import Main

router = Router(name="main")
router.message.filter(F.chat.type.in_({"private"}))

MineOrNot = (
    w.Format("\nЭто фото сделано вами или из сети?",
             when="m_type"
             ),
    Radio(
        w.Format("🔘 {item[0]}"),  # E.g `🔘 Apple`
        w.Format("⚪️ {item[0]}"),
        id="mine_r_ct",
        item_id_getter=operator.itemgetter(1),
        items="content_author_selector",
        when="m_type",
        on_click=do.change_author,
    ),
)


@router.message(Command(commands=['start', 'help', 'menu']))
async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)


dialog = Dialog(
    Window(
        w.Format("Привет! "
                 "Я {bot_name} [{bot_version}] для отправки анонимных сообщений в чатик {chat_name}!\n"
                 "Пиши, что хочешь отправить. Могу отправить также 📊опрос или медиа (спрячу под спойлер).",
                 err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        state=Main.menu,
        getter=get.getter,
    ),
    Window(
        w.Format("Все готово! Отправляем в чатик?", err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        *MineOrNot,
        w.Button("Отправляем!", on_click=do.postcard_send, emoji=Emojis.mail),
        w.MainMenu(),
        state=Main.click_send,
        getter=get.getter,
    ),
    Window(
        w.Format("{sent_link}", when="no_error"),
        w.Format("{dialog_error}", when="dialog_error"),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        *MineOrNot,
        w.MainMenu(),
        state=Main.sent,
        getter=get.final_getter,
        parse_mode=ParseMode.HTML,
    ),
    on_start=do.on_start_postcard,
)
