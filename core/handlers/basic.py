import re
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from loguru import logger
from core.database import query_BOT
from core.database.query_BOT import add_cash_in_whitelist, get_client_info
from core.filters.states.logins.loginTTN import check_cash_number
from core.keyboards import reply
from core.keyboards import inline
from core.keyboards.inline import getKeyboard_startMenu
from core.utils import texts
from core.utils.states import AddCashWhitelist


async def get_start(message: Message):
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    client_db = await query_BOT.get_client_info(chat_id=message.chat.id)
    if client_db:
        log.info("Уже зарегестрирован")
        await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu())
    else:
        log.error("Нужно пройти регистрацию")
        await message.answer(texts.need_registration, reply_markup=reply.getKeyboard_registration())

async def get_start_callback(call: CallbackQuery):
    log = logger.bind(name=call.message.chat.first_name, chat_id=call.message.chat.id)
    log.info('Зашел со старого бота')
    client_db = await query_BOT.get_client_info(chat_id=call.message.chat.id)
    if client_db:
        log.info("Уже зарегестрирован")
        await call.message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu())
    else:
        log.error("Нужно пройти регистрацию")
        await call.message.answer(texts.need_registration, reply_markup=reply.getKeyboard_registration())


async def registration(message: Message, bot: Bot):
    client_phone = ''.join(re.findall(r'[0-9]*', message.contact.phone_number))
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id, client_phone=client_phone)
    client_db = await query_BOT.get_client_info(chat_id=message.chat.id)
    if client_db:
        log.info("Есть в БД")
        await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu())
    else:
        await query_BOT.update_client_info(chat_id=message.chat.id, phone_number=client_phone,
                                         first_name=message.contact.first_name, last_name=message.contact.last_name,
                                         user_id=message.contact.user_id)
        await bot.send_message(message.chat.id, 'Регистрация успешна пройдена', reply_markup=ReplyKeyboardRemove())
        log.info("Прошел регистрацию")
        await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu())

async def my_id(message: Message):
    await message.answer(f'Ваш ID: <code>{message.chat.id}</code>')
    await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu())

async def clear(message: Message, state: FSMContext):
    await state.update_data(bottles=None)


async def start_add_cash_in_whitelist(message: Message, state: FSMContext):
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    log.info(f'Нажали команду "{message.text}"')
    client_info = await get_client_info(chat_id=message.chat.id)
    if not client_info.whitelist_admin:
        await message.answer('У вас нет прав доступа к данной команде')
    else:
        await message.answer(texts.enter_cash_number)
        await state.set_state(AddCashWhitelist.enter_cashNumber)


async def end_add_cash_in_whitelist(message: Message, state: FSMContext):
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    log.info(f'Напечатали номер компьютера "{message.text}"')
    cash_info = await check_cash_number(message)
    if not cash_info:
        await message.answer(texts.menu, reply_markup=getKeyboard_startMenu())
        await state.clear()
        return
    await add_cash_in_whitelist(cash_info.name, cash_info.inn)
    await message.answer(f'Компьютер <b>{message.text}</b> успешно добавлен в белый список')
    await state.clear()
    log.success(f'Комп добавлен в белый список "{cash_info.name}"')





