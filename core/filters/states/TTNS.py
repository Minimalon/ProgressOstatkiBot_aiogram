import asyncio

import os
import re
from collections import namedtuple
from typing import List
import httpx
from aiogram import Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from loguru import logger
from pyzbar import pyzbar
import cv2
from aiogram_media_group import media_group_handler
import socket
import paramiko
from bs4 import BeautifulSoup

import config
from core.database import query_PROGRESS
from core.database.query_BOT import add_client_cashNumber, get_client_info, check_cash_in_whitelist, check_inn_in_blacklist
from core.keyboards.inline import *
from core.utils import texts
from core.utils.states import StateTTNs
from core.utils.UTM import UTM
from core.utils.callbackdata import ChooseEntity, AcceptTTN, SendAcceptTTN

lock = asyncio.Lock()


async def read_barcodes_from_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    barcodes = pyzbar.decode(image)
    barcode_data_list = []
    for barcode in barcodes:
        barcode_data = barcode.data.decode('utf-8')
        barcode_data_list.append(barcode_data)
    return barcode_data_list


async def menu_back_ttns(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    data = await state.get_data()
    log.info('Нажали кнопку "Назад"')
    if await check_inn_in_blacklist(data['inn']):
        if await check_cash_in_whitelist(data['cash']):
            await call.message.answer(texts.WayBills, reply_markup=getKeyboard_menu_ttns())
        else:
            await call.message.answer(texts.WayBills_blacklist, reply_markup=getKeyboard_menu_ttns_who_in_blacklist())
    else:
        await call.message.answer(texts.WayBills, reply_markup=getKeyboard_menu_ttns())


async def choose_accept_ttns(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Нажали "Приём ТТН"')
    state_data = await state.get_data()
    utm = UTM(ip=state_data.get("ip"), port=state_data.get("port"))
    if not utm:
        await call.message.edit_text(texts.error_head + "УТМ не работает. Обратитесь в тех.поддержку", reply_markup=getKeyboard_tehpod_url())
        return
    ttns = await utm.get_Waybill_and_FORM2REGINFO()
    if not ttns:
        await call.message.edit_text(texts.error_head + 'Не найдено накладных для подтверждения\n'
                                                        'Можете обратиться в тех.поддержку', reply_markup=getKeyboard_tehpod_url())
        return
    await call.message.edit_text('Выберите накладную', reply_markup=getKeyboard_choose_ttn(ttns), parse_mode='HTML')


async def start_accept_ttns(call: CallbackQuery, state: FSMContext, callback_data: AcceptTTN, bot: Bot):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info(f'Выбрали накладную "{callback_data.ttn}"')
    data = await state.get_data()
    id_f2r = callback_data.id_f2r
    id_wb = callback_data.id_wb
    ttn_egais = callback_data.ttn.split('-')[1]
    url_utm = f'http://{data.get("ip")}:{data.get("port")}/opt/out'
    url_f2r, url_wb = f'{url_utm}/{id_f2r}', f'{url_utm}/{id_wb}'
    utm = UTM(ip=data.get('ip'), port=data.get('port'))
    beer_ttn = await utm.check_beer_waybill(url_wb, data.get('port'))
    if beer_ttn:
        log.debug("Пивная накладная")
        await state.update_data(ttn_egais=ttn_egais, id_f2r=id_f2r, id_wb=id_wb, busy=False)
        await call.message.edit_text(texts.beer_accept_text(beer_ttn), reply_markup=getKeyboard_accept_beer_ttn(await state.get_data()))
    else:
        log.debug("Алкогольная накладная")
        if not os.path.exists(os.path.join(config.dir_path, 'files', 'boxnumbers')):
            os.makedirs(os.path.join(config.dir_path, 'files', 'boxnumbers'))
        boxs = await utm.get_box_info_from_Waybill(url_wb)
        await state.update_data(ttn_egais=ttn_egais, boxs=boxs, id_f2r=id_f2r, id_wb=id_wb)
        await call.message.delete()
        text = '➖➖➖➖ℹ️<b><u>Инструкция</u></b>ℹ️➖➖➖➖\n' \
               'Для приема ТТН отправьте фото штрих-кодов с коробок, либо ввидите штрих-код текстом. Можно отправлять по одному, либо сразу несколько фото.\n' \
               'Пример фото:'
        await bot.send_photo(call.message.chat.id, FSInputFile(os.path.join(config.dir_path, 'files', 'startAccept.jpg')), caption=text)
        await bot.send_message(call.message.chat.id, texts.accept_text(boxs), reply_markup=getKeyboard_accept_ttn(await state.get_data()))
        logger.info(await state.get_data())
        await state.set_state(StateTTNs.accept_ttn)


async def check_file_exist(file, msg, bot: Bot, message: Message):
    log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
    if os.path.exists(file):
        await bot.send_photo(message.chat.id, photo=FSInputFile(file), caption=msg)
        log.debug(msg)
        await asyncio.sleep(0.20)
        os.remove(file)


async def wait_busy(state: FSMContext):
    data = await state.get_data()
    if data.get('busy'):
        while True:
            await asyncio.sleep(0.05)
            data = await state.get_data()
            if not data.get('busy'):
                break
    await state.update_data(busy=True)


async def get_boxs(boxs):
    """
    :param boxs: Коробки
    :return: [namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned'), ...]
    """
    boxinfo = namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned')
    result = []
    for name, capacity, boxnumber, count_bottles, amarks, scaned in boxs:
        result.append(boxinfo(name, capacity, boxnumber, count_bottles, amarks, scaned))
    return result


async def message_accept_ttns(message: Message, state: FSMContext, bot: Bot):
    async with lock:
        log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
        data = await state.get_data()
        messages = message.text.split()
        log.info(f'Написали штрихкод(-а) "{messages}"')
        boxs = await get_boxs(data.get('boxs'))
        result = [box for box in boxs if box.scaned]
        new_boxs = namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned')

        barcodes = []
        for bcode in messages:
            match = 0
            if re.findall('^[0-9]{8,9}$', bcode) or re.findall('^[A-Z0-9]{150}$', bcode) or re.findall('^[A-Z0-9]{68}$', bcode):
                for pos in result:
                    for mark in pos.amarks:
                        if re.findall(bcode, mark):
                            match += 1
                            log.debug(f'Данная акцизка "{bcode}" уже принята')
                            await bot.send_message(message.chat.id,
                                                   texts.error_head + f'Данная акцизная марка "<code>{bcode}</code>" уже принята. Отправьте другую акцизную марку')
                            break
                if match == 0:
                    barcodes.append(bcode)
            elif re.findall('^[0-9]{26,28}$', bcode):
                if bcode not in (b.boxnumber for b in boxs) and match:
                    text = texts.error_head + f'Данной коробки <code>"{bcode}"</code> не найдено в накладной'
                    await bot.send_message(message.chat.id, text)
                    log.debug(f'Данной коробки "{bcode}" не найдено в накладной')
                elif bcode in (b.boxnumber for b in result) and not match:
                    text = texts.error_head + f'Вы уже отправляли данную коробку\n"<code>{str(bcode).strip()}</code>"'
                    await bot.send_message(message.chat.id, text)
                    log.debug(f'Вы уже отправляли данную коробку "{bcode}"')
                else:
                    log.debug(f'Отправили коробку {bcode}')
                    barcodes.append(bcode)
            else:
                await bot.send_message(message.chat.id, texts.error_head + f'Данная позиция "<code>{bcode}</code>" не коробка, и не акцизная марка. Попробуйте снова')
        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return
        for box in boxs:
            match = 0
            for barcode in barcodes:
                if re.findall('^[0-9]{8,9}$', barcode) or re.findall('^[A-Z0-9]{150}$', barcode) or re.findall('^[A-Z0-9]{68}$', barcode):
                    for amark in box.amarks:
                        if re.findall(barcode, amark):
                            match += 1
                            log.info(f'Принял акцизу {barcode}')
                            result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, True))
                elif barcode == box.boxnumber:
                    match += 1
                    log.info(f'Принял коробку {barcode}')
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, True))
            if match == 0:
                if box.boxnumber not in [b.boxnumber for b in result]:
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, False))
                    continue

        await state.update_data(busy=False, boxs=result)
        state_info = await state.get_data()
        box_scaned = [box for box in result if box.scaned]
        log.info(f'Принято {len(box_scaned)}/{len(result)}')
        await message.answer(texts.accept_text(result), reply_markup=getKeyboard_accept_ttn(state_info))


