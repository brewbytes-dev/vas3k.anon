import logging
import uuid
from enum import Enum, auto
from functools import partial
from itertools import islice, accumulate, chain
from operator import itemgetter
from random import getrandbits
from typing import Optional, Union, Callable, Dict, Sequence, List

import aiogram.types as types
import aiogram_dialog.widgets.kbd as adw
from aiogram.dispatcher.filters.state import State
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils import emoji as emj
from aiogram.utils.exceptions import Throttled
from aiogram.utils.markdown import hlink
from aiogram_dialog import DialogManager, StartMode, Data, Dialog
from aiogram_dialog.widgets.kbd import Keyboard
from aiogram_dialog.widgets.kbd.button import OnClick
from aiogram_dialog.widgets.kbd.select import get_identity
from aiogram_dialog.widgets.kbd.state import EventProcessorButton
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.text.multi import Selector
from aiogram_dialog.widgets.when import WhenCondition, Predicate

from app.dialogs.main.states import Main
from app.loader import dp
from app.extensions.emojis import Emojis
from app.utils import clean_user_fsm

logger = logging.getLogger(__name__)
THROTTLE_RATE = 1


class ClickMode(Enum):
    NORMAL = auto()
    IDEMPOTENT = auto()
    THROTTLED = auto()


def generate_id():
    return str(uuid.uuid4()).replace('-', '_')


def process_throttle(button, original_process):
    async def _process(c, dialog, dialog_manager):
        if c.data != button.widget_id:
            return False

        try:
            await dp.throttle(rate=THROTTLE_RATE, key=button.widget_id)
            return await original_process(c, dialog, dialog_manager)
        except Throttled:
            await c.answer("Ой, кажется вы жмете кнопки слишком быстро!", show_alert=True)
            logger.error('Too fast click on %s', button.widget_id)
            return False

    return _process


def process_idempotent(button, original_process):
    async def _process(c, dialog, dialog_manager):
        if c.data != button.widget_id:
            return False

        idempotency_key = dialog_manager.current_context().widget_data.get('idempotency_key')
        widget_key = dialog_manager.current_context().widget_data['widget_key']

        if idempotency_key == widget_key:
            print('oops')
            return False

        dialog_manager.current_context().widget_data['idempotency_key'] = widget_key
        return await original_process(c, dialog, dialog_manager)

    return _process


def _render_keyboard_idempotent(original):
    async def _render(data: Dict, dialog_manager: DialogManager):
        h = getrandbits(32)
        dialog_manager.current_context().widget_data['widget_key'] = "%08x" % h
        return await original(data, dialog_manager)

    return _render


async def throttled_click(on_click, c: types.CallbackQuery, b: adw.Keyboard, m, *args, **kwargs):
    try:
        await dp.throttle(rate=THROTTLE_RATE, key=b.widget_id)
    except Throttled:
        await c.answer("Ой, кажется вы жмете кнопки слишком быстро!", show_alert=True)
        # logger.error('Too fast click on %s', b.widget_id)
        raise CancelHandler()

    if on_click:
        await on_click(c, b, m, *args, **kwargs)


class Format(Text):
    def __init__(
            self,
            text: str,
            err_prefix: bool = False,
            emojize=False,
            when: WhenCondition = None):
        super().__init__(when)

        if err_prefix:
            text = "{dialog_error}\n\n" + text

        self.emojize = emj.emojize if emojize else (lambda x: x)
        self.text = text

    async def _render_text(self, data: Dict, dialog_manager: DialogManager) -> str:
        text = self.text.format_map(data)
        return self.emojize(text)


async def close_kb(c: types.CallbackQuery, button: adw.Button, dialog_manager: DialogManager):
    await dialog_manager.event.bot.send_message(
        chat_id=c.from_user.id,
        text='Отменено',
        reply_markup=types.ReplyKeyboardRemove())


class Cancel(adw.Cancel):
    def __new__(cls, close_keyboard):
        return MainMenu(
            text=Format(f"{emj.emojize(':wastebasket:')} Отмена"),
            on_click=close_kb if close_keyboard else None,
            id='cancel_kb',
            mode=StartMode.RESET_STACK)


