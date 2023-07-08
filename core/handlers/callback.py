import re
from aiogram import Bot
from aiogram.types import CallbackQuery, InputMediaPhoto

from core.database.query_BOT import delete_cash_from_whitelist
from core.keyboards import inline, reply
from core.utils.callbackdata import *
from core.database import query_BOT
from core.utils import texts
from loguru import logger




async def delete_from_whitelist(call: CallbackQuery, callback_data: DeleteCashFromWhitelist):
    log = logger.bind(first_name=call.message.chat.first_name, chat_id=call.message.chat.id)
    await delete_cash_from_whitelist(callback_data.cash)
    await call.message.edit_text(f'Комп "{callback_data.cash.split("-")[1]}" успешно удалён из белого списка')
    log.success(f'Комп "{callback_data.cash}" успешно удалён из белого списка')