@media_group_handler
async def mediagroup_accept_ttns(messages: List[Message], state: FSMContext, bot: Bot):
    async with lock:
        data = await state.get_data()
        chat_id = messages[0].chat.id
        log = logger.bind(first_name=messages[0].chat.first_name, chat_id=chat_id)
        boxs = await get_boxs(data.get('boxs'))
        barcodes = []
        result = [box for box in boxs if box.scaned]
        barcode_path = os.path.join(config.dir_path, 'files', 'boxnumbers', str(chat_id))
        boxsnumbers = [box.boxnumber for box in boxs]

        for message in messages:
            file = await bot.get_file(message.photo[-1].file_id)

            if not os.path.exists(barcode_path):
                os.mkdir(barcode_path)

            file_path = os.path.join(barcode_path, f'barcode_{message.message_id}.jpg')
            await bot.download_file(file.file_path, file_path)
        for file in os.listdir(barcode_path):
            file = os.path.join(barcode_path, file)
            try:
                barcodes_from_img = await read_barcodes_from_image(file)
                log.info(f'Отсканировал фото "{barcodes_from_img}"')

                if len(barcodes_from_img) > 0:
                    for bcode in barcodes_from_img:
                        if bcode not in [b.boxnumber for b in result]:
                            barcodes.append(bcode)
                        else:
                            text = texts.error_head + f'Вы уже отправляли данную коробку\n"<code>{str(bcode).strip()}</code>"'
                            await bot.send_message(messages[0].chat.id, text)
                            log.debug(f'Вы уже отправляли данную коробку "{bcode}"')
                else:
                    await check_file_exist(file, 'На данном фото <b><u>не найдено</u></b> штрихкодов', bot, messages[0])

                match = 0
                for bcode in barcodes_from_img:
                    if bcode in boxsnumbers:
                        match += 1
                if match == 0:
                    text = f'Данной коробки <code>"{barcodes_from_img}"</code> не найдено в накладной'
                    await check_file_exist(file, text, bot, messages[0])

                if os.path.exists(file):
                    await asyncio.sleep(0.20)
                    os.remove(file)
            except TypeError:
                logger.debug(f'TypeError: {file}')
            except FileNotFoundError:
                log.debug(f'Файл не найден "{file}"')
            except PermissionError:
                log.debug(f'Файл занят другим процессом "{file}"')

        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return
        barcodes = list(set(barcodes))
        log.debug(f'Нашел коробки "{barcodes}"')
        new_boxs = namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned')

        for box in boxs:
            match = 0
            for barcode in barcodes:
                if barcode == box.boxnumber:
                    match += 1
                    log.info(f'Принял коробку {barcode}')
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, True))
                    barcodes.remove(barcode)

            if match == 0:
                if box.boxnumber not in [b.boxnumber for b in result]:
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, False))

        await state.update_data(busy=False, boxs=result)
        state_info = await state.get_data()
        box_scaned = [box for box in result if box.scaned]
        log.info(f'Принято {len(box_scaned)}/{len(result)}')
        await bot.send_message(messages[0].chat.id, texts.accept_text(result), reply_markup=getKeyboard_accept_ttn(state_info))


