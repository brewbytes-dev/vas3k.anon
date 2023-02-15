import logging
import uuid
from enum import Enum, auto
from functools import partial
from random import getrandbits
from typing import Union, Dict

import aiogram.types as types
import aiogram_dialog.widgets.kbd as adw
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils import emoji as emj
from aiogram.utils.exceptions import Throttled
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.when import WhenCondition

from app.dialogs.main.states import Main
from app.extensions.emojis import Emojis
from app.loader import dp
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


class MainMenu:
    def __new__(cls, **kwargs):
        kwargs['on_click'] = partial(throttled_main_click, kwargs.get('on_click'))
        return adw.Start(
            text=Format(f'{emj.emojize(":house:")} В главное меню'), id='start_bot', state=Main.menu,
            on_click=kwargs['on_click'], mode=StartMode.RESET_STACK)
