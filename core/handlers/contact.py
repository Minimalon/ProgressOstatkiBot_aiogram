from aiogram import Bot
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger

from core.database import botDB
from core.utils import texts
from core.keyboards.reply import getKeyboard_registration
from core.keyboards.inline import getKeyboard_startMenu


async def get_true_contact(message: Message, bot: Bot):
    phone = texts.phone(message.contact.phone_number)
    chat_id = message.chat.id
    first_name = message.contact.first_name
    last_name = message.contact.last_name
    user_id = message.contact.user_id
    q = await botDB.get_client_info(chat_id=chat_id)
    if not q:
        await botDB.update_client_info(phone_number=phone, chat_id=chat_id, first_name=first_name, last_name=last_name, user_id=user_id)
        await bot.send_message(chat_id, texts.succes_registration, reply_markup=ReplyKeyboardRemove())
        await message.answer(texts.menu, reply_markup=getKeyboard_startMenu())
        logger.bind(chat_id=chat_id).success('Успешная регистрация')
    else:
        await message.answer(texts.menu, reply_markup=getKeyboard_startMenu())



async def get_fake_contact(message: Message):
    phone = texts.phone(message.contact.phone_number)
    log = logger.bind(chat_id=message.chat.id, first_name=message.chat.first_name, phone=phone)
    log.error('Отправили чужой сотовый')
    await message.answer(texts.error_fake_client_phone, reply_markup=getKeyboard_registration(), parse_mode='HTML')