async def photo_accept_ttns(message: Message, state: FSMContext, bot: Bot):
    async with lock:

        chat_id = message.chat.id
        data = await state.get_data()
        log = logger.bind(first_name=message.chat.first_name, chat_id=chat_id)

        # Коробки
        boxs = await get_boxs(data.get('boxs'))
        boxsnumbers = [box.boxnumber for box in boxs]
        result = [box for box in boxs if box.scaned]
        barcodes = []

        # Качаем фотку и сохраняем в папку, название папки = айди чата
        barcode_path = os.path.join(config.dir_path, 'files', 'boxnumbers', str(chat_id))
        img = await bot.get_file(message.photo[-1].file_id)
        if not os.path.exists(barcode_path):
            os.mkdir(barcode_path)
        file = os.path.join(barcode_path, f'barcode_{message.message_id}.jpg')
        await bot.download_file(img.file_path, file)

        try:
            barcodes_from_img = await read_barcodes_from_image(file)
            log.info(f'Отсканировал фото "{barcodes_from_img}"')

            if len(barcodes_from_img) > 0:  # Если нашлись штрихкода в картинке
                for bcode in barcodes_from_img:
                    if bcode not in [b.boxnumber for b in result]:  # Если найденно шк нет в уже принятых коробках
                        barcodes.append(bcode)
                    else:
                        text = texts.error_head + f'Вы уже отправляли данную коробку\n"<code>{str(bcode).strip()}</code>"'
                        await bot.send_message(message.chat.id, text)
                        log.debug(f'Вы уже отправляли данную коробку "{bcode}"')
            else:
                await check_file_exist(file, 'На данном фото <b><u>не найдено</u></b> штрихкодов', bot, message)

            match = 0
            for bcode in barcodes_from_img:  # Проверяю найденный шк с коробками из накладной
                if bcode in boxsnumbers:
                    match += 1
            if match == 0:
                text = f'Данной коробки <code>"{barcodes_from_img}"</code> не найдено в накладной'
                await check_file_exist(file, text, bot, message)

            if os.path.exists(file):
                await asyncio.sleep(0.20)
                os.remove(file)
        except TypeError:
            logger.debug(f'TypeError: {file}')
        except FileNotFoundError:
            log.debug(f'Файл не найден "{file}"')
        except PermissionError:
            log.debug(f'Файл занят другим процессом "{file}"')

        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return
        barcodes = list(set(barcodes))
        log.debug(f'Нашел коробки "{barcodes}"')
        new_boxs = namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned')

        for box in boxs:
            match = 0
            for barcode in barcodes:
                if barcode == box.boxnumber:
                    match += 1
                    log.info(f'Принял коробку {barcode}')
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, True))
                    barcodes.remove(barcode)

            if match == 0:
                if box.boxnumber not in [b.boxnumber for b in result]:
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, False))

        await state.update_data(busy=False, boxs=result)
        state_info = await state.get_data()
        box_scaned = [box for box in result if box.scaned]
        log.info(f'Принято {len(box_scaned)}/{len(result)}')
        await bot.send_message(message.chat.id, texts.accept_text(result), reply_markup=getKeyboard_accept_ttn(state_info))


