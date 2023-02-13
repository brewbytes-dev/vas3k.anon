import operator
from dataclasses import dataclass

from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, ContentType
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Group

import extensions.widgets as w
from src.dataparser import DataParser
from src.emojis import Emojis
from . import get, do


class Main(StatesGroup):
    menu = State()
    what_to_do = State()
    save_message = State()
    send_message = State()
    saved_list = State()
    approve = State()


@dataclass
class PostCardData(DataParser):
    messages = None
    text = None
    photos = None

    def __post_init__(self):
        self.messages = []
        self.text = []
        self.photos = []


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(Main.menu, mode=StartMode.RESET_STACK)


dialog = Dialog(
    Window(
        w.Format("Привет! Я vas3k bot для отправки анонимных валентинок!"
                 "Пришли мне юзернейм или перешли сообщение того, кому хочешь отправить поздравление."),
        w.SwitchTo("Сохраненные", state=Main.saved_list, emoji=Emojis.mail),
        state=Main.menu,
        remove_on_close=True,
    ),
    Window(
        w.Format("Этот друг еще не заходил в бота, поэтому мы можем "
                 "сохранить ему валентинку и отправить сразу когда придет. "
                 "Либо я могу прислать вам уведомление, когда человек появится в боте"),
        w.SwitchTo("Сохранить", emoji=Emojis.mail, state=Main.save_message),
        w.Button("Напомнить", emoji=Emojis.mail, id='send', on_click=do.notify_when_available),
        w.MainMenu(),
        state=Main.what_to_do,
        remove_on_close=True,
    ),
    Window(
        w.Format("Отправьте мне открытку, я ее сохраню "
                 "и отправлю получателю как только он придет",
                 err_prefix=True),
        MessageInput(get.postcard_data, content_types=ContentType.ANY),
        w.MainMenu(),
        getter=get.getter,
        state=Main.save_message,
        remove_on_close=True,
    ),
    Window(
        w.Format("Все готово. Сохраняем и отправим в будущем?",
                 err_prefix=True),
        w.Button("Сохранить", emoji=Emojis.save, on_click=do.postcard_save),
        w.MainMenu(),
        state=Main.click_save,
        remove_on_close=True,
    ),
    Window(
        w.Format("Отправьте мне открытку, затем мы все проверим и отправим ее",
                 err_prefix=True),
        MessageInput(do.store_postcard_message, content_types=ContentType.ANY),
        w.MainMenu(),
        getter=get.getter,
        state=Main.send_message,
        remove_on_close=True,
    ),
    Window(
        w.Format("Все готово! Отправляем получателю?"),
        MessageInput(do.postcard_send, content_types=ContentType.ANY),
        w.MainMenu(),
        state=Main.click_send,
        remove_on_close=True,
    ),
    Window(
        w.Format("Открытки, которые ждут отправки:"),
        Group(
            w.Select(
                w.Format("{item[1]}, {item[3]}"),
                id="my_cards_lists",
                item_id_getter=operator.itemgetter(0),
                items="my_cards",
                on_click=do.open_card,
                when='my_cards',
            ),
            width=1,
            when='my_cards',
        ),
        w.MainMenu(),
        getter=get.cards_lists,
        state=Main.saved_list,
    ),
    on_start=get.cc_on_start,
)
