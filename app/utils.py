import asyncio
import logging
import os
import typing
from datetime import timezone, datetime
from hashlib import blake2b
from io import BytesIO

import pytz
from aiogram import Bot, types
from aiogram.types import InputMediaPhoto, ParseMode, Chat, ChatType, Message
from aiogram.utils.emoji import demojize, emojize
from aiogram.utils.exceptions import ChatNotFound, BotKicked, BotBlocked, MessageNotModified, MigrateToChat, \
    MessageToEditNotFound, RetryAfter, MessageIdentifierNotSpecified, Unauthorized
from aiogram_dialog.utils import get_chat

from bot_loader import bot
from app import config

FSM_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MEDIA = [types.ContentType.DOCUMENT, types.ContentType.PHOTO, types.ContentType.VIDEO]
ALL_MEDIA = {types.ContentType.PHOTO: types.InputMediaPhoto,
             types.ContentType.VIDEO: types.InputMediaVideo,
             types.ContentType.DOCUMENT: types.InputMediaDocument,
             types.ContentType.ANIMATION: types.Animation}


logger = logging.getLogger(__name__)


def html_mention(user_id, name='username'):
    return f'<a href=\"tg://user?id={user_id}\">{name}</a>'


async def user_mention(user_id, name='username', return_full_name_on_error=True):
    try:
        user_chat = await bot.get_chat(user_id)
        if user_chat.has_private_forwards and not user_chat.username:
            if return_full_name_on_error:
                return user_chat.full_name
            else:
                raise RuntimeError('User is not available for mention')
        else:
            return user_chat.get_mention(name=user_chat.mention or name, as_html=True)
    except Exception as e:
        if return_full_name_on_error:
            return html_mention(user_id, name)
        else:
            raise RuntimeError('User is not available for mention')


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


def get_login():
    try:
        return os.getlogin()
    except OSError:
        return None


def extract_unique_code(text):
    # Extracts the unique_code from the sent /start command.
    return text.split()[1] if len(text.split()) > 1 else None


def _check_access_type(user, chat, access_type):
    workers = chat.specs[access_type].workers

    for worker in workers:
        if worker.userid == user:
            return True


def get_hash(text: typing.Union[str, typing.List], digest_size=5):
    if not isinstance(text, typing.List):
        text = [text]

    h = blake2b(digest_size=digest_size)
    for t in text:
        h.update(str.encode(t))
    return h.hexdigest()


def moscow_time(dt):
    moscow_tz = 'Europe/Moscow'
    if isinstance(dt, int):
        return datetime.fromtimestamp(dt, tz=pytz.timezone(moscow_tz))
    return dt.astimezone(pytz.timezone(moscow_tz))


def moscow_time_timestamp(dt):
    return moscow_time(dt).timestamp()


def moscow_time_zone_independent(dt):
    return moscow_time(dt).replace(tzinfo=None)


def unix_time_millis(dt):
    return int(dt.astimezone(tz=timezone.utc).timestamp() * 1000)


def from_unix(ts):
    return datetime.fromtimestamp(int(ts) / 1000)


def date_to_fsm(dt: datetime):
    return dt.strftime(FSM_DATE_FORMAT)


def date_from_fsm(datestr):
    return datetime.strptime(datestr, FSM_DATE_FORMAT)


def normalize_apartment_num(apartment_num: str):
    entrance, num = apartment_num.split('-')
    return f'{int(num)}{entrance}'


def normalize_carplace_num(carplace_num: str):
    entrance, num = carplace_num.split('-')
    return f'{int(num)}'


async def clean_user_fsm(user_id):
    chat_id = user_id
    import redis
    r = redis.Redis().from_url(config.REDIS_URL)
    for key in r.scan_iter(f"fsm:{chat_id}:{user_id}:aiogd*"):
        r.delete(key)


# @timed_lru_cache(seconds=600, maxsize=None)
async def chat_members_count(bot: Bot, chat_id):
    try:
        return await bot.get_chat_member_count(chat_id)
    except (ChatNotFound, BotKicked, BotBlocked, MigrateToChat, Unauthorized) as e:
        logger.error(e)
        return 0


def iter_to_json(element):
    if isinstance(element, list):
        return [el.to_dict() for el in element]

    if isinstance(element, dict):
        return {k: v.to_dict() for k, v in element.items()}

    return element


def iter_to_json_dict(element):
    if isinstance(element, list):
        return [el.to_dict() for el in element]

    return element


def get_content_type_and_file_id_from_message(m: types.Message, allowed_types: typing.Iterable):
    content_type = m.content_type
    if m.content_type not in allowed_types:
        raise ValueError(f'Incorrect content_type {content_type}')

    if content_type == types.ContentType.PHOTO:
        file_id = m.photo[-1].file_id
    elif content_type == types.ContentType.DOCUMENT:
        file_id = m.document.file_id
    elif content_type == types.ContentType.VIDEO:
        file_id = m.video.file_id
    else:
        return content_type, None

    return content_type, file_id


