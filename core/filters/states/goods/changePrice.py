import asyncio
import os
import re

import sqlalchemy
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

import config
from core.database.query_BOT import create_barcode
from core.filters.states.TTNS import read_barcodes_from_image, check_file_exist
from core.keyboards.inline import getKeyboard_tehpod_url
from core.utils import texts
from core.utils.states import ChangePrice
from cron.barcodes import update_price_in_cash


async def send_barcode(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChangePrice.barcode)
    await call.message.edit_text('Напишите цифры штрихкода или пришлите фото штрихкода')

async def text_barcode(message: Message, state: FSMContext):
    log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
    if not message.text.isdigit():
        log.error(f'Штрихкод состоит не из цифр "{message.text}"')
        await message.answer(texts.error_head + 'Штрихкод состоит только из цифр.\nВведите штрихкод еще раз')
    log.info(f'Написали штрихкод "{message.text}"')
    await state.update_data(barcode=message.text)
    await state.set_state(ChangePrice.price)
    await message.answer('Напишите цену товара')


async def photo_barcode(message: Message, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    log = logger.bind(first_name=message.chat.first_name, chat_id=chat_id)
    barcode_path = os.path.join(config.dir_path, 'files', 'boxnumbers', str(chat_id))
    img = await bot.get_file(message.photo[-1].file_id)
    if not os.path.exists(barcode_path):
        os.mkdir(barcode_path)
    file = os.path.join(barcode_path, f'barcode_{message.message_id}.jpg')
    await bot.download_file(img.file_path, file)

    barcodes_from_img = await read_barcodes_from_image(file)
    log.info(f'Отсканировал фото "{barcodes_from_img}"')

    if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
        await check_file_exist(file, 'На данном фото <b><u>не найдено</u></b> штрихкодов', bot, message)
        return
    elif len(barcodes_from_img) > 1:
        await check_file_exist(file, 'На данном фото найдено <b><u>несколько</u></b> штрихкодов', bot, message)
        return

    if os.path.exists(file):
        await asyncio.sleep(0.20)
        os.remove(file)

    await state.update_data(barcode=barcodes_from_img[0])
    await state.set_state(ChangePrice.price)
    await message.answer('Напишите цену товара')


async def document_barcode(message: Message, state: FSMContext, bot: Bot):
    chat_id = message.chat.id
    log = logger.bind(first_name=message.chat.first_name, chat_id=chat_id)

    barcode_path = os.path.join(config.dir_path, 'files', 'boxnumbers', str(chat_id))
    img = await bot.get_file(message.document.file_id)
    if not os.path.exists(barcode_path):
        os.mkdir(barcode_path)
    file = os.path.join(barcode_path, f'barcode_{message.message_id}.jpg')
    await bot.download_file(img.file_path, file)

    barcodes_from_img = await read_barcodes_from_image(file)
    log.info(f'Отсканировал фото "{barcodes_from_img}"')

    if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
        await check_file_exist(file, 'На данном фото <b><u>не найдено</u></b> штрихкодов\nПришлите новое фото или напишите цифры штрихкода', bot, message)
        return
    elif len(barcodes_from_img) > 1:
        await check_file_exist(file, 'На данном фото найдено <b><u>несколько</u></b> штрихкодов\nПришлите новое фото или напишите цифры штрихкода', bot, message)
        return

    if os.path.exists(file):
        await asyncio.sleep(0.20)
        os.remove(file)

    await state.update_data(barcode=barcodes_from_img[0])
    await state.set_state(ChangePrice.price)
    await message.answer('Напишите цену товара')



async def final(message: Message, state: FSMContext):
    price = message.text
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    if re.findall(',', message.text):
        price = price.replace(',', '.')

    check_price = price.replace('.', '')
    if not check_price.isdecimal():
        log.error(f'Цена не только из цифр "{price}"')
        await message.answer(texts.error_price_not_decimal)
        return
    log.info(f'Ввели цену товаров "{price}"')
    await state.set_state(ChangePrice.final)
    data = await state.get_data()
    bcode, cash, ip = data['barcode'], data['cash'], data['ip']
    try:
        create_barcode(bcode=bcode, cash_number=cash, price=price, status='setprice')
        await update_price_in_cash(ip, cash)
        log.success('Цена изменена')
        await message.answer(f'Изменили цену штрихкода "{bcode}" на "{price}"')
    except sqlalchemy.exc.OperationalError as ex:
        log.error('Касса не в сети')
        log.exception(ex)
        await message.answer(texts.error_head + 'К сожалению, в данный момент нет соединения с кассой. '
                                                'Штрихкоды не могут быть загружены. '
                                                'Пожалуйста, проверьте ваше интернет-соединение. '
                                                'Штрихкоды будут загружены автоматически через 5 минут после восстановления связи',
                             reply_markup=getKeyboard_tehpod_url())
