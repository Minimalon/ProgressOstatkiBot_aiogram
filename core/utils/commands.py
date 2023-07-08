import loguru
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from core.database.query_BOT import get_whitelist_admins


async def get_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Главное меню'
        ),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def get_superadmin_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Главное меню'
        ),
        BotCommand(
            command='clear',
            description='Очистить кеш'
        ),
        BotCommand(
            command='id',
            description='Мой id чата'
        ),
    ]
    await bot.set_my_commands(commands, BotCommandScopeChat(chat_id=5263751490))


async def whitelist_admin_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Главное меню'
        ),
        BotCommand(
            command='/add_comp',
            description='Добавить компьютер в белый список'
        ),
    ]
    w_admins = await get_whitelist_admins()
    for admin in w_admins:
        try:
            await bot.set_my_commands(commands, BotCommandScopeChat(chat_id=admin.chat_id))
            loguru.logger.info(f'Сделал админом белого списка "{admin.chat_id}"')
        except Exception as e:
            loguru.logger.error(f'Не получилось назначить комманды "{admin.chat_id}"')
            loguru.logger.exception(e)