async def edit_or_send_new_message(chat_id, message_id, text,
                                   parse_mode=types.ParseMode.HTML, reply_markup=None,
                                   on_exception=None, photo_id=None):
    if photo_id:
        method = bot.edit_message_media
        second_method = bot.send_photo
        media = InputMediaPhoto(photo_id, caption=text, parse_mode=parse_mode)
        kwargs = {"media": media}
        kwargs_second = {"photo": photo_id, "caption": text, 'parse_mode': parse_mode}
    else:
        method = bot.edit_message_text
        second_method = bot.send_message
        kwargs = kwargs_second = {"text": text, 'parse_mode': parse_mode, 'disable_web_page_preview': True}

    try:
        sent = await method(**kwargs, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
        sent_message_id = sent.message_id
    except RetryAfter as e:
        await asyncio.sleep(e.timeout + 1)
        return await edit_or_send_new_message(chat_id, message_id, text,
                                              parse_mode, reply_markup, on_exception, photo_id)
    except MessageNotModified as e:
        sent = None
        sent_message_id = message_id
    except (MessageToEditNotFound, MessageIdentifierNotSpecified) as e:
        if on_exception:
            await on_exception()

        sent = await second_method(**kwargs_second, chat_id=chat_id, reply_markup=reply_markup)
        sent_message_id = sent.message_id
    except Exception as e:
        print(e)
        if on_exception:
            await on_exception()
        sent = await second_method(**kwargs_second, chat_id=chat_id, reply_markup=reply_markup)
        sent_message_id = sent.message_id

    return sent, sent_message_id


async def uncompress_photo_from_message(m: Message, chat_to_uncompress):
    pic_io = BytesIO()
    await m.document.download(destination_file=pic_io)

    try:
        sent = await bot.send_photo(chat_id=chat_to_uncompress, photo=pic_io, caption="Будет загружено сжатое фото")
    except:
        id_file = None
    else:
        id_file = sent.photo[-1].file_id

    pic_io.close()

    return id_file


async def get_photo_from_message(m: types.Message):
    pic_io = BytesIO()

    file_id = await get_id_from_message(m)
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


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = set(o for o in shared_keys if d1[o] == d2[o])
    return added, removed, modified, same


def dicts_are_equal(d1, d2):
    added, removed, modified, same = dict_compare(d1, d2)
    return not added and not removed and not modified


async def hidden_user(dialog_manager):
    try:
        await user_mention(get_chat(dialog_manager.event).id, return_full_name_on_error=False)
        privacy_error = False
    except Exception as e:
        privacy_error = True
    return privacy_error


def get_repo(dialog_manager):
    repo = dialog_manager.data['repo']
    return repo


def get_context_data(dialog_manager):
    context = dialog_manager.current_context()
    if context is not None:
        data = dialog_manager.current_context().dialog_data
    else:
        data = dict()

    return data, context


def thread_to_message(chat_id, message_id):
    chat_id = str(chat_id).replace('-100', '')
    comments_url = f'https://t.me/c/{chat_id}/{message_id + 1}' \
                   f'?thread={message_id}'
    return comments_url


def thread_to_message_2(chat_id, chat_post_id, comment_id):
    chat_id = str(chat_id).replace('-100', '')
    comments_url = f'https://t.me/c/{chat_id}/{comment_id}?thread={chat_post_id}'
    return comments_url


def channel_comments(channel_id, channel_post_id, chat_message_id):
    chat_id = str(channel_id).replace('-100', '')
    comments_url = f'https://t.me/{chat_id}/{channel_post_id}?comment={chat_message_id}'
    return comments_url


async def edit_message_w_wo_media(chat_id, message_id, text, media):
    if media:
        try:
            with media.open('rb') as media_io:
                empty_media = InputMediaPhoto(media_io,
                                              caption=text,
                                              parse_mode=ParseMode.HTML)
                await bot.edit_message_media(media=empty_media,
                                             chat_id=chat_id,
                                             message_id=message_id,
                                             reply_markup=None)
        except Exception as e:
            logger.exception(e)
    else:
        try:
            await bot.edit_message_text(text=text,
                                        chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=None)
        except Exception as e:
            logger.exception(e)


def link_to_chat_message(chat_id, message_id, text='message', as_html=True):
    mock_chat = Chat(id=int(chat_id),
                     type=ChatType.GROUP)
    mock_message = Message(chat=mock_chat,
                           message_id=int(message_id))
    return mock_message.link(text, as_html)
