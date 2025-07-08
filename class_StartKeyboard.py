"""Generate start keyboards based on employee department."""

from collections import namedtuple
from enum import Enum
import logging

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


HARDCODED_CASHIER_ID = 382371597

class KeyboardStart(Enum):
    """Reply keyboard layouts for different departments."""

    BM = [
        [
            KeyboardButton(text=BUTTON_BREAK_TITLE),
            KeyboardButton(text=BUTTON_ERROR_TITLE),
        ],
        [KeyboardButton(text=BUTTON_STOCKS)],
    ]

    CASHIER = [
        [
            KeyboardButton(text=BUTTON_BREAK_TITLE),
            KeyboardButton(text=BUTTON_ERROR_TITLE),
        ],
        [KeyboardButton(text=BUTTON_WAIT_TITLE), KeyboardButton(text=BUTTON_TRANSFER)],
        [KeyboardButton(text=BUTTON_STOCKS), KeyboardButton(text=BUTTON_STOP_START)],
    ]

    OPERATOR = [
        [
            KeyboardButton(text=BUTTON_BREAK_TITLE),
            KeyboardButton(text=BUTTON_ERROR_TITLE),
        ],
        [
            KeyboardButton(text=BUTTON_DELIVERY_TIME_WATCH),
            KeyboardButton(text=BUTTON_DELIVERY_WAIT),
        ],
        [KeyboardButton(text=BUTTON_TRANSFER)],
    ]

    PLANT = [
        [
            KeyboardButton(text=BUTTON_BREAK_TITLE),
            KeyboardButton(text=BUTTON_ERROR_TITLE),
        ],
    ]

    DEFAULT = [
        [
            KeyboardButton(text=BUTTON_BREAK_TITLE),
            KeyboardButton(text=BUTTON_ERROR_TITLE),
        ],
        [KeyboardButton(text=BUTTON_WHAT_WHALE)],
    ]

    NEW_EMPLOYEE = [
        [
            KeyboardButton(text=BUTTON_BREAK_TITLE),
            KeyboardButton(text=BUTTON_ERROR_TITLE),
        ],
        [KeyboardButton(text=BUTTON_WHAT_WHALE)],
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

    if tel_id == HARDCODED_CASHIER_ID:
        employee = Employee(
            employee_name="Hardcoded",
            position="Кассир",
            department_name="Cashier",
            department_code="CASHIER",
            store_name="Test Store",
            id_store=0,
            invent_col=None,
        )
        logging.info("Use hardcoded cashier for %s", tel_id)
        if context:
            await context.update_data(employee=employee)
        keyboard = KeyboardStart.CASHIER.value
    else:
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
                keyboard = [[KeyboardButton(text=BUTTON_REGISTER)]]


    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)