from aiogram.fsm.state import State, StatesGroup


class StateOstatki(StatesGroup):
    choose_entity = State()
    choose_menu_ostatki = State()
    LAST_OSTATKI = State()
    LIST_OSTATKI = State()
    ERROR = State()

class StateTTNs(StatesGroup):
    choose_entity = State()
    menu_ttns = State()
    accept_ttn = State()
    choose_divirgence_ttn = State()
