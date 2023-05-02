from aiogram.filters import BaseFilter
from aiogram.types import Message
from loguru import logger


class IsTrueContact(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        log = logger.bind(chat_id=message.chat.id, first_name=message.chat.first_name)

        if message.contact.user_id == message.from_user.id:
            log.info(f"Отправил свой сотовый '{message.contact.phone_number}'")
            return True
        else:
            log.debug(f"Отправил не свой сотовый '{message.contact.phone_number}'")
            return False
