import typing

from aiogram.types import Message, ContentType
from aiogram_dialog import Dialog, DialogManager
from dialogs.shared.data import copy_data
from src.special import SpecialType, Property
from src.states import ClaimRequest
from src.types import WorkerAccessType
from src.utils import get_repo, get_id_from_message

from dialogs.main import PostCardData


async def getter(dialog_manager: DialogManager, **kwargs):
    data: PostCardData = PostCardData.register(dialog_manager)
    return {
        "dialog_error": data.dialog_error,
    }


async def postcard_data(m: Message, d: Dialog, dialog_manager: DialogManager):
    data: PostCardData = PostCardData.register(dialog_manager)
    text, photos, messages = data.text, data.photos, data.messages

    if m.content_type == ContentType.TEXT:
        text.append(m.text)
    elif m.content_type == ContentType.PHOTO:
        text.append(m.text)
        photos.append(get_id_from_message(m))
    else:
        data.dialog_error = "Нормальная открытка содержит только текст или фото"
        return

    data.dialog_error = ''
    messages.append(m.message_id)

    data.text = text
    data.photos = photos
    data.messages = messages


async def cc_on_start(start_data: typing.Dict, dialog_manager: DialogManager):
    await copy_data(start_data, dialog_manager)
    house, primary_account = await primary_house_account(dialog_manager)

    if not primary_account:
        return await dialog_manager.switch_to(ClaimRequest.auth)

    await fill_data(dialog_manager, primary_account, house)


async def fill_data(dialog_manager: DialogManager, primary_account: Property, house_name):
    data: ClaimRequestData = ClaimRequestData.register(dialog_manager)
    data.primary_account_address = primary_account.address
    data.primary_account_phone = primary_account.phone
    data.primary_account_account_id_hash = primary_account.account_id_hash

    repo = get_repo(dialog_manager)
    houses = await repo.houses()

    house = houses[house_name]
    data.house_name_rus = house.name_rus

    house_chat = await repo.chat(house.chat_name)
    spec: SpecialType = house_chat.specs[WorkerAccessType.call_center]
    data.spec_helper_message = spec.helper_message
    data.spec_emoji = spec.emoji


async def cards_lists(dialog_manager: DialogManager, **kwargs):
    data: HlamData = HlamData.parse(dialog_manager)
    repo = get_repo(dialog_manager)
    user_id = get_chat(dialog_manager.event).id
    data.hlam_ad = None

    hlam_list: typing.List[HlamAd] = await repo.hlam_ads_by_user(user_id)
    hlam_list_print = [[hlam_ad.id,
                        hlam_ad.title,
                        hlam_ad.posted_date,
                        format_date(hlam_ad.posted_date, "d MMM", locale='ru_RU')]
                       for hlam_ad in hlam_list]
    return {**data.force_dict(), "my_ads": hlam_list_print}
