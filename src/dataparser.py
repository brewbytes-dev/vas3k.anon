import typing
from contextlib import suppress
from dataclasses import dataclass

from aiogram_dialog import DialogManager


@dataclass
class DataParser:
    dialog_error = ''
    dialog_manager: DialogManager = None

    @classmethod
    def register(cls, dialog_manager: DialogManager):
        inst = cls()
        inst.dialog_manager = dialog_manager
        inst._fetch()
        return inst

    @classmethod
    def parse(cls, data: typing.Dict):
        inst = cls()
        inst._fetch(data)
        return inst

    def clean(self):
        inst = type(self)()
        self.update((inst,))

    def update(self, data: typing.Tuple):
        for data_dict in data:
            if data_dict is None:
                continue

            if isinstance(data_dict, DataParser):
                data_dict = data_dict.force_dict()

            for key, value in data_dict.items():
                with suppress(Exception):
                    super().__setattr__(key, value)

                if self.dialog_manager:
                    self.dialog_manager.current_context().dialog_data[key] = value

    def _fetch(self, data=None):
        dialog_data = None

        if not self.dialog_manager:
            if data:
                dialog_data = data
        else:
            dialog_data = self.dialog_manager.current_context().dialog_data

        if dialog_data is not None:
            for key, value in dialog_data.items():
                with suppress(Exception):
                    super().__setattr__(key, value)

    def __getattr__(self, item):
        self._fetch()
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return None

    def __setattr__(self, key, value):
        if key != 'dialog_manager':
            self._fetch()

            if self.dialog_manager:
                self.dialog_manager.current_context().dialog_data[key] = value
        super().__setattr__(key, value)

    def pop(self, item):
        self.__setattr__(item, None)

    def force_dict(self) -> typing.Dict:
        return {key: jsonify(value) for key, value in self.__dict__.items()
                if value is not None and key != 'dialog_manager'}


def jsonify(value):
    if hasattr(value, 'to_json'):
        return value.to_json()

    return value
