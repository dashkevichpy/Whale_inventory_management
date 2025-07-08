from collections import namedtuple
from enum import Enum

from telegram import KeyboardButton, ReplyKeyboardMarkup

from Conversations.conversationStoplist import BUTTON_STOP_START
from keyboards import BUTTON_BREAK_TITLE, BUTTON_ERROR_TITLE, BUTTON_STOCKS, BUTTON_WAIT_TITLE, BUTTON_TRANSFER, \
    BUTTON_DELIVERY_WAIT, BUTTON_DELIVERY_TIME_WATCH, BUTTON_WHAT_WHALE, BUTTON_REGISTER
from postgres import pg_get_employee_in_store, pg_get_position_by_id


class KeyboardStart(Enum):
    BM = [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
          [KeyboardButton(BUTTON_STOCKS)]]

    CASHIER = [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
               [KeyboardButton(BUTTON_WAIT_TITLE), KeyboardButton(BUTTON_TRANSFER)],
               [KeyboardButton(BUTTON_STOCKS), KeyboardButton(BUTTON_STOP_START)]]

    OPERATOR = [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
                [KeyboardButton(BUTTON_DELIVERY_TIME_WATCH), KeyboardButton(BUTTON_DELIVERY_WAIT)],
                [KeyboardButton(BUTTON_TRANSFER)]]

    PLANT = [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)]]

    DEFAULT = [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
               [KeyboardButton(BUTTON_WHAT_WHALE)]]

    NEW_EMPLOYEE = [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
               [KeyboardButton(BUTTON_WHAT_WHALE)]]


Employee = namedtuple('Employee', {'employee_name',
                                   'position',
                                   'department_name',
                                   'department_code',
                                   'store_name',
                                   'id_store',
                                   'invent_col'})


def keyboard_start(tel_id, context):
    store_name = pg_get_employee_in_store(tel_id)  # отметил ли сотрудник точку, где сейчас
    if store_name:
        employee = {**pg_get_position_by_id(tel_id)[0], **store_name[0]}
        employee = Employee(**employee)
        context.user_data['employee'] = employee
        keyboard = KeyboardStart[employee.department_code].value
    else:
        keyboard = KeyboardStart.DEFAULT.value
        if not pg_get_position_by_id(tel_id):  # и не зарегистрирован?
            keyboard = [[KeyboardButton(BUTTON_REGISTER)]]  # иди регистрируйся

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
