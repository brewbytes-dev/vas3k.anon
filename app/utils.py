import logging
import logging
import typing
from collections import namedtuple
from io import BytesIO

from aiogram import types
from aiogram.types import Message
from emoji import demojize, emojize

from app import config
from bot_loader import bot

FSM_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MEDIA = [types.ContentType.DOCUMENT, types.ContentType.PHOTO, types.ContentType.VIDEO]

Forwarder = namedtuple("Forwarder", "content_type, aio_type, sender, spoilering")

ALL_MEDIA = {types.ContentType.PHOTO    : Forwarder(types.InputMediaPhoto,
                                                    types.ContentType.PHOTO,
                                                    bot.send_photo,
                                                    True,
                                                    ),
             types.ContentType.VIDEO    : Forwarder(types.InputMediaVideo,
                                                    types.ContentType.VIDEO,
                                                    bot.send_video,
                                                    True,
                                                    ),
             types.ContentType.DOCUMENT : Forwarder(types.InputMediaDocument,
                                                    types.ContentType.DOCUMENT,
                                                    bot.send_document,
                                                    Forwarder,
                                                    ),
             types.ContentType.ANIMATION: Forwarder(types.InputMediaAnimation,
                                                    types.ContentType.ANIMATION,
                                                    bot.send_animation,
                                                    True,
                                                    )
             }

logger = logging.getLogger(__name__)


def extract_special_command(message_text):
    emj = extract_emojis(message_text)
    if not emj:
        return
    return emojize(emj[0])


def extract_emojis(message_text):
    def is_emoji(command):
        return demojize(command).startswith(':') and demojize(command).endswith(':')

    def gen_emoji():
        if message_text:
            for command in message_text.split():
                if is_emoji(command):
                    yield demojize(command)

    return list(gen_emoji())


def contains(message_text, text=typing.Union[typing.List[str], str], ignore_case=True):
    if not message_text:
        return False

    if ignore_case:
        message_text = message_text.lower()

    if isinstance(text, typing.List):
        for text_item in text:

            if ignore_case:
                text_item = text_item.lower()

            if text_item in message_text:
                return True
        return False

    if ignore_case:
        text = text.lower()
    return text in message_text


async def clean_user_fsm(user_id):
    chat_id = user_id
    import redis
    r = redis.Redis().from_url(config.REDIS_URL)
    for key in r.scan_iter(f"fsm:{chat_id}:{user_id}:aiogd*"):
        r.delete(key)


def get_content_type_and_file_id_from_message(m: types.Message, allowed_types: typing.Iterable):
    content_type = m.content_type
    if m.content_type not in allowed_types:
        raise ValueError(f'Incorrect content_type {content_type}')

    file_id = get_id_from_message(m)

    return content_type, file_id


async def get_photo_from_message(m: types.Message):
    pic_io = BytesIO()

    file_id = get_id_from_message(m)
    if m.content_type != types.ContentType.PHOTO:
        file_id = None

    if file_id:
        await bot.download_file_by_id(file_id=file_id, destination=pic_io)
        return pic_io


def get_id_from_message(m: types.Message):
    if m.content_type == types.ContentType.DOCUMENT:
        file_id = m.document.file_id
    elif m.content_type == types.ContentType.PHOTO:
        file_id = m.photo[-1].file_id
    elif m.content_type == types.ContentType.VIDEO:
        file_id = m.video.file_id
    elif m.content_type == types.ContentType.ANIMATION:
        file_id = m.animation.file_id
    else:
        file_id = None

    return file_id
