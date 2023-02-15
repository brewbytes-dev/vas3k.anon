from aiogram.dispatcher.filters.state import StatesGroup, State


class Main(StatesGroup):
    menu = State()
    get_postcard = State()
    click_send = State()
    sent = State()
