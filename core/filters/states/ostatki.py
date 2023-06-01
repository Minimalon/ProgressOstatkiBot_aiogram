import os
from aiogram import Bot
from aiogram.types import CallbackQuery, FSInputFile
from loguru import logger
from datetime import datetime as dt

import config
from core.utils import texts
from core.keyboards.inline import getKeyboard_startMenu, getKeyboard_tehpod_url, getKeyboard_choose_list_ostatki
from core.utils.ostatki_server import get_last_file, get_last_files
from core.utils.callbackdata import OstatkiLast, OstatkiList, OstatkiChooseList


async def send_ostatki(chat_id, file_path, bot: Bot):
    date = file_path.split(os.sep)[-1].split('.')[0]
    date_file = dt.strptime(date, '%Y_%m_%d__%H_%M').strftime('%d-%m-%Y %H:%M')
    log = logger.bind(chat_id=chat_id, file_path=file_path, date=date_file)
    await bot.send_document(chat_id, document=FSInputFile(file_path))
    log.info("Отправил остатки")
    await bot.send_message(chat_id, texts.ostatki_date(date_file), reply_markup=getKeyboard_tehpod_url(), parse_mode='HTML')
    await bot.send_message(chat_id, texts.menu, reply_markup=getKeyboard_startMenu(), parse_mode='HTML')


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
