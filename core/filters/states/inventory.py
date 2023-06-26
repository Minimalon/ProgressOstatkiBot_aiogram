import asyncio
import re
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from core.keyboards.inline import getKeyboard_end_inventory, getKeyboard_detailed_inventory
from core.utils import texts
from core.utils.anticontrafact import Anticontrafact
from core.utils.states import Inventory

anti_api = Anticontrafact()
lock = asyncio.Lock()


# async def get_bottles(bottles):
#     if bottles is None:
#         return
#     bottle = namedtuple('bottle', 'name amarks')
#     result = []
#     for name, amarks in bottles:
#         result.append(bottle(name, amarks))
#     return result

async def wait_busy(state: FSMContext):
    data = await state.get_data()
    if data.get('busy'):
        while True:
            await asyncio.sleep(0.5)
            data = await state.get_data()
            if not data.get('busy'):
                break
    await state.update_data(busy=True)


async def start_inventory(call: CallbackQuery, state: FSMContext):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    data = await state.get_data()
    log.info('Нажали кнопку "Начать сканирование"')
    bottles = data.get('bottles')
    await state.set_state(Inventory.scaning)
    if bottles:
        await call.message.answer(texts.scanning_inventory(bottles), reply_markup=getKeyboard_end_inventory())
    else:
        await call.message.answer("Можете начинать сканирование. Вам достаточно в чат с ботом отсканировать акцизную марку")
    await call.answer()


async def message_inventory(message: Message, state: FSMContext):
    # await wait_busy(state)
    async with lock:
        log = logger.bind(first_name=message.chat.first_name, chat_id=message.chat.id)
        data = await state.get_data()
        bottles = data.get('bottles')
        marks = message.text.split()
        log.info(f'Написали марку(-и) "{marks}"')

        if bottles is None:
            bottles = []

        accept_amarks = []
        for mark in marks:
            match = 0
            if re.findall('^[0-9]{8,9}$', mark) or re.findall('^[A-Z0-9]{150}$', mark) or re.findall('^[A-Z0-9]{68}$', mark):
                if bottles:
                    for amark in bottles:
                        if mark == amark or re.findall(mark, amark):
                            await message.reply(texts.error_head + f"Данная марка уже была отсканирована ранее")
                            match += 1
            else:
                await message.reply(texts.error_head + 'Данная марка не засчитана\nПопробуйте снова отсканировать <b><u>Акцизную марку</u></b>')
                match += 1

            if match == 0:
                accept_amarks.append(mark)

        if len(accept_amarks) == 0:
            await state.update_data(busy=False)
            return

        for amark in accept_amarks:
            bottles.append(amark)

        await message.answer(texts.scanning_inventory(bottles), reply_markup=getKeyboard_end_inventory())
        await state.update_data(bottles=bottles, busy=False)


async def detailed_inventory(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Загрузка данных в процессе. Пожалуйста, подождите около 1 минуты.")
    data = await state.get_data()
    bottles = await anti_api.new_bottles_tuple(data['bottles'])
    await call.message.edit_text(texts.detailed_inventory(bottles), reply_markup=getKeyboard_detailed_inventory())
