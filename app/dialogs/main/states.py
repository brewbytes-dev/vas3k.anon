from aiogram.fsm.state import State, StatesGroup


class Main(StatesGroup):
    menu = State()
    get_postcard = State()
    click_send = State()
    sent = State()