class Next:
    def __new__(cls, text, *args, **kwargs):
        kwargs['on_click'] = partial(throttled_click, kwargs.get('on_click'))
        return adw.Next(text=Format(f"{emj.emojize(':right_arrow:')} {text}"))


class Back:
    def __new__(cls, *args, to=None, **kwargs):
        kwargs['on_click'] = partial(throttled_click, kwargs.get('on_click'))
        if to:
            return adw.SwitchTo(
                text=Format(f"{emj.emojize(':left_arrow:')} Назад"),
                id='back', state=to)
        else:
            return adw.Back(
                text=Format(f"{emj.emojize(':left_arrow:')} Назад"),
                id='back')


class Button:
    def __new__(
            cls, text: Union[Format, str],
            *,
            click_mode: ClickMode = ClickMode.NORMAL,
            on_click,
            emoji: Emojis, **kwargs) -> adw.Button:
        if isinstance(text, Format):
            text = text.text

        if emoji == Emojis.NONE:
            text = Format(text)
        else:
            text = Format(f"{emoji} {text}")

        if 'id' not in kwargs:
            kwargs['id'] = generate_id()

        b = adw.Button(text, on_click=on_click, **kwargs)

        if click_mode == ClickMode.THROTTLED:
            b.process_callback = process_throttle
        elif click_mode == ClickMode.IDEMPOTENT:
            b.process_callback = process_idempotent(b, b.process_callback)
            b._render_keyboard = _render_keyboard_idempotent(b.render_keyboard)

        return b


class SwitchTo:
    def __new__(cls, text: Union[Format, str],
                *,
                state,
                emoji: Emojis,
                **kwargs) -> adw.SwitchTo:
        if isinstance(text, Format):
            text = text.text

        if emoji == Emojis.NONE:
            text = Format(text)
        else:
            text = Format(f"{emoji} {text}")

        if 'id' not in kwargs:
            kwargs['id'] = generate_id()
        kwargs['on_click'] = partial(throttled_click, kwargs.get('on_click'))
        return adw.SwitchTo(text, state, **kwargs, state=state)


class Multiselect:
    def __new__(cls, *args, **kwargs):
        kwargs['on_click'] = partial(throttled_click, kwargs.get('on_click'))
        return adw.Multiselect(*args, **kwargs)


async def throttled_main_click(on_click, c: types.CallbackQuery, b: adw.Keyboard, m, *args, **kwargs):
    try:
        await dp.throttle(rate=THROTTLE_RATE, key=b.widget_id)
    except Throttled:
        await c.answer("Ой, кажется вы жмете кнопки слишком быстро!", show_alert=True)
        logger.error('Too fast click on %s', b.widget_id)
        raise CancelHandler()

    await clean_user_fsm(c.from_user.id)

    if on_click:
        await on_click(c, b, m, *args, **kwargs)



class Chat(Keyboard):
    def __init__(self, bot_name, chat_name, chat_title, when: Union[str, Callable, None] = None):
        _id = generate_id()
        super().__init__(_id, when)
        self.bot_name = bot_name
        self.chat_name = chat_name
        self.chat_title = chat_title

    async def _render_keyboard(self, data: Dict, manager: DialogManager) -> List[List[types.InlineKeyboardButton]]:
        bot_name = await self.bot_name.render_text(data, manager)
        chat_name = await self.chat_name.render_text(data, manager)
        chat_title = await self.chat_title.render_text(data, manager)

        # open_chat_auth_page(dialog_manager, chats, chat, user)

        text = f"{chat_title} [После открытия нажмите Start/Начать]"
        url = f't.me/{bot_name}?start={chat_name}'

        return [[
            types.InlineKeyboardButton(
                text=text,
                url=url
            )
        ]]