async def document_accept_ttn(message: Message, state: FSMContext, bot: Bot):
    async with lock:

        data = await state.get_data()

        chat_id = message.chat.id
        log = logger.bind(first_name=message.chat.first_name, chat_id=chat_id)

        # Коробки
        boxs = await get_boxs(data.get('boxs'))
        boxsnumbers = [box.boxnumber for box in boxs]
        result = [box for box in boxs if box.scaned]
        barcodes = []

        # Качаем фотку и сохраняем в папку, название папки = айди чата
        barcode_path = os.path.join(config.dir_path, 'files', 'boxnumbers', str(chat_id))
        img = await bot.get_file(message.document.file_id)
        if not os.path.exists(barcode_path):
            os.mkdir(barcode_path)
        file = os.path.join(barcode_path, f'barcode_{message.message_id}.jpg')
        await bot.download_file(img.file_path, file)
        try:
            barcodes_from_img = await read_barcodes_from_image(file)
            log.info(f'Отсканировал фото "{barcodes_from_img}"')

            if len(barcodes_from_img) > 0:  # Если нашлись штрихкода в картинке
                for bcode in barcodes_from_img:
                    if bcode not in [b.boxnumber for b in result]:  # Если найденно шк нет в уже принятых коробках
                        barcodes.append(bcode)
                    else:
                        text = texts.error_head + f'Вы уже отправляли данную коробку\n"<code>{str(bcode).strip()}</code>"'
                        await bot.send_message(message.chat.id, text)
                        log.debug(f'Вы уже отправляли данную коробку "{bcode}"')
            else:
                await check_file_exist(file, 'На данном фото <b><u>не найдено</u></b> штрихкодов', bot, message)

            match = 0
            for bcode in barcodes_from_img:  # Проверяю найденный шк с коробками из накладной
                if bcode in boxsnumbers:
                    match += 1
            if match == 0:
                text = f'Данной коробки <code>"{barcodes_from_img}"</code> не найдено в накладной'
                await check_file_exist(file, text, bot, message)

            if os.path.exists(file):
                await asyncio.sleep(0.20)
                os.remove(file)
        except TypeError:
            logger.debug(f'TypeError: {file}')
        except FileNotFoundError:
            log.debug(f'Файл не найден "{file}"')
        except PermissionError:
            log.debug(f'Файл занят другим процессом "{file}"')

        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return
        barcodes = list(set(barcodes))
        log.debug(f'Нашел коробки "{barcodes}"')
        new_boxs = namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned')

        for box in boxs:
            match = 0
            for barcode in barcodes:
                if barcode == box.boxnumber:
                    match += 1
                    log.info(f'Принял коробку {barcode}')
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, True))
                    barcodes.remove(barcode)

            if match == 0:
                if box.boxnumber not in [b.boxnumber for b in result]:
                    result.append(new_boxs(box.name, box.capacity, box.boxnumber, box.count_bottles, box.amarks, False))

        await state.update_data(busy=False, boxs=result)
        state_info = await state.get_data()
        box_scaned = [box for box in result if box.scaned]
        log.info(f'Принято {len(box_scaned)}/{len(result)}')
        await bot.send_message(message.chat.id, texts.accept_text(result), reply_markup=getKeyboard_accept_ttn(state_info))


