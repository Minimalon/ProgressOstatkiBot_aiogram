from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat


async def get_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Главное меню'
        ),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

async def get_admin_commands(bot: Bot):
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
