import os
import re
from aiogram import Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime as dt
from sqlalchemy.exc import OperationalError

import config
from core.database.botDB import add_client_cashNumber
from core.utils.states import StateOstatki
from core.utils import texts
from core.database import progressDB
from core.keyboards.inline import getKeyboard_startMenu, getKeyboard_tehpod_url, getKeyboard_ostatki_entity, \
    getKeyboard_ostatki, getKeyboard_choose_list_ostatki
from core.utils.ostatki_server import get_last_file, get_last_files
from core.utils.callbackdata import Ostatki, OstatkiLast, OstatkiList, OstatkiChooseList


async def check_cash_number(message: Message):
    log = logger.bind(text=message.text)
    try:
        cash_info = progressDB.get_cash_info(message.text)
        count_cashes = progressDB.check_cash_info(message.text)
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


async def send_ostatki(chat_id, file_path, bot: Bot):
    date = file_path.split(os.sep)[-1].split('.')[0]
    date_file = dt.strptime(date, '%Y_%m_%d__%H_%M').strftime('%d-%m-%Y %H:%M')
    log = logger.bind(chat_id=chat_id, file_path=file_path, date=date_file)
    await bot.send_document(chat_id, document=FSInputFile(file_path))
    log.info("Отправил остатки")
    await bot.send_message(chat_id, texts.ostatki_date(date_file), reply_markup=getKeyboard_tehpod_url(), parse_mode='HTML')
    await bot.send_message(chat_id, texts.menu, reply_markup=getKeyboard_startMenu(), parse_mode='HTML')


async def enter_cash_number(call: CallbackQuery, state: FSMContext):
    logger.bind(name=call.message.chat.first_name, chat_id=call.message.chat.id). \
        info('Нажали кнопку "Остатки"')
    await call.message.answer(texts.enter_cash_number, parse_mode='HTML')
    await call.answer()
    await state.set_state(StateOstatki.choose_entity)


async def choose_entity(message: Message, state: FSMContext, bot: Bot):
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    cash_info = await check_cash_number(message)
    if not cash_info:
        await bot.send_message(message.chat.id, texts.menu, reply_markup=getKeyboard_startMenu())
        await state.clear()
        return
    log.info(f'Написали компьютер "{message.text}"')
    await add_client_cashNumber(chat_id=message.chat.id, cash=cash_info.name)
    await message.answer(texts.choose_entity, reply_markup=getKeyboard_ostatki_entity(cash_info))
    await state.clear()


async def choose_ostatki_menu(call: CallbackQuery, callback_data: Ostatki):
    inn, fsrar = (callback_data.inn, callback_data.fsrar)
    await call.message.edit_text(texts.ostatki, parse_mode='HTML', reply_markup=getKeyboard_ostatki(inn, fsrar))


async def push_last_ostatki(call: CallbackQuery, bot: Bot, callback_data: OstatkiLast):
    log = logger.bind(name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Кнопка "Последние остатки"')
    inn, fsrar = (callback_data.inn, callback_data.fsrar)
    last_file, date = await get_last_file(inn, fsrar)
    if not last_file:
        await call.message.edit_text(texts.error_head + 'Список остатков пуст')
        await bot.send_message(call.message.chat.id, texts.menu, reply_markup=getKeyboard_startMenu())
        return
    await call.message.delete()
    await send_ostatki(call.message.chat.id, last_file, bot)


async def choose_list_ostatki(call: CallbackQuery, bot: Bot, callback_data: OstatkiList):
    log = logger.bind(name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Кнопка "Список по датам"')
    inn, fsrar = (callback_data.inn, callback_data.fsrar)
    list_files = await get_last_files(inn, fsrar)
    if not list_files:
        await call.message.edit_text(texts.error_head + 'Список остатков пуст')
        await bot.send_message(call.message.chat.id, texts.menu, reply_markup=getKeyboard_startMenu())
        return
    await call.message.edit_text(texts.list_ostatki, reply_markup=getKeyboard_choose_list_ostatki(list_files, inn, fsrar))


async def push_list_ostatki(call: CallbackQuery, bot: Bot, callback_data: OstatkiChooseList):
    inn, fsrar = (callback_data.inn, callback_data.fsrar)
    file_path = os.path.join(config.server_path, 'ostatki', inn, fsrar, 'xls', callback_data.file_name)
    await call.message.delete()
    await send_ostatki(call.message.chat.id, file_path, bot)