class MainMenu:
    def __new__(cls, **kwargs):
        kwargs['on_click'] = partial(throttled_main_click, kwargs.get('on_click'))
        return adw.Start(
            text=Format(f'{emj.emojize(":house:")} В главное меню'), id='start_bot', state=Main.menu,
            on_click=kwargs['on_click'], mode=StartMode.RESET_STACK)


class Start(EventProcessorButton):
    def __init__(
            self, text: Text, id: str,
            state: State,
            data: Data = None,
            on_click: Optional[OnClick] = None,
            mode: StartMode = StartMode.NORMAL,
            when: WhenCondition = None):
        super().__init__(text, id, self._on_click, when)
        self.text = text
        self.user_on_click = partial(throttled_click, on_click)
        self.state = state
        self.mode = mode
        self.data = data

    async def _on_click(self, c: types.CallbackQuery, button: Button, dialog_manager: DialogManager):
        if self.user_on_click:
            await self.user_on_click(c, self, dialog_manager)
        await dialog_manager.start(self.state, mode=self.mode, data=self.data)


class Select:
    def __new__(cls, *args, **kwargs):
        kwargs['on_click'] = partial(throttled_click, kwargs.get('on_click'))
        return adw.Select(*args, **kwargs)


class Layout(adw.Keyboard):
    def __init__(
            self,
            *buttons: adw.Keyboard,
            id: Optional[str] = None,
            layout: Union[str, Sequence] = None,
            when: WhenCondition = None):
        super().__init__(id, when)
        self.buttons = buttons

        if isinstance(layout, str):
            self.layout_getter = itemgetter(layout)
        elif layout is None:
            self.layout_getter = lambda x: None
        else:
            self.layout_getter = get_identity(layout)

    def find(self, widget_id):
        widget = super(Layout, self).find(widget_id)
        if widget:
            return widget
        for btn in self.buttons:
            widget = btn.find(widget_id)
            if widget:
                return widget
        return None

    async def _render_keyboard(self, data: Dict, dialog_manager: DialogManager) -> List[
        List[types.InlineKeyboardButton]]:
        kbd: List[List[types.InlineKeyboardButton]] = []
        layout = self.layout_getter(data)

        for b in self.buttons:
            b_kbd = await b.render_keyboard(data, dialog_manager)
            if layout is None or not kbd:
                kbd += b_kbd
            else:
                kbd[0].extend(chain.from_iterable(b_kbd))

        if layout and kbd:
            kbd = list(self._wrap_kbd(kbd[0], layout))
        return kbd

    def _wrap_kbd(self, kbd: List[types.InlineKeyboardButton], layout: Sequence) -> List[
        List[types.InlineKeyboardButton]]:
        _layout = list(accumulate(layout))

        for start, end in zip(
                [0, *_layout],
                [*_layout, _layout[-1]]):
            yield list(islice(kbd, start, end))

    async def process_callback(self, c: types.CallbackQuery, dialog: Dialog, dialog_manager: DialogManager) -> bool:
        for b in self.buttons:
            if await b.process_callback(c, dialog, dialog_manager):
                return True
        return False


class PrivacyWarn(Format):
    def __new__(cls, prefix: str = "Для продолжения", when='privacy_error', *args, **kwargs):
        return Format(
            f"{Emojis.warning} {prefix} "
            f"{hlink(title='разрешите боту ссылаться на ваш аккаунт', url='https://teletype.in/@lainer/allow_bot')}",
            when=when)


class CaseBool(Text):
    def __init__(self, on_true, on_false, selector: Union[str, Selector], when: WhenCondition = None):
        super().__init__(when)
        self.getter = [on_false, on_true]
        if isinstance(selector, str):
            self.selector = new_case_bool_field(selector)
        else:
            self.selector = selector

    async def _render_text(self, data, manager: DialogManager) -> str:
        selection = self.selector(data, self, manager)
        return await self.getter[selection].render_text(data, manager)


def new_case_bool_field(fieldname: str) -> Predicate:
    def case_field(data: Dict, widget: "CaseBool", manager: DialogManager) -> bool:
        return bool(data.get(fieldname))

    return case_field
