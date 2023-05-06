from collections import namedtuple

from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.utils.callbackdata import *
from loguru import logger


def getKeyboard_startMenu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Остатки", callback_data='ostatki')
    kb.button(text="Накладные", callback_data='WayBills')
    kb.adjust(2)
    return kb.as_markup()


def getKeyboard_ostatki(inn, fsrar):
    kb = InlineKeyboardBuilder()
    kb.button(text="Последние остатки", callback_data=OstatkiLast(inn=inn, fsrar=fsrar))
    kb.button(text="Список по датам", callback_data=OstatkiList(inn=inn, fsrar=fsrar))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_choose_list_ostatki(list_files: list, inn: str, fsrar: str):
    kb = InlineKeyboardBuilder()
    for file_path, date in list_files:
        kb.button(text=date, callback_data=OstatkiChooseList(file_name=file_path, inn=inn, fsrar=fsrar))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_menu_ttns():
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить накладные", callback_data='accept_ttns')
    kb.button(text="Список", callback_data='list_ttns')
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_tehpod_url():
    kb = InlineKeyboardBuilder()
    kb.button(text="Тех.Поддержка", url='wa.me/79600484366')
    kb.adjust(1)
    return kb.as_markup()


def getKeyboard_ostatki_entity(cash_info):
    kb = InlineKeyboardBuilder()
    try:
        ooo_inn, ooo_name, ooo_fsrar = (cash_info.inn, cash_info.ooo_name, cash_info.fsrar)
    except AttributeError:
        ooo_inn, ooo_name, ooo_fsrar = False, False, False
    try:
        ip_inn, ip_name, ip_fsrar = (cash_info.ip_inn, cash_info.ip_name, cash_info.fsrar2)
    except AttributeError:
        ip_inn, ip_name, ip_fsrar = False, False, False
    if ooo_inn and ooo_fsrar:
        kb.button(text=ooo_name, callback_data=Ostatki(inn=ooo_inn, fsrar=ooo_fsrar))
    if ip_inn and ip_fsrar:
        kb.button(text=ip_name, callback_data=Ostatki(inn=ip_inn, fsrar=ip_fsrar))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_ttns_entity(cash_info, UTM_8082, UTM_18082):
    kb = InlineKeyboardBuilder()
    try:
        ooo_inn, ooo_name, ooo_fsrar = (cash_info.inn, cash_info.ooo_name, cash_info.fsrar)
    except AttributeError:
        ooo_inn, ooo_name, ooo_fsrar = False, False, False
    try:
        ip_inn, ip_name, ip_fsrar = (cash_info.ip_inn, cash_info.ip_name, cash_info.fsrar2)
    except AttributeError:
        ip_inn, ip_name, ip_fsrar = False, False, False
    if ooo_inn and ooo_fsrar and UTM_8082:
        kb.button(text=ooo_name, callback_data=TTNSChooseEntity(inn=ooo_inn, fsrar=ooo_fsrar, port='8082', ip=cash_info.ip))
    if ip_inn and ip_fsrar and UTM_18082:
        kb.button(text=ip_name, callback_data=TTNSChooseEntity(inn=ip_inn, fsrar=ip_fsrar, port='18082', ip=cash_info.ip))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_choose_ttn(TTNs: list):
    kb = InlineKeyboardBuilder()
    for ttn in TTNs:
        kb.button(text=f"{ttn.date} | {ttn.wbnumber} | {ttn.shipper_name}", callback_data=AcceptTTN(id_f2r=ttn.id_f2r, id_wb=ttn.id_wb, ttn=ttn.ttn_egais))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_accept_ttn(state_info):
    def get_boxs(boxs):
        boxinfo = namedtuple('Box', 'name capacity boxnumber count_bottles scaned')
        result = []
        for name, capacity, boxnumber, count_bottles, scaned in boxs:
            result.append(boxinfo(name, capacity, boxnumber, count_bottles, scaned))
        return result

    kb = InlineKeyboardBuilder()
    boxs = get_boxs(state_info.get('boxs'))
    id_f2r = state_info.get('id_f2r')
    id_wb = state_info.get('id_wb')
    ttn_egais = state_info.get('ttn_egais')
    admin = state_info.get('admin')
    scaned = all((box.scaned for box in boxs))
    if scaned:
        kb.button(text="Подтвердить накладную", callback_data=SendAcceptTTN(id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais))
    elif admin and not scaned:
        kb.button(text="Подтвердить накладную", callback_data=SendAcceptTTN(id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais))
        kb.button(text="Отправить акт расхождения", callback_data='choose_divergence_ttn')
    else:
        kb.button(text="Отправить акт расхождения", callback_data='choose_divergence_ttn')
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_accept_beer_ttn(state_info):
    kb = InlineKeyboardBuilder()
    id_f2r = state_info.get('id_f2r')
    id_wb = state_info.get('id_wb')
    ttn_egais = state_info.get('ttn_egais')
    kb.button(text="Принять накладную", callback_data=SendAcceptTTN(id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_choose_divirgence_ttn():
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data='send_divergence_ttn')
    kb.button(text="Нет", callback_data='cancel_divergence_ttn')
    kb.adjust(2, repeat=True)
    return kb.as_markup()


def getKeyboard_choose_list_ttn(ttns_info, ttnload):
    """
    :param ttns_info: list
    Список [date_ttn, wbnumber, shipper_name, ttn_egais]
    :param ttnload: str
    Название папки
    :return: Keyboard
    """
    kb = InlineKeyboardBuilder()
    for date_ttn, wbnumber, shipper_name, ttn_egais in ttns_info:
        kb.button(text=f'{date_ttn} | {wbnumber} | {shipper_name}', callback_data=ListTTN(ttnload=ttnload, ttn_e=ttn_egais))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def getKeyboard_info_ttn():
    kb = InlineKeyboardBuilder()
    kb.button(text=f'⬅️ Назад', callback_data='menu_ttns')
    kb.adjust(1, repeat=True)
    return kb.as_markup()
