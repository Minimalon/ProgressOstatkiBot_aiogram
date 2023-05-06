import re
from aiogram import Bot
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger
from core.database import botDB
from core.keyboards import reply
from core.keyboards import inline
from core.utils import texts

async def get_start(message: Message):
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id)
    client_db = await botDB.get_client_info(chat_id=message.chat.id)
    if client_db:
        log.info("Уже зарегестрирован")
        await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu(), parse_mode='HTML')
    else:
        log.error("Нужно пройти регистрацию")
        await message.answer(texts.need_registration, reply_markup=reply.getKeyboard_registration(), parse_mode='HTML')


async def registration(message: Message, bot: Bot):
    client_phone = ''.join(re.findall(r'[0-9]*', message.contact.phone_number))
    log = logger.bind(name=message.chat.first_name, chat_id=message.chat.id, client_phone=client_phone)
    client_db = await botDB.get_client_info(chat_id=message.chat.id)
    if client_db:
        log.info("Есть в БД")
        await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu(), parse_mode='HTML')
    else:
        await botDB.update_client_info(chat_id=message.chat.id, phone_number=client_phone,
                                         first_name=message.contact.first_name, last_name=message.contact.last_name,
                                         user_id=message.contact.user_id)
        await bot.send_message(message.chat.id, 'Регистрация успешна пройдена', reply_markup=ReplyKeyboardRemove())
        log.info("Прошел регистрацию")
        await message.answer(texts.menu, reply_markup=inline.getKeyboard_startMenu(), parse_mode='HTML')

async def my_id(message: Message):
    await message.answer(f'Ваш ID: <code>{message.chat.id}</code>')





