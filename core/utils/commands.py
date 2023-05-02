from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def get_commands(bot: Bot):
    commands = [
        BotCommand(
            command='start',
            description='Главное меню'
        ),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
