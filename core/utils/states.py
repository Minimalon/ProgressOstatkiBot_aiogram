from aiogram.fsm.state import State, StatesGroup


class StateOstatki(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()
    LAST_OSTATKI = State()
    LIST_OSTATKI = State()
    ERROR = State()


class StateTTNs(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()
    accept_ttn = State()
    choose_divirgence_ttn = State()


class Goods(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()

class CreateBarcode(StatesGroup):
    dcode = State()
    measure = State()
    barcode = State()
    price = State()
    name = State()
    final = State()
class ChangePrice(StatesGroup):
    barcode = State()
    price = State()
    final = State()
class Inventory(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()
    scaning = State()