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

class TTNSChooseEntity(CallbackData, prefix='ttns'):
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