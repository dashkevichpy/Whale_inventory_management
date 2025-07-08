"""Generate start keyboards based on employee department."""

from collections import namedtuple
from enum import Enum

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext


from keyboards import (
    BUTTON_BREAK_TITLE,
    BUTTON_DELIVERY_TIME_WATCH,
    BUTTON_DELIVERY_WAIT,
    BUTTON_ERROR_TITLE,
    BUTTON_REGISTER,
    BUTTON_STOCKS,
    BUTTON_TRANSFER,
    BUTTON_WAIT_TITLE,
    BUTTON_WHAT_WHALE,
    BUTTON_STOP_START,
)
from postgres import pg_get_employee_in_store, pg_get_position_by_id

class KeyboardStart(Enum):
    """Reply keyboard layouts for different departments."""

    BM = [
        [KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
        [KeyboardButton(BUTTON_STOCKS)],
    ]

    CASHIER = [
        [KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
        [KeyboardButton(BUTTON_WAIT_TITLE), KeyboardButton(BUTTON_TRANSFER)],
        [KeyboardButton(BUTTON_STOCKS), KeyboardButton(BUTTON_STOP_START)],
    ]

    OPERATOR = [
        [KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
        [KeyboardButton(BUTTON_DELIVERY_TIME_WATCH), KeyboardButton(BUTTON_DELIVERY_WAIT)],
        [KeyboardButton(BUTTON_TRANSFER)],
    ]

    PLANT = [
        [KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
    ]

    DEFAULT = [
        [KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
        [KeyboardButton(BUTTON_WHAT_WHALE)],
    ]

    NEW_EMPLOYEE = [
        [KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
        [KeyboardButton(BUTTON_WHAT_WHALE)],
    ]


Employee = namedtuple(
    "Employee",
    {
        "employee_name",
        "position",
        "department_name",
        "department_code",
        "store_name",
        "id_store",
        "invent_col",
    },
)


async def keyboard_start(
        tel_id: int, context: FSMContext | None
) -> ReplyKeyboardMarkup:
    """Return start keyboard for user and store employee data."""

    store_name = pg_get_employee_in_store(tel_id)
    if store_name:
        employee = {**pg_get_position_by_id(tel_id)[0], **store_name[0]}
        employee = Employee(**employee)
        if context:
            await context.update_data(employee=employee)
        keyboard = KeyboardStart[employee.department_code].value
    else:
        keyboard = KeyboardStart.DEFAULT.value
        if not pg_get_position_by_id(tel_id):
            keyboard = [[KeyboardButton(BUTTON_REGISTER)]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)