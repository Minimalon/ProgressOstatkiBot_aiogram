#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-
import asyncio
import aiogram.exceptions
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage

from core.handlers import basic, contact
from core.filters.states import ostatki, TTNS
from core.filters.iscontact import IsTrueContact
from core.utils.callbackdata import *
from core.filters.states.ostatki import *
from core.utils.states import *
from core.utils.commands import get_commands


@logger.catch()
async def start():
    if not os.path.exists(os.path.join(config.dir_path, 'logs')):
        os.makedirs(os.path.join(config.dir_path, 'logs'))
    logger.add(os.path.join(config.dir_path, 'logs', 'debug.log'),
               format="{time} | {level} | {name}:{function}:{line} | {message} | {extra}", )

    bot = Bot(token=config.token, parse_mode='HTML')
    await get_commands(bot)
    # storage = RedisStorage.from_url(config.redisStorage)
    # dp = Dispatcher(storage=storage)
    dp = Dispatcher()

    # Калбэки с прошлого бота для регистрации
    dp.callback_query.register(basic.get_start_callback, F.data == 'cb_last_ostatki')
    dp.callback_query.register(basic.get_start_callback, F.data == 'cb_list_ostatki')

    # COMMANDS
    dp.message.register(basic.get_start, Command(commands=['start']))
    dp.message.register(basic.my_id, Command(commands=['id']))

    # CONTACT REGISTRATION
    dp.message.register(contact.get_true_contact, F.contact, IsTrueContact())
    dp.message.register(contact.get_fake_contact, F.contact)

    # OSTATKI
    dp.callback_query.register(ostatki.enter_cash_number, F.data == 'ostatki')
    # OSTATKI STATES
    dp.message.register(ostatki.choose_entity, StateOstatki.choose_entity)
    # OSTATKI MENU
    dp.callback_query.register(ostatki.choose_ostatki_menu, Ostatki.filter())
    dp.callback_query.register(ostatki.push_last_ostatki, OstatkiLast.filter())
    dp.callback_query.register(ostatki.choose_list_ostatki, OstatkiList.filter())
    dp.callback_query.register(ostatki.push_list_ostatki, OstatkiChooseList.filter())

    # TTNS
    dp.callback_query.register(TTNS.enter_cash_number, F.data == 'WayBills')
    # TTNS STATES
    dp.message.register(TTNS.choose_entity, StateTTNs.choose_entity)
    dp.callback_query.register(TTNS.enter_inn, TTNSChooseEntity.filter())
    dp.message.register(TTNS.menu_ttns, StateTTNs.menu_ttns)
    # TTNS MENU
    dp.callback_query.register(TTNS.choose_accept_ttns, F.data == 'accept_ttns')
    # TTNS ACCEPT
    dp.callback_query.register(TTNS.start_accept_ttns, AcceptTTN.filter())
    dp.message.register(TTNS.mediagroup_accept_ttns, StateTTNs.accept_ttn, F.media_group_id, F.photo)
    dp.message.register(TTNS.photo_accept_ttns, StateTTNs.accept_ttn, F.photo)
    dp.message.register(TTNS.document_accept_ttn, StateTTNs.accept_ttn, F.document)
    dp.message.register(TTNS.message_accept_ttns, StateTTNs.accept_ttn)
    dp.callback_query.register(TTNS.send_accept_ttn, SendAcceptTTN.filter())
    # TTNS DIVIRGENCE
    dp.callback_query.register(TTNS.choose_divirgence_ttn, F.data == 'choose_divergence_ttn')
    dp.callback_query.register(TTNS.send_divirgence_ttn, F.data == 'send_divergence_ttn')
    dp.callback_query.register(TTNS.back_to_accept_ttn, F.data == 'cancel_divergence_ttn')
    # TTNS LIST
    dp.callback_query.register(TTNS.choose_list_ttns, F.data == 'list_ttns')
    dp.callback_query.register(TTNS.info_ttn, ListTTN.filter())
    dp.callback_query.register(TTNS.menu_back_ttns, F.data == 'menu_ttns')  # Кнопка "Назад"

    try:
        await dp.start_polling(bot)
    except aiogram.exceptions.TelegramNetworkError:
        dp.callback_query.register(basic.get_start)
    except Exception as e:
        logger.exception(e)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(start())
