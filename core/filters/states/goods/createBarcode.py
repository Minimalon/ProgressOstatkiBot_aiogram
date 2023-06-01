import asyncio
import os
import re

import sqlalchemy.exc
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from loguru import logger

import config
from core.filters.states.TTNS import read_barcodes_from_image, check_file_exist
from core.keyboards.inline import getKeyboard_select_dcode, getKeyboard_select_measure_alcohol, getKeyboard_select_measure_beer, getKeyboard_select_measure_products, \
    getKeyboard_tehpod_url
from core.utils import texts
from core.utils.callbackdata import SelectDcode, SelectMeasure
from core.utils.generateBarcode import generate_barcode, generate_pdf
from core.utils.states import CreateBarcode
from cron.barcodes import add_barcodes_in_cash


async def select_dcode(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Нажали "Создать штрихкод"')
    await call.message.edit_text("Выберите нужный тип товара", reply_markup=getKeyboard_select_dcode())
    await state.set_state(CreateBarcode.dcode)
    await state.update_data(barcode=None)


async def select_measure(call: CallbackQuery, state: FSMContext, callback_data: SelectDcode):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    await state.set_state(CreateBarcode.measure)
    dcode, op_mode, tmctype = callback_data.dcode, callback_data.op_mode, callback_data.tmctype
    log.info(f'Выбрали dcode={dcode}')
    await state.update_data(dcode=dcode, op_mode=op_mode, tmctype=tmctype)
    if dcode == 1:
        await call.message.edit_text('Выберите вид продажи\n'
                                     '<b><u>Поштучный</u></b> - Алкоголь который будете продавать сканировав акцизную марку\n'
                                     '<b><u>Розлив</u></b> - Алкоголь который продаётся порционно (подойдет для баров)',
                                     reply_markup=getKeyboard_select_measure_alcohol())
    elif dcode == 2:
        await call.message.edit_text('Выберите вид продажи\n'
                                     '<b><u>Поштучный</u></b> - Пиво которое будете продавать целыми бутылками\n'
                                     '<b><u>Розлив</u></b> - Пиво которое продаётся порционно (подойдет для пива которое в кегах)',
                                     reply_markup=getKeyboard_select_measure_beer())
    elif dcode == 3:
        await state.update_data(measure=1)
        await state.set_state(CreateBarcode.barcode)
        await call.message.edit_text('Напишите цифры штрихкода или пришлите фото штрихкода')
    elif dcode == 4:
        await call.message.edit_text('Выберите вид продажи\n'
                                     '<b><u>Поштучный</u></b> - Товар который будет продаваться целиком. Например: хлеб, колбаса)\n'
                                     '<b><u>Весовой</u></b> - Товар который продаётся порционно. Например: Сыр, рыба, орехи',
                                     reply_markup=getKeyboard_select_measure_products())
    elif dcode == 5:
        await state.update_data(measure=1)
        await state.set_state(CreateBarcode.barcode)
        await call.message.edit_text('Напишите цифры штрихкода или пришлите фото штрихкода')


async def accept_measure(call: CallbackQuery, state: FSMContext, callback_data: SelectMeasure):
    log = logger.bind(name=call.message.chat.first_name, chat_id=call.message.chat.id)
    data = await state.get_data()
    measure, op_mode, tmctype, dcode = callback_data.measure, callback_data.op_mode, callback_data.tmctype, data['dcode']
    await state.update_data(measure=measure, op_mode=op_mode, tmctype=tmctype)
    log.info(f"Выбрали measure={measure} op_mode={op_mode} tmctype={tmctype}")
    if (dcode == 1 and tmctype == 1) \
            or (dcode == 2 and measure == 1) \
            or (dcode == 4 and measure == 1):
        await state.set_state(CreateBarcode.barcode)
        await call.message.edit_text('Напишите цифры штрихкода или пришлите фото штрихкода')
    else:
        await state.set_state(CreateBarcode.price)
        await call.message.edit_text('Напишите цену товара')


async def text_barcode(message: Message, state: FSMContext):
    log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
    if not message.text.isdigit():
        log.error(f'Штрихкод состоит не из цифр "{message.text}"')
        await message.answer(texts.error_head + 'Штрихкод состоит только из цифр.\nВведите штрихкод еще раз')
    log.info(f'Написали штрихкод "{message.text}"')
    await state.update_data(barcode=message.text)
    await state.set_state(CreateBarcode.price)
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
    await state.set_state(CreateBarcode.price)
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
    await state.set_state(CreateBarcode.price)
    await message.answer('Напишите цену товара')


async def price(message: Message, state: FSMContext):
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
    await state.update_data(price=price)
    await state.set_state(CreateBarcode.name)
    await message.answer('Напишите название товара')


async def accept_name(message: Message, state: FSMContext, bot: Bot):
    log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
    data = await state.get_data()
    cash_number, op_mode, measure, dcode, tmctype, ip, price = data['cash'], data['op_mode'], data['measure'], data['dcode'], data['tmctype'], data['ip'], data['price']
    names = message.text.split('\n')
    log.info(f'Ввели название товаров "{names}"')
    for name in names:
        try:
            generate_barcode(cash_number=cash_number, name=name, op_mode=op_mode, measure=measure, dcode=dcode, bcode=data.get('barcode'), tmctype=tmctype,
                             price=price)
        except ValueError:
            await message.answer(texts.error_head + f"Слишком длинное название '{name}'\nПопробуйте написать название товара еще раз.")
            log.error(f'Слишком длинное название "{message.text}"')
    path = generate_pdf(cash_number)
    await bot.send_document(message.chat.id, document=FSInputFile(path))
    try:
        await add_barcodes_in_cash(ip, cash_number)
        log.success(f'Успешно {len(names)} штриход(-а)')
        if len(names) == 1:
            await message.answer('Успешно создан 1 штрихкод, через 5 минут он будет загружен на кассу')
        else:
            await message.answer(f'Успешно создано {len(names)} штрихкода(-ов), через 5 минут они будут загружены на кассу')
        await state.clear()
    except sqlalchemy.exc.OperationalError as ex:
        log.exception(ex)
        await message.answer(texts.error_head + 'К сожалению, в данный момент нет соединения с кассой. '
                                                'Штрихкоды не могут быть загружены. '
                                                'Пожалуйста, проверьте ваше интернет-соединение. '
                                                'Штрихкоды будут загружены автоматически через 5 минут после восстановления связи',
                             reply_markup=getKeyboard_tehpod_url())

