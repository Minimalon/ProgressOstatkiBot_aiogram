#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

import asyncio
import aiogram.exceptions
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage

from core.handlers import basic, contact
from core.filters.states import ostatki, TTNS, inventory
from core.filters.states.goods import createBarcode, changePrice
from core.filters.iscontact import IsTrueContact
from core.utils.callbackdata import *
from core.filters.states.ostatki import *
from core.utils.states import *
from core.utils.commands import get_commands, get_superadmin_commands, whitelist_admin_commands
from core.filters.states.logins import loginGoods, loginTTN, loginOstatki, loginInventory


@logger.catch()
async def start():
    if not os.path.exists(os.path.join(config.dir_path, 'logs')):
        os.makedirs(os.path.join(config.dir_path, 'logs'))
    logger.add(os.path.join(config.dir_path, 'logs', 'debug.log'), format="{time} | {level} | {name}:{function}:{line} | {message} | {extra}", )

    bot = Bot(token=config.token, parse_mode='HTML')
    await bot.send_message(5263751490, 'Я Запустился!')
    await get_commands(bot)
    await get_superadmin_commands(bot)
    await whitelist_admin_commands(bot)
    storage = RedisStorage.from_url(config.redisStorage)
    dp = Dispatcher(storage=storage)

    # Калбэки с прошлого бота для регистрации
    dp.callback_query.register(basic.get_start_callback, F.data == 'cb_last_ostatki')
    dp.callback_query.register(basic.get_start_callback, F.data == 'cb_list_ostatki')

    # COMMANDS
    dp.message.register(basic.get_start, Command(commands=['start']))
    dp.message.register(basic.my_id, Command(commands=['id']))
    dp.message.register(basic.clear, Command(commands=['clear']))

    # Команды для админов белого списка
    dp.message.register(basic.start_add_cash_in_whitelist, Command(commands=['add_comp']))


    # Добавление компа в белый список для приёма ТТН
    dp.message.register(basic.end_add_cash_in_whitelist, AddCashWhitelist.enter_cashNumber)

    # CONTACT REGISTRATION
    dp.message.register(contact.get_true_contact, F.contact, IsTrueContact())
    dp.message.register(contact.get_fake_contact, F.contact)
    # OSTATKI
    dp.callback_query.register(loginOstatki.enter_cash_number, F.data == 'ostatki')
    # OSTATKI STATES
    dp.message.register(loginOstatki.choose_entity, StateOstatki.enter_cashNumber)
    dp.callback_query.register(loginOstatki.enter_inn, Ostatki.filter(), StateOstatki.choose_entity)
    dp.message.register(loginOstatki.menu, StateOstatki.inn)
    # OSTATKI MENU
    dp.callback_query.register(ostatki.push_last_ostatki, OstatkiLast.filter())
    dp.callback_query.register(ostatki.choose_list_ostatki, OstatkiList.filter())
    dp.callback_query.register(ostatki.push_list_ostatki, OstatkiChooseList.filter())

    # TTNS
    dp.callback_query.register(loginTTN.enter_cash_number, F.data == 'WayBills')
    # TTNS STATES
    dp.message.register(loginTTN.choose_entity, StateTTNs.enter_cashNumber)
    dp.callback_query.register(loginTTN.enter_inn, ChooseEntity.filter(), StateTTNs.choose_entity)
    dp.message.register(loginTTN.menu_ttns, StateTTNs.inn)
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

# goods
    dp.callback_query.register(loginGoods.enter_cash_number, F.data == 'goods')
    dp.message.register(loginGoods.choose_entity, Goods.enter_cashNumber)
    dp.callback_query.register(loginGoods.enter_inn, ChooseEntity.filter(), Goods.choose_entity)
    dp.message.register(loginGoods.menu_goods, Goods.inn)

    # Создание штрихкода
    dp.callback_query.register(createBarcode.select_dcode, F.data == 'new_barcode')
    dp.callback_query.register(createBarcode.select_measure, SelectDcode.filter())
    dp.callback_query.register(createBarcode.accept_measure, SelectMeasure.filter())
    dp.message.register(createBarcode.photo_barcode, CreateBarcode.barcode, F.photo)
    dp.message.register(createBarcode.document_barcode, CreateBarcode.barcode, F.document)
    dp.message.register(createBarcode.text_barcode, CreateBarcode.barcode)
    dp.message.register(createBarcode.price, CreateBarcode.price)
    dp.message.register(createBarcode.accept_name, CreateBarcode.name)

    # Изменение цены
    dp.callback_query.register(changePrice.send_barcode, F.data == 'new_price_barcode')
    dp.message.register(changePrice.photo_barcode, ChangePrice.barcode, F.photo)
    dp.message.register(changePrice.document_barcode, ChangePrice.barcode, F.document)
    dp.message.register(changePrice.text_barcode, ChangePrice.barcode)
    dp.message.register(changePrice.final, ChangePrice.price)

# inventory
    # логин
    dp.callback_query.register(loginInventory.enter_cash_number, F.data == 'inventory')
    dp.message.register(loginInventory.choose_entity, Inventory.enter_cashNumber)
    dp.callback_query.register(loginInventory.enter_inn, ChooseEntity.filter(), Inventory.choose_entity)
    dp.message.register(loginInventory.menu, Inventory.inn)
    dp.callback_query.register(inventory.start_inventory, F.data == 'start_inventory')
    dp.message.register(inventory.message_inventory, Inventory.scaning)
    dp.callback_query.register(inventory.detailed_inventory, F.data == 'detailed_invetory')





    try:
        await dp.start_polling(bot)
    except aiogram.exceptions.TelegramNetworkError:
        dp.callback_query.register(basic.get_start)
    except Exception as e:
        logger.exception(e)
    finally:
        await bot.send_message(5263751490, 'Я Остановился!!!!')
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(start())
