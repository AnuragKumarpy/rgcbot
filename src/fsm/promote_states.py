from aiogram.fsm.state import State, StatesGroup


class PromoteStates(StatesGroup):
    choosing_permissions = State()