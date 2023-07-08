from aiogram.filters.callback_data import CallbackData

# ====OSTATKI====

class Ostatki(CallbackData, prefix='ostatki'):
    inn: str
    fsrar: str


class OstatkiLast(CallbackData, prefix='ost_last'):
    inn: str
    fsrar: str

class OstatkiList(CallbackData, prefix='ostatki_menu_list'):
    inn: str
    fsrar: str

class OstatkiChooseList(CallbackData, prefix='ost_list'):
    inn: str
    fsrar: str
    file_name: str

# ====TTNS====

class ChooseEntity(CallbackData, prefix='entity'):
    inn: str
    fsrar: str
    port: str
    ip: str

class AcceptTTN(CallbackData, prefix='accept_ttn'):
    id_f2r: str
    id_wb: str
    ttn: str

class SendAcceptTTN(CallbackData, prefix='send_ttn'):
    id_f2r: str
    id_wb: str
    ttn: str


class ListTTN(CallbackData, prefix='ttn_list'):
    ttnload: str
    ttn_e: str

class SelectDcode(CallbackData, prefix='dcode'):
    dcode: int
    op_mode: int
    tmctype: int
class SelectMeasure(CallbackData, prefix='measure'):
    measure: int
    op_mode: int
    tmctype: int
class DeleteCashFromWhitelist(CallbackData, prefix='del_from_whitelist'):
    cash: str