async def send_accept_ttn(call: CallbackQuery, state: FSMContext, callback_data: SendAcceptTTN):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Нажали "Принять накладную"')
    try:
        await call.message.edit_text('Идёт процесс потдверждения накладной. Загрузка займет не дольше 1-ой минуты')
        state_info = await state.get_data()
        url = f'http://{state_info.get("ip")}:{state_info.get("port")}/opt/out'
        url_f2r = f'{url}/FORM2REGINFO/{state_info.get("id_f2r")}'
        url_wb = f'{url}/WayBill_v4/{state_info.get("id_wb")}'
        utm = UTM(ip=state_info.get('ip'), port=state_info.get('port'))
        boxs = await get_boxs(state_info.get('boxs'))
        cash = state_info.get('cash').split('-')[1]

        response = await utm.send_WayBillv4(callback_data.ttn)
        log.info(f'response = {response.status_code}')
        if response.status_code == 200:
            await utm.add_to_whitelist(url_wb, boxs, cash)
            async with httpx.AsyncClient() as client:
                await client.delete(url_f2r)
                await client.delete(url_wb)
            log.success(f'Приняли накладную "{callback_data.ttn}"')
            await call.message.edit_text("✅Акт потдверждения накладной успешно отправлен\n"
                                         "Накладная будет принята в течении 5 минут")
            await state.clear()
        else:
            log.error(f'Накладная не принята "{callback_data.ttn}". Код ошибки "{response.status_code}"')
            text = texts.error_head + f'Попробуйте еще раз подтвердить накладную. Код ошибки "{response.status_code}"'
            await call.message.answer(text, reply_markup=getKeyboard_tehpod_url())
    except Exception as e:
        log.exception(e)
        await call.message.edit_text(texts.error_head + e)


