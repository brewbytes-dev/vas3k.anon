import logging
from contextlib import suppress

from aiogram.types import CallbackQuery, ParseMode, Message
from aiogram.utils.markdown import hcode
from aiogram_dialog import DialogManager

from bot_loader import bot
from extensions.widgets import Button
from src.commands import Emojis
from src.keyboards import Keyboards
from src.prodom import ProdomApi
from src.special import UserRequests
from src.utils import get_repo
from .data import ClaimRequestData

logger = logging.getLogger(__name__)


async def store_claim(chat_id, text, message_id, claim_id, repo):
    user_claim = UserRequests()
    user_claim.user_id = chat_id
    user_claim.status = 'Новая'
    user_claim.text = text
    user_claim.message_id = message_id
    user_claim.request_id = claim_id
    await repo.new_request(user_claim)


async def postcard_send(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    ...


async def notify_when_available(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    repo = utils.get_repo(dialog_manager)
    ...


async def send_to_cc(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await c.answer('Отправляем...')
    data: ClaimRequestData = ClaimRequestData.register(dialog_manager)

    if not data.text:
        return await c.message.answer(text='Необходимо дополнить заявку текстовым описанием',
                                      parse_mode=ParseMode.HTML)

    photos = [await bot.download_file_by_id(file_id=file_id)
              for file_id in data.photos]

    if len(photos) > 3:
        photos = photos[:3]
        await c.answer("Сейчас Продом не принимает больше трех файлов, "
                       "поэтому в заявку добавлены только первые три", show_alert=True)

    text = '\n'.join(data.text)
    repo = get_repo(dialog_manager)

    api = ProdomApi()
    sent, claim_id = await api.new_request(encrypted_id=data.primary_account_account_id_hash,
                                           text=text,
                                           phone=data.primary_account_phone,
                                           files=photos)
    if sent:
        claim = hcode(str(claim_id))
        message_text = f'{Emojis.call_center} Заявка создана: №{claim}\n ' \
                       f'Вы получите уведомление при изменении статуса.'

        sent_message = await c.message.answer(text=message_text,
                                              reply_markup=Keyboards.happy,
                                              parse_mode=ParseMode.HTML)

        await store_claim(chat_id=c.from_user.id,
                          text=text,
                          message_id=sent_message.message_id,
                          claim_id=claim_id,
                          repo=repo)

        with suppress(Exception):
            await c.message.delete()

        await dialog_manager.done()
    else:
        await c.message.answer(text='Возникла ошибка и задача не смогла уйти диспетчеру',
                               parse_mode=ParseMode.HTML)


async def open_card(c: types.CallbackQuery, button, dialog_manager: DialogManager, ad_id: str = None):
    if dialog_manager.current_context() is not None:
        data: HlamData = HlamData.parse(dialog_manager)
    else:
        data = HlamData()

    ad_id = ad_id or data.ad_id

    repo = get_repo(dialog_manager)
    ad: HlamAd = await repo.hlam_ad(int(ad_id))

    state = AD_TYPE_STATE[ad.ad_type]

    data.hlam_ad = ad.force_dict()
    data.ad_type = ad.ad_type
    data.old_hlam_ad = deepcopy(data.hlam_ad)

    if dialog_manager.current_context() is not None:
        d_data = await on_start_hlam(data.force_dict(), dialog_manager)
    else:
        d_data = data.force_dict()

    await dialog_manager.start(state, d_data, mode=StartMode.RESET_STACK)
