import re
from sqlalchemy.exc import OperationalError

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from loguru import logger

from core.database import query_PROGRESS
from core.database.query_BOT import get_client_info, add_client_cashNumber, check_cashNumber
from core.keyboards.inline import getKeyboard_startMenu, getKeyboard_tehpod_url, getKeyboard_ostatki_entity, getKeyboard_ostatki
from core.utils import texts
from core.utils.callbackdata import Ostatki
from core.utils.states import StateOstatki


async def check_cash_number(message: Message):
    log = logger.bind(text=message.text)
    try:
        cash_info = query_PROGRESS.get_cash_info(message.text)
        count_cashes = query_PROGRESS.check_cash_info(message.text)
        if not message.text.isdigit():
            log.error('Состоит не только из цифр')
            await message.answer(texts.error_cashNumber)
            return False
        elif not re.findall('^[0-9]{1,4}$', message.text):
            log.error('Не проходит по регулярному выражению "^[0-9]{1,4}$"')
            await message.answer(texts.error_cashNumber)
            return False
        elif not cash_info:
            log.error("Не найдено кассы в базе данных")
            await message.answer(texts.error_cash_not_found)
            return False
        elif count_cashes > 1:
            log.error('Найдено больше одной кассы')
            await message.answer(texts.error_duplicateCash)
            return False
        return cash_info
    except OperationalError as ex:
        return await check_cash_number(message)


async def enter_cash_number(call: CallbackQuery, state: FSMContext):
    logger.bind(name=call.message.chat.first_name, chat_id=call.message.chat.id). \
        info('Нажали кнопку "Остатки"')
    await call.message.answer(texts.enter_cash_number, parse_mode='HTML')
    await call.answer()
    await state.set_state(StateOstatki.enter_cashNumber)


async def choose_entity(message: Message, state: FSMContext, bot: Bot):
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    cash_info = await check_cash_number(message)
    if not cash_info:
        await bot.send_message(message.chat.id, texts.menu, reply_markup=getKeyboard_startMenu())
        await state.clear()
        return
    log.info(f'Написали компьютер "{message.text}"')
    await state.set_state(StateOstatki.choose_entity)
    await state.update_data(cash=cash_info.name)
    await message.answer(texts.choose_entity, reply_markup=getKeyboard_ostatki_entity(cash_info))


async def enter_inn(call: CallbackQuery, state: FSMContext, callback_data: Ostatki):
    inn, fsrar = (callback_data.inn, callback_data.fsrar)
    data = await state.get_data()
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id, inn=inn, fsrar=fsrar)
    client = await get_client_info(chat_id=call.message.chat.id)
    log.info(f'Выбрали Юр.Лицо "{inn}"')
    await state.update_data(inn=inn, fsrar=fsrar, admin=client.admin)
    await state.set_state(StateOstatki.inn)
    # Если пользователь уже логинился с этим номером компа раньше, то сразу выдаю меню
    if await check_cashNumber(str(call.message.chat.id), data['cash']):
        await state.set_state(StateOstatki.menu)
        await call.message.edit_text(texts.ostatki, reply_markup=getKeyboard_ostatki(inn, fsrar))
    else:
        await call.message.answer('Напишите ИНН юр.лица которого выбрали:\nНужны только цифры. Например: <b><u>1660340123</u></b>')


async def menu(message: Message, state: FSMContext):
    log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
    data = await state.get_data()
    inn = data.get('inn')
    log.info(f'Ввели ИНН "{inn}"')
    if inn == message.text:
        await add_client_cashNumber(chat_id=message.chat.id, cash=data['cash'])
        await state.set_state(StateOstatki.menu)
        inn, fsrar = data['inn'], data['fsrar']
        await message.answer(texts.ostatki, parse_mode='HTML', reply_markup=getKeyboard_ostatki(inn, fsrar))
    else:
        log.error('Ввели неверный ИНН')
        await message.answer(texts.error_head + "Вы ввели неверный ИНН\nПопробуйте снова.", reply_markup=getKeyboard_tehpod_url())