async def choose_divirgence_ttn(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(StateTTNs.choose_divirgence_ttn)
    data = await state.get_data()
    text = texts.divirgence_text(await get_boxs(data.get('boxs')))
    await call.message.edit_text(text)
    text = ('Акт расхождения - это частичное подтвеждение накладной\n'
            'Вы уверены что хотите отправить акт расхождения?')
    await bot.send_message(call.message.chat.id, text, reply_markup=getKeyboard_choose_divirgence_ttn())


async def send_divirgence_ttn(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Отправили акт расхождения')
    try:
        await call.message.edit_text("Идёт процесс отправки накладной. Загрузка займёт не дольше 1-ой минуты")
        state_info = await state.get_data()
        utm = UTM(ip=state_info.get('ip'), port=state_info.get('port'))
        url = f'http://{state_info.get("ip")}:{state_info.get("port")}/opt/out'
        url_f2r = f'{url}/FORM2REGINFO/{state_info.get("id_f2r")}'
        url_wb = f'{url}/WayBill_v4/{state_info.get("id_wb")}'
        ttn_egais = state_info.get('ttn_egais')
        response = await utm.send_divirgence_ttn(url_wb, url_f2r, await get_boxs(state_info.get('boxs')), ttn_egais)
        if response.status_code == 200:
            await utm.add_to_whitelist(url_wb, await get_boxs(state_info.get('boxs')), state_info.get('cash').split('-')[1])
            async with httpx.AsyncClient() as client:
                await client.delete(url_f2r)
                await client.delete(url_wb)
            log.success(f'Акт расхождения успешно отправлен "{ttn_egais}"')
            await call.message.edit_text("✅Акт расхождения успешно отправлен\n")
            await state.clear()
        else:
            log.error(f'Накладная не принята "{ttn_egais}". Код ошибки "{response.status_code}"')
            text = texts.error_head + f'Попробуйте еще раз отправить акт расхождения. Код ошибки "{response.status_code}"'
            await call.message.answer(text, reply_markup=getKeyboard_tehpod_url())
    except Exception as e:
        log.exception(e)
        await call.message.edit_text(texts.error_head + e)


async def back_to_accept_ttn(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    data = await state.get_data()
    boxs = await get_boxs(data.get('boxs'))
    log.info('Нажали "Нет" при отправке акта расхождения')
    await call.message.edit_text(texts.accept_text(boxs), reply_markup=getKeyboard_accept_ttn(await state.get_data()))
    await state.set_state(StateTTNs.accept_ttn)


async def choose_list_ttns(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    data = await state.get_data()
    ttnload = 'ttnload2' if data.get('port') == "18082" else "ttnload"
    log.info(f'Cписок накладных из "{ttnload}"')
    ttns_info = []
    client = paramiko.SSHClient()
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=data.get('ip'), username=config.user_ssh, password=config.password_ssh, port=config.port_ssh, timeout=5)
        stdin, stdout, stderr = client.exec_command(f'find /root/{ttnload}/TTN -name WayBill_v* | sort | tail -n10')
        if stderr.read():
            await call.message.answer(texts.error_head + stderr.read().decode('utf-8'), reply_markup=getKeyboard_tehpod_url())
            return
        ttns_path = stdout.read().split()
        for ttn in ttns_path:
            ttn_egais = ttn.decode('utf-8').split('/')[4]
            stdin, stdout, stderr = client.exec_command(f'cat {ttn.decode("utf-8")}')
            tree = BeautifulSoup(stdout.read(), 'xml').Documents.Document.WayBill_v4
            shipper_name = tree.Header.Shipper.UL.ShortName.text
            date = tree.Header.Date.text
            wbnumber = tree.Header.NUMBER.text
            ttns_info.append([date, wbnumber, shipper_name, ttn_egais])
    except socket.timeout as e:
        await call.message.answer(texts.error_head + "Компьютер не в сети. Возможно он выключен, или нет интернета.", reply_markup=getKeyboard_tehpod_url())
        return
    finally:
        client.close()
    log.info(f'Вывел накладные "{ttns_info}"')
    await call.message.edit_text("Выберите накладную", reply_markup=getKeyboard_choose_list_ttn(ttns_info, ttnload))


async def info_ttn(call: CallbackQuery, state: FSMContext, callback_data: ListTTN):
    data = await state.get_data()
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    ttnload, ttn_egais = callback_data.ttnload, callback_data.ttn_e
    log.info(f"Выбрали накладную '{ttn_egais}' из папки '{ttnload}'")
    client = paramiko.SSHClient()
    ttn_path = f'/root/{ttnload}/TTN/{ttn_egais}'
    text = 'ℹ️Статус накладной️:'
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=data.get('ip'), username=config.user_ssh, password=config.password_ssh, port=config.port_ssh, timeout=5)
        stdin, stdout_wb, stderr = client.exec_command(f'cat {ttn_path}/WayBill_v*')
        if stderr.read():
            await call.message.answer(texts.error_head + stderr.read().decode('utf-8'), reply_markup=getKeyboard_tehpod_url())
            return
        stdin, ls, stderr = client.exec_command(f'ls {ttn_path}')
        stdin, grep, stderr = client.exec_command(f"grep OperationComment {ttn_path}/Ticket.xml | cut -d '<' -f2 | cut -d '>' -f2")
        grep = grep.read().decode('utf-8')
        tree = BeautifulSoup(stdout_wb.read(), 'xml').Documents.Document.WayBill_v4
        if grep:
            if re.findall('подтверждена', grep):
                text += '<b><u>Подтверждена</u></b>✅\n'
            elif re.findall('отменен', grep):
                text += '<b><u>Ожидает действий от получателя</u></b>\n'
            elif re.findall('отозвана', grep):
                text += '<b><u>Поставщик отозвал накладную</u></b>\n'
            elif re.findall('отказана', grep):
                text += '<b><u>Отказана</u></b>❌\n'
            else:
                text += f"<b><u>{grep}</u></b>\n"
        else:
            text += '<b><u>Ожидает действий от получателя</u></b>\n'
        text += f"Поставщик: <code>{tree.Header.Shipper.UL.ShortName.text}</code>\n"
        text += f"Номер накладной: <code>{tree.Header.NUMBER.text}</code>\n"
        text += f"Дата накладной: <code>{tree.Header.Date.text}</code>\n"
        text += f"Номер накладной в ЕГАИС: <code>{ttn_egais}</code>\n"
        text += '➖' * 15 + '\n'
        text += 'Название | Количество\n'
        text += '➖' * 15 + '\n'
        for product in tree.findAll('Position'):
            Fullname = product.find('FullName').text
            shortName = product.find('{http://fsrar.ru/WEGAIS/ProductRef_v2}ShortName').text \
                if product.find('{http://fsrar.ru/WEGAIS/ProductRef_v2}ShortName') \
                else False
            capacity = f"{product.find('Capacity').text[:4]}" if product.find('Capacity') else ''
            quantity = product.find('Quantity').text if product.find('Quantity') else '?'
            if shortName:
                text += f'{shortName} {capacity}л | {quantity} шт\n'
            else:
                text += f'{Fullname} {capacity}л | {quantity} шт\n'
    except socket.timeout as e:
        await call.message.answer(texts.error_head + "Компьютер не в сети. Возможно он выключен, или нет интернета.", reply_markup=getKeyboard_tehpod_url())
        return
    finally:
        client.close()
    await call.answer()
    await call.message.answer(text, reply_markup=getKeyboard_info_ttn())
