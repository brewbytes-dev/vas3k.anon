import logging
import uuid
from enum import Enum, auto
from typing import Union, Dict

import aiogram_dialog.widgets.kbd as adw
import emoji as emj
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.text import Text

from app.dialogs.main.states import Main
from app.extensions.emojis import Emojis

logger = logging.getLogger(__name__)


class ClickMode(Enum):
    NORMAL = auto()


def generate_id():
    return str(uuid.uuid4()).replace('-', '_')


class Format(Text):
    def __init__(
            self,
            text: str,
            err_prefix: bool = False,
            emojize=False,
            when=None):
        super().__init__(when)

        if err_prefix:
            text = f"{{dialog_error}}\n\n" + text

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
        return adw.SwitchTo(text, state, **kwargs, state=state)


class MainMenu:
    def __new__(cls, **kwargs):
        return adw.Start(
            text=Format(f'{emj.emojize(":house:")} В главное меню'), id='start_bot', state=Main.menu,
            on_click=kwargs.get('on_click'), mode=StartMode.RESET_STACK)
